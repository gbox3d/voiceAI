# filename: server.py
# Author: gbox3d
# Created: 2025-02-18
# Description This file is a part of STT App Server
# llm 모듈은 위의 소스정보 부분을 수정하지 않습니다. 아래 부터 수정할수있습니다.

import asyncio
import struct
import sys
import os
import io
import re

import torch
import numpy as np
from pydub import AudioSegment

# pydub.AudioSegment는 ffmpeg/avconv가 설치되어 있어야 mp3, webm 등을 처리 가능
# (pip install pydub, 그리고 OS에 ffmpeg 설치 필요)

from transformers import AutoModelForSpeechSeq2Seq, AutoProcessor, pipeline

#---------------------------------------------------------
# 1. 다양한 포맷을 처리하기 위한 디코딩 함수
#---------------------------------------------------------
def decode_audio(audio_data: bytes, audio_format: str):
    audio_segment = AudioSegment.from_file(io.BytesIO(audio_data), format=audio_format)
    sample_rate = audio_segment.frame_rate
    channels = audio_segment.channels
    samples = np.array(audio_segment.get_array_of_samples())
    
    # 멀티채널이면 mono로 변환
    if channels > 1:
        samples = samples.reshape((-1, channels))
        samples = samples.mean(axis=1)
    
    # sample_width를 활용하여 정규화 계수 계산 (예: 2바이트=16비트라면 2^(16-1)=32768)
    max_val = float(1 << (8 * audio_segment.sample_width - 1))
    waveform = samples.astype(np.float32) / max_val

    return waveform, sample_rate


