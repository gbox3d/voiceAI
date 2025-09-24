
import pyaudio
import numpy as np
from typing import Optional


class AudioPlayer:
    def __init__(self, 
                 sample_rate: int = 16000,
                 channels: int = 1,
                 sample_width: int = 2,  # 2 = 16bit
                 device_index: Optional[int] = None,
                 frames_per_buffer: int = 1024):
        
        self.sample_rate = sample_rate
        self.channels = channels
        self.sample_width = sample_width
        self.frames_per_buffer = frames_per_buffer
        
        self.p = pyaudio.PyAudio()
        self.stream = None
        self.is_playing = False
        
        # PyAudio 포맷 매핑
        format_map = {1: pyaudio.paInt8, 2: pyaudio.paInt16, 4: pyaudio.paInt32}
        self.format = format_map.get(sample_width, pyaudio.paInt16)
        
        self.device_index = device_index
        
    def start(self):
        """오디오 스트림 시작"""
        if self.stream is None:
            self.stream = self.p.open(
                format=self.format,
                channels=self.channels,
                rate=self.sample_rate,
                output=True,
                output_device_index=self.device_index,
                frames_per_buffer=self.frames_per_buffer
            )
        self.is_playing = True
        print(f"[AUDIO] 출력 시작: {self.sample_rate}Hz, {self.channels}ch, {self.sample_width*8}bit")
    
    def stop(self):
        """오디오 스트림 중지"""
        self.is_playing = False
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
            self.stream = None
        print("[AUDIO] 출력 중지")
    
    def play_chunks(self, chunks: list[bytes]):
        """청크 리스트를 재생"""
        if not self.is_playing or not self.stream:
            return
        
        for chunk in chunks:
            if not self.is_playing:
                break
            if chunk and len(chunk) > 0:
                try:
                    self.stream.write(chunk)
                except Exception as e:
                    print(f"[AUDIO ERROR] 재생 실패: {e}")
                    break
    
    def close(self):
        """리소스 정리"""
        self.stop()
        if self.p:
            self.p.terminate()

