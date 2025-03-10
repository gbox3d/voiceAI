from VoiceDetector import VoiceDetector
import time
import numpy as np
import wave
import os
import collections
from datetime import datetime
import torch
from transformers import AutoModelForSpeechSeq2Seq, AutoProcessor, pipeline
import struct
import dotenv


class Application:
    def __init__(self):
        """초기화 및 환경변수 로드"""
        print("환경변수 로드")
        dotenv.load_dotenv()
        self.bSaveRsult = os.getenv("SAVE_RESULT", "False").lower() == "true"
        self.strSavePath = os.getenv("SAVE_PATH", "results")
        
        # 녹음 관련 변수 초기화
        self.is_recording = False
        self.recorded_data = []
        self.silence_start_time = None
        self.silence_threshold = 3  # 무음 감지 지속 시간 (초)
        
        # 기타 속성들은 run 메서드에서 초기화됨
        self.detector = None
        self.audio_buffer = None
        self.asr_pipe = None
    
    def initialize_asr_model(self):
        """Whisper ASR 모델 초기화"""
        # 디바이스 설정: GPU가 있으면 GPU를, 없으면 CPU 사용
        device = "cuda:0" if torch.cuda.is_available() else "cpu"
        torch_dtype = torch.float16 if torch.cuda.is_available() else torch.float32
        
        print(f"디바이스 설정: {device}")
        
        # 모델 및 프로세서 불러오기 (Whisper large-v3-turbo)
        model_id = "openai/whisper-large-v3-turbo"
        model = AutoModelForSpeechSeq2Seq.from_pretrained(
            model_id,
            torch_dtype=torch_dtype,
            low_cpu_mem_usage=True,
            use_safetensors=True
        )
        model.to(device)
        processor = AutoProcessor.from_pretrained(model_id)
        
        # 파이프라인 생성: 자동 음성 인식(ASR)
        asr_pipe = pipeline(
            "automatic-speech-recognition",
            model=model,
            tokenizer=processor.tokenizer,
            feature_extractor=processor.feature_extractor,
            torch_dtype=torch_dtype,
            device=device
        )
        
        return asr_pipe
    
    def process_audio_direct(self, audio_data, sample_rate):
        """녹음된 오디오 데이터를 직접 ASR 처리 (파일 저장 없음)"""
        try:
            # 바이트 데이터를 float32 NumPy 배열로 변환
            audio_bytes = b''.join(audio_data)
            
            # 16비트 PCM 데이터를 float32로 변환
            count = len(audio_bytes) // 2
            format_str = "%dh" % count
            shorts = np.array(struct.unpack(format_str, audio_bytes)).astype(np.float32)
            
            # 정규화 (-1.0 ~ 1.0 범위로)
            shorts = shorts / 32768.0
            
            # 오디오 길이 계산
            duration = len(shorts) / sample_rate
            print(f"녹음 길이: {duration:.2f}초")
            
            # 음성 인식 (ASR) 처리
            print("음성 인식(ASR) 처리 중...")
            
            # ASR 모델에 직접 전달
            result = self.asr_pipe(shorts, generate_kwargs={"language": "korean"})
            
            # 음성 인식 결과 출력
            print("========== 인식 결과 ==========")
            print(result["text"])
            print("==============================")
            
            if self.bSaveRsult:
                # 필요하다면 결과를 파일로 저장 (선택 사항)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                os.makedirs(self.strSavePath, exist_ok=True)
                
                # 텍스트 결과 저장
                text_filename = f"{self.strSavePath}/transcript_{timestamp}.txt"
                with open(text_filename, 'w', encoding='utf-8') as f:
                    f.write(result["text"])
                print(f"텍스트 파일 저장됨: {text_filename}")
                
                # 나중에 필요할 경우를 대비해 WAV 파일도 저장 (선택 사항)
                if False:  # 필요한 경우 True로 변경
                    wav_filename = f"recordings/recording_{timestamp}.wav"
                    with wave.open(wav_filename, 'wb') as wf:
                        wf.setnchannels(1)  # 모노
                        wf.setsampwidth(2)  # 16-bit
                        wf.setframerate(sample_rate)
                        wf.writeframes(audio_bytes)
                    print(f"녹음 파일 저장됨: {wav_filename}")
            
        except Exception as e:
            print(f"오디오 처리 중 오류 발생: {e}")
    
    def run(self):
        """애플리케이션 실행 메인 루프"""
        # ASR 모델 초기화
        print("ASR 모델 초기화 중...")
        self.asr_pipe = self.initialize_asr_model()
        print("ASR 모델 초기화 완료")
        
        # 디버그 모드로 설정
        self.detector = VoiceDetector(debug_mode=True)
        
        # 오디오 설정 요약 정보 출력
        audio_settings = self.detector.get_audio_settings_summary()
        print("===== 오디오 샘플링 정보 =====")
        print(f"포맷: {audio_settings['format']}")
        print(f"채널: {audio_settings['channels']}")
        print(f"샘플링 레이트: {audio_settings['rate']}")
        print(f"청크 크기: {audio_settings['chunk']}")
        
        # 스트림 초기화 (기본 마이크 사용)
        self.detector.initialize_stream()
        
        # 순환 버퍼 생성 (1초 이전 데이터를 저장)
        buffer_seconds = 1
        buffer_size = int(self.detector.RATE / self.detector.CHUNK * buffer_seconds)
        self.audio_buffer = collections.deque(maxlen=buffer_size)
        
        print("VAD 테스트 시작... 음성이 감지되면 녹음하고 ASR을 실행합니다...")
        
        try:
            self._main_loop()
        
        except KeyboardInterrupt:
            print("\n테스트 종료")
            
            # 녹음 중이었다면 처리
            if self.is_recording and self.recorded_data:
                print("녹음 중 종료됨. 마지막 녹음 처리...")
                self.process_audio_direct(self.recorded_data, self.detector.RATE)
        
        finally:
            # 리소스 정리
            self.detector.close_stream()
    
    def _main_loop(self):
        """메인 처리 루프"""
        while True:
            # 오디오 데이터 읽기
            audio_data = self.detector.stream.read(self.detector.CHUNK, exception_on_overflow=False)
            
            # 버퍼에 항상 오디오 데이터 추가
            self.audio_buffer.append(audio_data)
            
            # 음성 감지
            speech_detected, vad_result, smoothed_rms, rms_result, freq_result = self.detector.detect_speech(audio_data)
            
            # 음성이 감지된 경우
            if speech_detected:
                # 녹음 중이 아니라면 녹음 시작
                if not self.is_recording:
                    print("\n음성 감지! 녹음 시작...")
                    self.is_recording = True
                    self.recorded_data = []
                    
                    # 버퍼에 있는 1초 이전 데이터 추가
                    self.recorded_data.extend(list(self.audio_buffer))
                
                # 무음 타이머 초기화
                self.silence_start_time = None
                
                # 현재 데이터 추가
                self.recorded_data.append(audio_data)
            
            # 음성이 감지되지 않았지만 녹음 중인 경우
            elif self.is_recording:
                # 현재 데이터 추가
                self.recorded_data.append(audio_data)
                
                # 무음 시작 시간 체크
                if self.silence_start_time is None:
                    self.silence_start_time = time.time()
                    
                # 무음 지속 시간 확인
                silence_duration = time.time() - self.silence_start_time
                
                # 무음이 지정된 시간 이상 지속되면 녹음 종료
                if silence_duration >= self.silence_threshold:
                    print(f"무음 {self.silence_threshold}초 이상 감지됨. 녹음 종료.")
                    
                    # 오디오 데이터를 직접 ASR 처리 (파일 저장 없음)
                    self.process_audio_direct(self.recorded_data, self.detector.RATE)
                    
                    # 변수 초기화
                    self.is_recording = False
                    self.recorded_data = []
                    self.silence_start_time = None
            
            # CPU 사용량 줄이기
            time.sleep(0.01)


def main():
    """애플리케이션 시작점"""
    app = Application()
    app.run()


if __name__ == "__main__":
    main()