#---------------------------------------------------------
# 2. 비동기 서버 클래스
#---------------------------------------------------------
class AsrServer:
    # --- status_code 정의 ---
    SUCCESS = 0
    ERR_CHECKCODE_MISMATCH = 1
    ERR_INVALID_DATA = 2
    ERR_INVALID_REQUEST = 3
    ERR_INVALID_PARAMETER = 4
    ERR_INVALID_FORMAT = 5
    ERR_UNKNOWN_CODE = 8
    ERR_EXCEPTION = 9
    ERR_TIMEOUT = 10
    
    __VERSION__ = "1.0.1"

    def __init__(self, host=None, port=None, timeout=None, checkcode=None, stt_pipeline=None, 
                 min_text_length=5, no_voice_text="novoice"):
        # 환경 변수나 기본값으로 설정
        self.host = host or os.getenv("ASR_HOST", "localhost")
        self.port = port or int(os.getenv("ASR_PORT", 26070))
        
        # timeout 값이 문자열이면 int로 변환합니다.
        if timeout is not None:
            self.timeout = int(timeout)
        else:
            self.timeout = int(os.getenv("ASR_TIMEOUT", 10))
            
        self.checkcode = checkcode or int(os.getenv("ASR_CHECKCODE", 20250122))

        self.stt_pipeline = stt_pipeline
        
        # 음성 인식 필터링 관련 설정
        self.min_text_length = min_text_length  # 최소 텍스트 길이
        self.no_voice_text = no_voice_text      # 의미 없는 음성일 때 반환할 텍스트

    async def receive_data_with_timeout(self, reader, size, label):
        """
        비동기 방식으로 데이터 수신 (타임아웃 포함)
          - size 바이트 만큼 정확히 읽는다.
        """
        try:
            data = await asyncio.wait_for(reader.readexactly(size), timeout=self.timeout)
            return data
        except asyncio.TimeoutError:
            print(f"[ERROR] {label} 수신 타임아웃 발생")
            return None
        except Exception as e:
            print(f"[ERROR] {label} 수신 중 예외 발생: {e}")
            return None
    
    def is_meaningful_speech(self, text):
        """
        인식된 텍스트가 의미있는 음성인지 판단합니다.
        """
        if text is None:
            return False
            
        # 1. 텍스트 길이 확인 (너무 짧으면 무시)
        if len(text.strip()) < self.min_text_length:
            print(f"[INFO] 텍스트가 너무 짧음: '{text}'")
            return False
            
        # 2. 의미 없는 소리 패턴 체크
        noise_patterns = ["음", "어", "아", "흠", "음...", "어...", "아...", "음~", "어~", "아~"]
        text_words = text.strip().split()
        
        # 모든 단어가 무의미한 소리인지 확인
        if all(word in noise_patterns for word in text_words):
            print(f"[INFO] 의미 없는 소리만 포함됨: '{text}'")
            return False
            
        # 3. 반복되는 패턴 체크 (예: "아 아 아 아")
        if len(text_words) > 2:
            # 동일한 단어가 3번 이상 반복되면 의미 없는 것으로 간주
            word_counts = {}
            for word in text_words:
                word_counts[word] = word_counts.get(word, 0) + 1
                
            max_repeat = max(word_counts.values()) if word_counts else 0
            if max_repeat >= 3 and max_repeat / len(text_words) > 0.5:  # 50% 이상이 동일 단어 반복
                print(f"[INFO] 단어 반복 패턴 감지됨: '{text}'")
                return False
                
        # 4. 특수문자나 숫자만으로 구성된 텍스트인지 확인
        if re.match(r'^[\d\W]+$', text.strip()):
            print(f"[INFO] 숫자나 특수문자만 포함됨: '{text}'")
            return False
            
        # 추가 필터를 여기에 구현할 수 있습니다
            
        return True

    async def process_audio(self, waveform, sr):
        """
        오디오 데이터를 처리하고 STT 결과를 반환합니다.
        의미 없는 음성일 경우 no_voice_text를 반환합니다.
        """
        try:
            # STT Pipeline 호출
            result = self.stt_pipeline({
                "array": waveform,
                "sampling_rate": sr
            })
            
            recognized_text = result["text"].strip()
            
            # 의미 있는 음성인지 확인
            if self.is_meaningful_speech(recognized_text):
                return recognized_text
            else:
                return self.no_voice_text
                
        except Exception as e:
            print(f"[ERROR] 음성 처리 중 오류 발생: {e}")
            return self.no_voice_text

    async def handle_client(self, reader, writer):
        addr = writer.get_extra_info('peername')
        print(f"[INFO] 클라이언트 연결됨: {addr}")

        try:
            #------------------------------------------------
            # 1) 헤더(8바이트) 수신: checkcode(4) + request_code(4)
            #------------------------------------------------
            header = await reader.readexactly(8)
            checkcode, request_code = struct.unpack('!ii', header)
            print(f"[INFO] 요청 - checkcode: {checkcode}, code: {request_code}")

            #------------------------------------------------
            # 2) checkcode 확인
            #------------------------------------------------
            if checkcode != self.checkcode:
                print("[ERROR] 잘못된 checkcode")
                response = struct.pack('!iiB', self.checkcode, request_code, self.ERR_CHECKCODE_MISMATCH)
                writer.write(response)
                await writer.drain()
                return

            #------------------------------------------------
            # 3) 요청 코드별 처리
            #------------------------------------------------
            if request_code == 99:
                # Ping
                print("[INFO] Ping 요청 수신")
                response = struct.pack('!iiB', self.checkcode, request_code, self.SUCCESS)
                writer.write(response)
                await writer.drain()

            elif request_code == 0x01:
                #------------------------------------------------
                # (A) 오디오 포맷코드(예: 1바이트) 수신
                #------------------------------------------------
                format_byte = await self.receive_data_with_timeout(reader, 1, "Audio Format Code")
                if not format_byte:
                    print("[ERROR] 오디오 포맷 코드 수신 실패")
                    response = struct.pack('!iiB', self.checkcode, request_code, self.ERR_INVALID_FORMAT)
                    writer.write(response)
                    await writer.drain()
                    return

                format_code = struct.unpack('!B', format_byte)[0]

                # 포맷 매핑 예시 (원하는 방식으로 확장 가능)
                format_map = {
                    1: "wav",
                    2: "mp3",
                    3: "webm",
                    4: "mp4"  # 새로운 포맷코드 4에 대한 매핑 추가
                }

                if format_code not in format_map:
                    print(f"[ERROR] 지원하지 않는 포맷 코드: {format_code}")
                    response = struct.pack('!iiB', self.checkcode, request_code, self.ERR_INVALID_FORMAT)
                    writer.write(response)
                    await writer.drain()
                    return

                audio_format_str = format_map[format_code]
                print(f"[INFO] 오디오 포맷: {audio_format_str}")

                #------------------------------------------------
                # (B) 오디오 데이터 길이(4바이트) 수신 후, 오디오 데이터
                #------------------------------------------------
                size_bytes = await self.receive_data_with_timeout(reader, 4, "Audio Data Size")
                if not size_bytes:
                    print("[ERROR] 오디오 데이터 길이 정보 수신 실패")
                    response = struct.pack('!iiB', self.checkcode, request_code, self.ERR_INVALID_DATA)
                    writer.write(response)
                    await writer.drain()
                    return
                
                audio_size = struct.unpack('!i', size_bytes)[0]
                print(f"[INFO] 오디오 데이터 길이: {audio_size} 바이트")
                audio_data = await self.receive_data_with_timeout(reader, audio_size, "Audio Data")
                if not audio_data:
                    print("[ERROR] 오디오 데이터 수신 실패")
                    response = struct.pack('!iiB', self.checkcode, request_code, self.ERR_INVALID_DATA)
                    writer.write(response)
                    await writer.drain()
                    return

                #------------------------------------------------
                # (C) Whisper 모델 STT 처리
                #------------------------------------------------
                if not self.stt_pipeline:
                    print("[ERROR] STT Pipeline(모델)이 초기화되지 않음")
                    response = struct.pack('!iiB', self.checkcode, request_code, self.ERR_INVALID_REQUEST)
                    writer.write(response)
                    await writer.drain()
                    return

                try:
                    # 1) 디코딩 (pydub)
                    waveform, sr = decode_audio(audio_data, audio_format_str)
                    print(f"[INFO] 오디오 데이터 변환 완료: shape={waveform.shape}, sr={sr}")   

                    # 2) STT Pipeline 호출 (의미 있는 음성 판단 추가)
                    recognized_text = await self.process_audio(waveform, sr)
                    print(f"[INFO] 인식 결과: '{recognized_text}'")
                    
                except Exception as e:
                    print(f"[ERROR] STT 변환 중 예외 발생: {e}")
                    response = struct.pack('!iiB', self.checkcode, request_code, self.ERR_EXCEPTION)
                    writer.write(response)
                    await writer.drain()
                    return

                #------------------------------------------------
                # (D) 변환 결과 전송
                #------------------------------------------------
                encoded_text = recognized_text.encode('utf-8')
                response_header = struct.pack('!iiB', self.checkcode, request_code, self.SUCCESS)
                response_length = struct.pack('!i', len(encoded_text))
                response = response_header + response_length + encoded_text

                writer.write(response)
                await writer.drain()

            else:
                print(f"[ERROR] 알 수 없는 요청 코드: {request_code}")
                response = struct.pack('!iiB', self.checkcode, request_code, self.ERR_UNKNOWN_CODE)
                writer.write(response)
                await writer.drain()

        except asyncio.IncompleteReadError:
            print("[ERROR] 클라이언트 데이터 수신 실패")
        except Exception as e:
            print(f"[ERROR] 처리 중 예외 발생: {e}")
        finally:
            writer.close()
            await writer.wait_closed()
            print(f"[INFO] 클라이언트 연결 종료: {addr}")

    async def run_server(self):
        server = await asyncio.start_server(self.handle_client, self.host, self.port)
        addr = server.sockets[0].getsockname()
        print(f"[INFO] 서버 시작: {addr}, TIMEOUT={self.timeout}s, CHECKCODE={self.checkcode} , VERSION={self.__VERSION__}")
        print(f"[INFO] 음성 필터링 설정: 최소 길이={self.min_text_length}, 무음성 텍스트='{self.no_voice_text}'")

        try:
            async with server:
                await server.serve_forever()
        except KeyboardInterrupt:
            # Ctrl+C(KeyInterrupt) 시, 에러 메시지 없이 종료
            print("\n[INFO] 서버가 종료됩니다 (KeyboardInterrupt).")
            server.close()
            await server.wait_closed()
            sys.exit(0)

#-----------------------
# 실행 파트 (직접 실행 시)
#-----------------------
if __name__ == "__main__":
    device = "cuda:0" if torch.cuda.is_available() else "cpu"
    torch_dtype = torch.float16 if torch.cuda.is_available() else torch.float32

    model_id = "openai/whisper-large-v3-turbo"
    print("[INFO] 모델과 프로세서 로딩 중...")
    model = AutoModelForSpeechSeq2Seq.from_pretrained(
        model_id,
        torch_dtype=torch_dtype,
        low_cpu_mem_usage=True,
        use_safetensors=True
    ).to(device)
    processor = AutoProcessor.from_pretrained(model_id)

    # STT 파이프라인 구성
    stt_pipeline = pipeline(
        task="automatic-speech-recognition",
        model=model,
        processor=processor,
        device=0 if device.startswith("cuda") else -1
    )

    print("[INFO] 모델 및 프로세서 로딩 완료")
 
    # 서버 인스턴스 생성
    asr_server = AsrServer(
        host="0.0.0.0",
        port=2500,
        timeout=10,
        checkcode=20250122,
        stt_pipeline=stt_pipeline,
        min_text_length=5,
        no_voice_text="novoice"
    )

    asyncio.run(asr_server.run_server())