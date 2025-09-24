import threading
import numpy as np
import json
import os
import torch
import wave
from datetime import datetime
import pyaudio # 샘플 크기를 가져오기 위해 import
# from AudioDevice import AudioDevice

# --- Silero VAD 모델 로드 ---
try:
    VAD_MODEL, VAD_UTILS = torch.hub.load(
        repo_or_dir='snakers4/silero-vad',
        model='silero_vad',
        force_reload=False,
        onnx=False
    )
except Exception as e:
    print("VAD 모델 로딩 실패", f"Silero VAD 모델을 로드할 수 없습니다.\n인터넷 연결을 확인하세요: {e}")
    exit()

class VADProcessor:

    def __init__(self,
                 audio_device=None,
                 vad_threshold=0.5, 
                 silence_timeout_ms=1000,
                 pre_buffer_ms=200,
                 onRmsUpdate=None, onVadStatusUpdate=None,onVoiceDetected=None):
        
        self.audio_device = audio_device
        self.vad_threshold = vad_threshold
        self.silence_timeout_ms = silence_timeout_ms
        self.pre_buffer_ms = pre_buffer_ms

        self.monitoring_thread = None
        self.is_monitoring = threading.Event()
        
        # --- [추가] 일시정지/재개를 위한 Event 객체 ---
        self.is_paused = threading.Event()
        self.is_paused.set()  # 진행상태로 시작
        # --------------------------------------------

        self.is_speaking = False
        self.audio_buffer = []
        self.pre_speech_buffer = []
        self.silence_chunk_count = 0

        self.onRmsUpdate = onRmsUpdate
        self.onVadStatusUpdate = onVadStatusUpdate
        self.onVoiceDetected = onVoiceDetected

    
    def start_monitoring(self):    
        name = self.audio_device.settings['device_name']
        host_api = self.audio_device.settings['device_host_api']
        device = self.audio_device.get_device(device_name=name, host_api=host_api)

        if not device:            
            return False
        
        device_index = device['index']
        print(f"선택된 장치: {device['name']} (인덱스: {device_index})")            
            
        self.is_speaking = False
        self.audio_buffer.clear()
        self.pre_speech_buffer.clear()
        self.silence_chunk_count = 0

        self.is_monitoring.set()
        # self.is_paused.set() # 시작 시에는 재개 상태로 설정
        self.monitoring_thread = threading.Thread(target=self._monitor_thread, args=(device_index,), daemon=True)
        self.monitoring_thread.start()

        return True

    def stop_monitoring(self):        
        if self.is_monitoring.is_set():
            self.is_monitoring.clear()
            # self.is_paused.set()  # 스레드가 wait()에서 멈추는 것을 방지
            if self.monitoring_thread:
                self.monitoring_thread.join(timeout=1)
            self.monitoring_thread = None

    def pause_monitoring(self):
        """모니터링을 일시정지합니다."""

        self.is_speaking = False
        self.audio_buffer.clear()
        self.pre_speech_buffer.clear()
        self.silence_chunk_count = 0

        print("VAD 모니터링 일시정지")

        self.is_paused.clear()  # 일시정지 상태로 설정
        

    def resume_monitoring(self):
        """모니터링을 재개합니다."""

        print("VAD 모니터링 재개")

        self.is_speaking = False
        self.is_speeching = False
        self.audio_buffer.clear()
        self.pre_speech_buffer.clear()
        self.silence_chunk_count = 0

        self.is_paused.set()

    def _monitor_thread(self, device_index):
        """백그라운드에서 오디오를 처리하고, 음성 구간을 감지하여 버퍼에 저장합니다."""
        if not self.audio_device.initialize(device_index):
            print("오류", "오디오 장치를 열 수 없습니다.")
            return
        
        rate = self.audio_device.settings['rate']
        chunk_size = self.audio_device.settings['chunk']
        if rate not in [8000, 16000]:
            print(f"경고: 현재 샘플링 레이트({rate}Hz)는 Silero VAD에 최적화되지 않았습니다.")            
        
        chunks_per_second = rate / chunk_size
        silence_chunks_needed = int(chunks_per_second * (self.silence_timeout_ms / 1000))
        pre_buffer_chunks_needed = int(chunks_per_second * (self.pre_buffer_ms / 1000))
            
        try:
            while self.is_monitoring.is_set():
                # --- [수정] 일시정지 상태이면 여기서 대기 ---
                self.is_paused.wait()
                # ----------------------------------------

                audio_chunk_bytes = self.audio_device.read_chunk()
                if audio_chunk_bytes:
                    audio_int16 = np.frombuffer(audio_chunk_bytes, dtype=np.int16)
                    audio_float32 = audio_int16.astype(np.float32) / 32768.0
                    audio_tensor = torch.from_numpy(audio_float32)

                    speech_prob = VAD_MODEL(audio_tensor, rate).item()
                    is_speech = speech_prob > self.vad_threshold
                    
                    rms_level = self.audio_device.get_rms(audio_chunk_bytes)
                    
                    if self.onRmsUpdate:
                        self.onRmsUpdate(rms_level)
                    if self.onVadStatusUpdate:
                        self.onVadStatusUpdate(is_speech,self.is_speaking)

                    if is_speech:
                        if not self.is_speaking:
                            self.is_speaking = True
                            self.audio_buffer.extend(self.pre_speech_buffer)
                        
                        self.audio_buffer.append(audio_chunk_bytes)
                        self.silence_chunk_count = 0
                    else:
                        if self.is_speaking:
                            self.silence_chunk_count += 1
                            self.audio_buffer.append(audio_chunk_bytes)
                            if self.silence_chunk_count > silence_chunks_needed:
                                data_to_save = list(self.audio_buffer)
                                
                                self.is_speaking = False
                                self.silence_chunk_count = 0
                                self.audio_buffer.clear()
                                
                                if data_to_save and self.onVoiceDetected:
                                    self.onVoiceDetected(data_to_save)                                    
                        else:
                            self.pre_speech_buffer.append(audio_chunk_bytes)
                            if len(self.pre_speech_buffer) > pre_buffer_chunks_needed:
                                self.pre_speech_buffer.pop(0)
        finally:
            self.audio_device.close()

    
