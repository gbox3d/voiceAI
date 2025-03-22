import torch
from transformers import AutoModelForSpeechSeq2Seq, AutoProcessor, pipeline
import pyaudio
import wave
import numpy as np
import time
import os
import tempfile
import threading
import keyboard

# 디바이스 설정: GPU가 있으면 GPU를, 없으면 CPU 사용
device = "cuda:0" if torch.cuda.is_available() else "cpu"
torch_dtype = torch.float16 if torch.cuda.is_available() else torch.float32

print(f"사용 중인 디바이스: {device}")

# 모델 및 프로세서 불러오기 (Whisper large-v3-turbo)
model_id = "openai/whisper-large-v3-turbo"
print("모델 로딩 중...")
model = AutoModelForSpeechSeq2Seq.from_pretrained(
    model_id,
    torch_dtype=torch_dtype,
    low_cpu_mem_usage=True,
    use_safetensors=True
)
model.to(device)
processor = AutoProcessor.from_pretrained(model_id)

print("모델 및 프로세서 불러오기 완료")

# 파이프라인 생성: 자동 음성 인식(ASR)
asr_pipe = pipeline(
    "automatic-speech-recognition",
    model=model,
    tokenizer=processor.tokenizer,
    feature_extractor=processor.feature_extractor,
    torch_dtype=torch_dtype,
    device=device
)

print("자동 음성 인식(ASR) 파이프라인 생성 완료")

# 녹음 설정
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 16000  # Whisper는 16kHz 오디오를 사용
CHUNK = 1024

class AudioRecorder:
    def __init__(self):
        self.audio = pyaudio.PyAudio()
        self.frames = []
        self.is_recording = False
        self.record_thread = None
        
    def start_recording(self):
        """녹음 시작"""
        self.is_recording = True
        self.frames = []
        self.stream = self.audio.open(
            format=FORMAT, 
            channels=CHANNELS,
            rate=RATE, 
            input=True,
            frames_per_buffer=CHUNK
        )
        
        print("녹음 중... (종료하려면 Enter 키를 누르세요)")
        
        # 녹음 스레드 시작
        self.record_thread = threading.Thread(target=self._record)
        self.record_thread.start()
    
    def _record(self):
        """녹음 처리 (별도 스레드에서 실행)"""
        while self.is_recording:
            data = self.stream.read(CHUNK)
            self.frames.append(data)
    
    def stop_recording(self):
        """녹음 중지"""
        if not self.is_recording:
            return None
            
        self.is_recording = False
        
        # 녹음 스레드가 종료될 때까지 대기
        if self.record_thread:
            self.record_thread.join()
        
        # 스트림 정리
        self.stream.stop_stream()
        self.stream.close()
        
        # 녹음된 데이터가 없으면 None 반환
        if not self.frames:
            return None
            
        # 임시 파일로 저장
        temp_file = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
        wf = wave.open(temp_file.name, 'wb')
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(self.audio.get_sample_size(FORMAT))
        wf.setframerate(RATE)
        wf.writeframes(b''.join(self.frames))
        wf.close()
        
        print("녹음 완료!")
        return temp_file.name
        
    def close(self):
        """리소스 정리"""
        self.audio.terminate()

def speech_to_text(audio_file):
    """
    오디오 파일을 텍스트로 변환
    """
    if not audio_file:
        return "녹음된 오디오가 없습니다."
        
    print("음성을 텍스트로 변환 중...")
    # 한국어로 전사하도록 language 파라미터 설정
    result = asr_pipe(audio_file, generate_kwargs={"language": "korean"})
    return result["text"]

def main():
    recorder = AudioRecorder()
    
    try:
        print("실시간 음성 인식 시작")
        
        while True:
            print("\n녹음을 시작하려면 Enter 키를 누르세요...")
            input()  # 엔터 키를 기다림
            
            # 녹음 시작
            recorder.start_recording()
            
            # 다시 엔터 키를 누를 때까지 대기
            input()
            
            # 녹음 중지
            audio_file = recorder.stop_recording()
            
            if audio_file:
                # 음성을 텍스트로 변환
                text = speech_to_text(audio_file)
                print("인식된 텍스트:", text)
                
                # 임시 파일 삭제
                os.unlink(audio_file)
            
    except KeyboardInterrupt:
        print("\n프로그램 종료")
    finally:
        recorder.close()

if __name__ == "__main__":
    main()