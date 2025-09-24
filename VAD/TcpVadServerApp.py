# file: TcpVadServerApp.py

import io, wave
import asyncio
import threading
import time
import os
import signal
import sys
from typing import Optional
from VadChecker import VadChecker   # ← 추가: VAD 판정기

import torch

import wave
from pathlib import Path
from datetime import datetime

import dotenv
dotenv.load_dotenv()  # .env 파일 로드

from server import Server
from AudioPlayer import AudioPlayer
 

def get_env_bool(key: str, default: bool = False) -> bool:
    """환경변수에서 boolean 값 읽기"""
    value = os.getenv(key, "").lower()
    if value in ("true", "1", "yes", "on"):
        return True
    elif value in ("false", "0", "no", "off"):
        return False
    return default


def get_env_int(key: str, default: int) -> int:
    """환경변수에서 int 값 읽기"""
    try:
        return int(os.getenv(key, str(default)))
    except ValueError:
        return default


def get_env_float(key: str, default: float) -> float:
    """환경변수에서 float 값 읽기"""
    try:
        return float(os.getenv(key, str(default)))
    except ValueError:
        return default


class TcpVadServerApp:
    def __init__(self):
        # .env에서 서버 설정 읽기
        host = os.getenv("VAD_HOST")
        port = get_env_int("VAD_PORT", 26070)
        timeout = get_env_int("VAD_TIMEOUT", 10)
        checkcode = get_env_int("VAD_CHECKCODE", 20250918)
        
        # .env에서 오디오 설정 읽기
        auto_play = get_env_bool("VAD_AUTO_PLAY", True)
        audio_sample_rate = get_env_int("VAD_AUDIO_SAMPLE_RATE", 16000)
        audio_channels = get_env_int("VAD_AUDIO_CHANNELS", 1)
        vad_threshold = get_env_float("VAD_THRESHOLD", 0.5)   # ← 선택적: 임계값 환경변수
        audio_device_index = get_env_int("VAD_AUDIO_DEVICE_INDEX", -1)
        if audio_device_index < 0:
            audio_device_index = None

        # 세그먼트 저장 옵션 (기본 활성화)
        self._save_segments = get_env_bool("VAD_SAVE_SEGMENTS", True)
        self._out_dir = Path(os.getenv("VAD_OUT_DIR", "vad_segments"))
        if self._save_segments:
            self._out_dir.mkdir(parents=True, exist_ok=True)

        # .env에서 재생 설정 읽기
        play_chunk_count = get_env_int("VAD_PLAY_CHUNK_COUNT", 5)
        play_interval = get_env_float("VAD_PLAY_INTERVAL", 0.1)
        
        print(f"[CONFIG] 서버 설정: {host}:{port}, 체크코드: {checkcode}")
        print(f"[CONFIG] 오디오 설정: {audio_sample_rate}Hz, {audio_channels}ch, 자동재생:  {auto_play}")
        print(f"[CONFIG] 재생 설정: {play_chunk_count}개씩, {play_interval}초 간격")
        
        # 서버 인스턴스 생성
        self.server = Server(host, port, timeout, checkcode)
        
        # 오디오 플레이어 설정
        self.auto_play = auto_play
        self.audio_player = AudioPlayer(
            sample_rate=audio_sample_rate,
            channels=audio_channels,
            device_index=audio_device_index
        ) if auto_play else None

        # VAD 판정기 초기화 (다운믹스 전제: mono PCM16)
        self.vad = VadChecker(
            sample_rate=audio_sample_rate,
            vad_threshold=vad_threshold,
            min_speech_ms= get_env_int("VAD_MIN_SPEECH_MS", 150), # 최소 발화 길이
            min_silence_ms= get_env_int("VAD_MIN_SILENCE_MS", 300), # 발화 종료 기준
            pre_buffer_ms= get_env_int("VAD_PRE_BUFFER_MS", 200), # 발화 시작부 보호
            device="cuda" if torch.cuda.is_available() else "cpu",
            force_reload=False
        )
        self._audio_channels = audio_channels
        self._audio_sample_rate = audio_sample_rate

        # 재생 스레드 설정
        self.play_chunk_count = play_chunk_count
        self.play_interval = play_interval
        self.play_thread = None
        self.running = False
        
        # 종료 처리용
        self.shutdown_event = asyncio.Event()
        self._cleanup_done = False

     # === 추가: RAW PCM16 -> WAV(bytes) 래핑 ===
    
    def _pcm16_to_wav_bytes(self, pcm_bytes: bytes) -> bytes:
        """mono PCM16 @ self._audio_sample_rate -> WAV 바이트 인코딩"""
        bio = io.BytesIO()
        with wave.open(bio, "wb") as wf:
            wf.setnchannels(1)  # VAD 출력이 mono 전제
            wf.setsampwidth(2)  # PCM16 = 2 bytes
            wf.setframerate(self._audio_sample_rate)
            wf.writeframes(pcm_bytes)
        return bio.getvalue()
    
    # ---- 파일명 포맷: SSS.mmm-EEE.mmm.wav ----
    def _fmt_sec_ms(self, sec_float: float) -> str:
        # 00012.345 형식(정수부 zero-pad 5자리, 소수 3자리)
        return f"{sec_float:09.3f}"

    def _save_wav_segment_with_trackname(self, pcm_bytes: bytes, start_s: float, end_s: float) -> str:
        sr = self._audio_sample_rate
        name = f"{self._fmt_sec_ms(start_s)}-{self._fmt_sec_ms(end_s)}.wav"
        fpath = self._out_dir / name
        with wave.open(str(fpath), "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sr)
            wf.writeframes(pcm_bytes)
        return str(fpath)

    def _audio_playback_loop(self):
        """백그라운드 오디오 재생 루프"""
        print("[AUDIO] 재생 스레드 시작")
        
        while self.running:
            try:
                if self.server.has_chunks(self.play_chunk_count): # 정해진 개수 이상의 청크가 있을 때만 재생
                    # 버퍼에서 청크 가져오기
                    chunks = self.server.pop_chunks(self.play_chunk_count)
                    
                    # ▶ 재생 전 VAD 판정 & 로그 출력 (+오프셋)
                    segs, details, offsets = self.vad.check_vad_chunks(                    
                        chunks, return_details=True, return_offsets=True
                    )

                    if details is not None:
                        for i, item in enumerate(details, 1):
                            if len(item) == 3:
                                prob, is_speech, silence_ms = item
                                tag = "🗣️" if is_speech else "—"
                                print(f"[VAD] chunk#{i:02d}: prob={prob:.2f} {tag} silence={silence_ms:.1f}ms")
                            else:
                                prob, is_speech = item
                                tag = "🗣️" if is_speech else "—"
                                print(f"[VAD] chunk#{i:02d}: prob={prob:.2f} {tag}")

                    if segs:
                        total_seg_bytes = sum(len(s) for s in segs)
                        print(f"[VAD] completed segments: {len(segs)} (bytes={total_seg_bytes})")
                        if offsets:

                            sr = self._audio_sample_rate
                            for (seg_bytes, (st_samp, ed_samp)) in zip(segs, offsets):
                                start_sec = st_samp / float(sr)
                                end_sec = ed_samp / float(sr)
                                
                                
                                # ① WAV 저장(옵션)
                                if self._save_segments:
                                    path = self._save_wav_segment_with_trackname(seg_bytes, start_sec, end_sec)
                                    print(f"[VAD] saved: {path}  (start={start_sec:.3f}s, end={end_sec:.3f}s, dur={end_sec-start_sec:.3f}s)")
                                
                                # ② 클라이언트로 전송
                                #   format_code: 1 = PCM16 mono (임의 정의)
                                try:
                                    # self.server.send_segment(format_code=1, audio_bytes=seg_bytes)
                                    # (변경) RAW -> WAV 변환 후 전송
                                    wav_bytes = self._pcm16_to_wav_bytes(seg_bytes)
                                    self.server.send_segment(format_code=1, audio_bytes=wav_bytes)

                                    print(f"[VAD] sent to client: {len(seg_bytes)} bytes "
                                          f"(start={start_sec:.3f}s, end={end_sec:.3f}s)")
                                except Exception as e:
                                    print(f"[WARN] 클라이언트 전송 실패: {e}")

                    if chunks and self.audio_player:
                        buffer_info = self.get_buffer_info()
                        print(f"[AUDIO] 버퍼 상태: {buffer_info['chunk_count']}개 청크 남음, {buffer_info['total_bytes']}바이트 (사용 가능: {buffer_info['available_bytes']}바이트)")
                        self.audio_player.play_chunks(chunks)
                
                time.sleep(self.play_interval)
                
            except Exception as e:
                if self.running:  # 종료 중이 아닐 때만 에러 출력
                    print(f"[AUDIO ERROR] 재생 루프 오류: {e}")
                time.sleep(1.0)
        
        print("[AUDIO] 재생 스레드 종료")
    
    def start_audio_playback(self):
        """오디오 재생 시작"""
        if not self.auto_play or not self.audio_player:
            return
        
        self.audio_player.start()
        self.running = True
        
        self.play_thread = threading.Thread(target=self._audio_playback_loop, daemon=True)
        self.play_thread.start()
    
    def stop_audio_playback(self):
        """오디오 재생 중지"""
        if not self.running:
            return
            
        print("[AUDIO] 오디오 재생 중지 중...")
        self.running = False
        
        if self.play_thread and self.play_thread.is_alive():
            self.play_thread.join(timeout=3.0)
            if self.play_thread.is_alive():
                print("[WARN] 오디오 스레드가 제한시간 내에 종료되지 않았습니다")
        
        if self.audio_player:
            try:
                self.audio_player.stop()
            except Exception as e:
                print(f"[WARN] 오디오 플레이어 정지 중 오류: {e}")
        
        print("[AUDIO] 오디오 재생 중지 완료")
    
    def get_buffer_info(self):
        """현재 버퍼 상태 정보"""
        return {
            'chunk_count': self.server.get_chunk_count(),
            'total_bytes': self.server.get_total_bytes(),
            'available_bytes': self.server.get_available_bytes()
        }
    
    async def cleanup(self):
        """리소스 정리"""
        if self._cleanup_done:
            return
        
        print("[INFO] 서버 정리 중...")
        self._cleanup_done = True
        
        # 오디오 재생 중지
        self.stop_audio_playback()
        
        # 오디오 플레이어 정리
        if self.audio_player:
            try:
                self.audio_player.close()
                print("[INFO] 오디오 플레이어 정리 완료")
            except Exception as e:
                print(f"[WARN] 오디오 플레이어 정리 중 오류: {e}")

        # VAD 정리 (자원 없음이지만 명시적으로 호출)
        try:
            if hasattr(self, "vad") and self.vad:
                self.vad.close()
        except Exception:
            pass
        
        # 버퍼 정리
        if hasattr(self.server, 'clear_buffer'):
            cleared = self.server.clear_buffer()
            if cleared > 0:
                print(f"[INFO] 버퍼 정리: {cleared}개 청크 삭제")
        
        print("[INFO] 서버 정리 완료")
    
    def request_shutdown(self):
        """종료 요청"""
        print("[INFO] 종료 요청 받음")
        self.shutdown_event.set()
    def manual_play_chunks(self, count: int = None):
        """수동으로 청크 재생 (자동 재생이 비활성화된 경우)"""
        if not self.audio_player:
            print("[WARN] 오디오 플레이어가 비활성화되어 있습니다")
            return
        
        count = count or self.play_chunk_count
        
        if self.server.has_chunks(count):
            chunks = self.server.pop_chunks(count)
            self.audio_player.play_chunks(chunks)
            print(f"[AUDIO] 수동 재생: {len(chunks)}개 청크")
        else:
            current_count = self.server.get_chunk_count()
            print(f"[WARN] 재생할 충분한 청크가 없습니다 (요청: {count}, 현재: {current_count})")
    
    async def run(self):
        """서버 실행"""
        print(f"[INFO] TCP VAD 서버 시작")
        print(f"[INFO] 자동 오디오 재생: {'활성' if self.auto_play else '비활성'}")
        
        # 자동 재생 시작
        if self.auto_play:
            self.start_audio_playback()
        
        # 서버 태스크 생성
        server_task = asyncio.create_task(self.server.run())
        shutdown_task = asyncio.create_task(self.shutdown_event.wait())
        
        try:
            # 서버 실행 또는 종료 이벤트 대기
            done, pending = await asyncio.wait(
                [server_task, shutdown_task],
                return_when=asyncio.FIRST_COMPLETED
            )
            
            # 미완료 태스크들 취소
            for task in pending:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
            
        except Exception as e:
            print(f"[ERROR] 서버 실행 중 오류: {e}")
        finally:
            await self.cleanup()


def setup_signal_handlers(server_app):
    """시그널 핸들러 설정"""
    def signal_handler(signum, frame):
        print(f"\n[INFO] 시그널 {signum} 받음 - 종료 처리 시작")
        server_app.request_shutdown()
    
    # Windows와 Unix 모두 지원
    signal.signal(signal.SIGINT, signal_handler)  # Ctrl+C
    if hasattr(signal, 'SIGTERM'):
        signal.signal(signal.SIGTERM, signal_handler)  # 종료 시그널


async def main():
    # 서버 생성
    server_app = TcpVadServerApp()
    
    # 시그널 핸들러 설정
    setup_signal_handlers(server_app)
    
    try:
        await server_app.run()
    except KeyboardInterrupt:
        # 이미 시그널 핸들러에서 처리됨
        pass
    except Exception as e:
        print(f"[ERROR] 예상치 못한 오류: {e}")
    finally:
        print("[INFO] 프로그램 종료")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        # asyncio.run 레벨에서의 KeyboardInterrupt 처리
        print("\n[INFO] 강제 종료")
        sys.exit(0)