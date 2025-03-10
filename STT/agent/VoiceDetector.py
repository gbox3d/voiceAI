import pyaudio #pip install pyaudio
import wave
import numpy as np
import webrtcvad # pip install webrtcvad
import struct
import time
from datetime import datetime
import os
from scipy.fftpack import fft
import json


class VoiceDetector:
    """음성 감지를 위한 클래스"""
    
    # 기본 설정값 (클래스 상수)
    DEFAULT_SETTINGS = {
        # VAD 및 감지 설정
        "vad_mode": 0,                 # VAD 감도 (0: 낮음 ~ 3: 높음)
        "voice_threshold": 300,        # 음성 감지 임계값
        "required_speech_frames": 3,   # 연속 감지 필요 프레임 수
        "human_freq_low": 85,          # 사람 목소리 주파수 하한 (Hz)
        "human_freq_high": 255,        # 사람 목소리 주파수 상한 (Hz)
        "smoothing_factor": 0.3,       # RMS 스무딩 계수 (낮을수록 부드러움)
        "use_rms": True,               # RMS 분석 사용 여부
        "use_freq": True,              # 주파수 분석 사용 여부
        
        # 오디오 설정
        "format": pyaudio.paInt16,     # 오디오 형식
        "channels": 1,                 # 채널 수
        "rate": 16000,                 # 샘플링 레이트 (Hz)
        "chunk": 480                   # 청크 크기 (샘플 수)
    }
    
    # VAD 지원 샘플링 레이트
    SUPPORTED_VAD_RATES = [8000, 16000, 32000, 48000]
    
    # 설정 파일 기본 경로
    DEFAULT_SETTINGS_PATH = "./temp/voice_detector_settings.json"
    
    
    def __init__(self, debug_mode=False, settings_path=None):
        # 설정 파일 경로
        self.settings_path = settings_path or self.DEFAULT_SETTINGS_PATH
        
        # 상태 변수 - debug_mode를 먼저 설정
        self.consecutive_speech = 0
        self.debug_mode = debug_mode
        
        # 스무딩을 위한 변수
        self.smoothed_rms = 0
        
        # 설정값 초기화 (파일에서 로드하거나 기본값 사용)
        self._load_or_init_settings()
        
        # VAD 설정
        self.vad = webrtcvad.Vad()
        self.vad.set_mode(self.vad_mode)
        
        # PyAudio 초기화 및 스트림 (탐지에만 필요할 경우 사용)
        self.p = None
        self.stream = None
    
    def _load_or_init_settings(self):
        """설정 파일에서 설정을 로드하거나 기본값으로 초기화"""
        # 기본 설정값으로 먼저 초기화
        self.vad_mode = self.DEFAULT_SETTINGS["vad_mode"]
        self.VOICE_THRESHOLD = self.DEFAULT_SETTINGS["voice_threshold"]
        self.required_speech_frames = self.DEFAULT_SETTINGS["required_speech_frames"]
        self.human_freq_low = self.DEFAULT_SETTINGS["human_freq_low"]
        self.human_freq_high = self.DEFAULT_SETTINGS["human_freq_high"]
        self.smoothing_factor = self.DEFAULT_SETTINGS["smoothing_factor"]
        self.use_rms = self.DEFAULT_SETTINGS["use_rms"]
        self.use_freq = self.DEFAULT_SETTINGS["use_freq"]
        
        # 오디오 설정 초기화
        self.FORMAT = self.DEFAULT_SETTINGS["format"]
        self.CHANNELS = self.DEFAULT_SETTINGS["channels"]
        self.RATE = self.DEFAULT_SETTINGS["rate"]
        self.CHUNK = self.DEFAULT_SETTINGS["chunk"]
        
        # 파일이 존재하면 설정 불러오기
        try:
            self.load_settings(self.settings_path)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            # 파일이 없거나 손상되었으면 기본값 사용
            if self.debug_mode:
                print(f"설정 파일 로드 실패, 기본값 사용: {e}")
    
    def get_current_settings(self):
        """현재 설정값 딕셔너리 반환"""
        return {
            # VAD 및 감지 설정
            "vad_mode": self.vad_mode,
            "voice_threshold": self.VOICE_THRESHOLD,
            "required_speech_frames": self.required_speech_frames,
            "human_freq_low": self.human_freq_low,
            "human_freq_high": self.human_freq_high,
            "smoothing_factor": self.smoothing_factor,
            "use_rms": self.use_rms,
            "use_freq": self.use_freq,
            
            # 오디오 설정
            "format": self.FORMAT,
            "channels": self.CHANNELS,
            "rate": self.RATE,
            "chunk": self.CHUNK
        }
    
    def apply_settings(self, settings):
        """설정값 딕셔너리를 적용"""
        # 각 설정값 적용 (존재하는 키만)
        # VAD 및 감지 설정 적용
        if "vad_mode" in settings:
            self.vad_mode = settings["vad_mode"]
            # VAD 모드 즉시 적용
            if hasattr(self, 'vad'):
                self.vad.set_mode(self.vad_mode)
        
        if "voice_threshold" in settings:
            self.VOICE_THRESHOLD = settings["voice_threshold"]
        
        if "required_speech_frames" in settings:
            self.required_speech_frames = settings["required_speech_frames"]
        
        if "human_freq_low" in settings:
            self.human_freq_low = settings["human_freq_low"]
        
        if "human_freq_high" in settings:
            self.human_freq_high = settings["human_freq_high"]
        
        if "smoothing_factor" in settings:
            self.smoothing_factor = settings["smoothing_factor"]
            
        if "use_rms" in settings:
            self.use_rms = settings["use_rms"]
            
        if "use_freq" in settings:
            self.use_freq = settings["use_freq"]
        
        # 오디오 설정 적용
        audio_settings_changed = False
        
        if "format" in settings:
            self.FORMAT = settings["format"]
            audio_settings_changed = True
        
        if "channels" in settings:
            # print(settings["channels"])
            self.CHANNELS = settings["channels"]
            audio_settings_changed = True
        
        if "rate" in settings:
            # VAD 지원 샘플링 레이트인지 확인
            if settings["rate"] in self.SUPPORTED_VAD_RATES:
                self.RATE = settings["rate"]
                audio_settings_changed = True
            else:
                if self.debug_mode:
                    print(f"경고: {settings['rate']}Hz는 WebRTC VAD가 지원하지 않습니다. 지원 레이트: {self.SUPPORTED_VAD_RATES}")
        
        if "chunk" in settings:
            self.CHUNK = settings["chunk"]
            audio_settings_changed = True
        
        # 오디오 설정이 변경된 경우 스트림 재초기화
        if audio_settings_changed and self.stream is not None:
            self._reinitialize_stream()
            
        return audio_settings_changed
    
    def _reinitialize_stream(self):
        """오디오 설정 변경 후 스트림 재초기화"""
        # 현재 장치 인덱스 저장
        device_index = None
        if hasattr(self.stream, '_device_index'):
            device_index = self.stream._device_index
            
        # 기존 스트림 종료
        self.stream.stop_stream()
        self.stream.close()
        
        # 새 설정으로 스트림 재생성
        self.stream = self.p.open(
            format=self.FORMAT,
            channels=self.CHANNELS,
            rate=self.RATE,
            input=True,
            input_device_index=device_index,
            frames_per_buffer=self.CHUNK
        )
        
        if self.debug_mode:
            print(f"오디오 설정 변경됨: 레이트={self.RATE}Hz, 청크={self.CHUNK}")
    
    def save_settings(self, file_path=None):
        """현재 설정을 파일에 저장"""
        # 경로가 없으면 기본 경로 사용
        file_path = file_path or self.settings_path
        
        # 현재 설정 가져오기
        settings = self.get_current_settings()
        
        # JSON 파일로 저장
        try:
            # 디렉토리가 없으면 생성
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(settings, f, indent=4)
            
            if self.debug_mode:
                print(f"설정이 '{file_path}'에 저장되었습니다.")
            return True
        except Exception as e:
            if self.debug_mode:
                print(f"설정 저장 오류: {e}")
            return False
    
    def load_settings(self, file_path=None):
        """파일에서 설정 불러오기"""
        # 경로가 없으면 기본 경로 사용
        file_path = file_path or self.settings_path
        
        try:
            # 파일 존재 확인
            if not os.path.exists(file_path):
                if self.debug_mode:
                    print(f"설정 파일 '{file_path}'이 존재하지 않습니다.")
                return False
            
            # JSON 파일 로드
            with open(file_path, 'r', encoding='utf-8') as f:
                settings = json.load(f)
            
            # 설정 적용
            self.apply_settings(settings)
            
            if self.debug_mode:
                print(f"'{file_path}'에서 설정을 로드했습니다.")
            return True
        except Exception as e:
            if self.debug_mode:
                print(f"설정 로드 오류: {e}")
            return False
    
    def reset_to_defaults(self):
        """설정을 기본값으로 초기화"""
        self.apply_settings(self.DEFAULT_SETTINGS)
        if self.debug_mode:
            print("설정이 기본값으로 초기화되었습니다.")
        return True
    
    def initialize_stream(self, device_index=None):
        """필요한 경우 스트림 초기화 (특정 장치 선택 가능)"""
        if self.p is None:
            self.p = pyaudio.PyAudio()
        
        if self.stream is None:
            self.stream = self.p.open(
                format=self.FORMAT,
                channels=self.CHANNELS,
                rate=self.RATE,
                input=True,
                input_device_index=device_index,  # 선택된 장치 인덱스 사용
                frames_per_buffer=self.CHUNK
            )
            # 장치 인덱스 저장 (나중에 재초기화할 때 사용)
            if device_index is not None:
                self.stream._device_index = device_index
    
    
    def get_audio_devices(self):
        """시스템에서 사용 가능한 모든 오디오 입력 장치 목록 반환"""
        if self.p is None:
            self.p = pyaudio.PyAudio()
        
        devices = []
        info = []
        
        # 모든 장치 정보 가져오기
        for i in range(self.p.get_device_count()):
            device_info = self.p.get_device_info_by_index(i)
            # 입력 채널이 있는 장치만 선택 (마이크)
            if device_info['maxInputChannels'] > 0:
                name = device_info['name']
                devices.append(f"{i}: {name}")
                info.append({
                    'index': i,
                    'name': name,
                    'channels': device_info['maxInputChannels'],
                    'sample_rate': int(device_info['defaultSampleRate'])
                })
        
        return devices, info
    
    def close_stream(self):
        """스트림 및 PyAudio 리소스 정리"""
        if self.stream is not None:
            self.stream.stop_stream()
            self.stream.close()
            self.stream = None
        
        if self.p is not None:
            self.p.terminate()
            self.p = None
    
    def calibrate(self):
        """주변 환경 소음을 측정하여 임계값 자동 조정"""
        print("환경 소음 측정 중... (10초)")
        
        # 필요한 경우 스트림 초기화
        self.initialize_stream()
        
        samples = []
        
        # 10초 동안 샘플 수집 (5초에서 10초로 증가)
        for _ in range(int(self.RATE / self.CHUNK * 10)):
            audio_data = self.stream.read(self.CHUNK, exception_on_overflow=False)
            rms = self.get_rms(audio_data)
            samples.append(rms)
        
        # 배경 소음 레벨 계산 (하위 80%의 평균 사용)
        samples.sort()
        valid_samples = samples[:int(len(samples) * 0.8)]  # 상위 20% 제외 (일시적 소음 제거)
        background_noise = np.mean(valid_samples)
        noise_std = np.std(valid_samples)
        
        # 임계값 설정 (배경 소음 + 표준편차의 4배)
        self.VOICE_THRESHOLD = background_noise + noise_std * 4.0
        
        print(f"측정 완료. 배경 소음 레벨: {background_noise:.2f}")
        print(f"음성 감지 임계값: {self.VOICE_THRESHOLD:.2f}로 설정됨")
    
    def detect_speech(self, audio_data):
        """개선된 음성 감지 로직 - 내부 설정 사용
        
        Args:
            audio_data: 분석할 오디오 데이터
            
        Returns:
            tuple: (speech_detected, vad_result, rms_value, rms_result, freq_result)
                - speech_detected: 최종 음성 감지 여부
                - vad_result: VAD 결과
                - rms_value: 계산된 RMS 값
                - rms_result: RMS 분석 결과
                - freq_result: 주파수 분석 결과
        """
        # WebRTC VAD로 음성 감지 (항상 실행)
        try:
            vad_result = self.vad.is_speech(audio_data, self.RATE)
        # except:
        #     print("VAD 오류")
        #     vad_result = False
        except Exception as e:
            if self.debug_mode:
                print(f"VAD 오류: {e}")
            vad_result = False
        
        # RMS 기반 감지 (선택적 실행)
        rms = self.get_rms(audio_data)
        self.smoothed_rms = self.smoothing_factor * rms + (1 - self.smoothing_factor) * self.smoothed_rms
        rms_result = self.smoothed_rms > self.VOICE_THRESHOLD if self.use_rms else False
        
        # 주파수 분석 기반 감지 (선택적 실행)
        if self.use_freq:
            freq_result = self.check_human_freq(audio_data)
        else:
            freq_result = False
        
        # 디버그 모드에서는 상세 정보 출력
        if self.debug_mode:
            # 각 조건별 아이콘 표시
            vad_icon = "✓" if vad_result else "✗"
            rms_icon = "✓" if rms_result else "✗"
            freq_icon = "✓" if freq_result else "✗"
            
            # 최종 결정 로직 (선택에 따라 다름)
            if self.use_rms and self.use_freq:
                speech = "🗣️" if (vad_result and (rms_result or freq_result)) else "  "
            elif self.use_rms:
                speech = "🗣️" if (vad_result and rms_result) else "  "
            elif self.use_freq:
                speech = "🗣️" if (vad_result and freq_result) else "  "
            else:
                speech = "🗣️" if vad_result else "  "
            
            # 디버그 정보 상세 출력
            print(f"VAD: {vad_icon}, RMS: {rms_icon}({self.smoothed_rms:.1f}/{self.VOICE_THRESHOLD:.1f}), FREQ: {freq_icon} {speech}", end='\r')
        
        # 최종 결과 결정 (선택에 따라 다름)
        if self.use_rms and self.use_freq:
            # 둘 다 사용하는 경우 - 하나라도 True면 충분
            speech_detected = vad_result and (rms_result or freq_result)
        elif self.use_rms:
            # RMS만 사용하는 경우
            speech_detected = vad_result and rms_result
        elif self.use_freq:
            # 주파수만 사용하는 경우
            speech_detected = vad_result and freq_result
        else:
            # 둘 다 사용하지 않는 경우 - VAD로만 판단
            speech_detected = vad_result
        
        # 연속적인 음성 프레임 카운팅 및 관리
        if speech_detected:
            self.consecutive_speech += 1
        else:
            self.consecutive_speech = 0
        
        # 결과 반환
        return speech_detected, vad_result, self.smoothed_rms, rms_result, freq_result
    
    def is_speech_continuous(self):
        """지정된 연속 프레임 이상 음성이 감지되었는지 확인"""
        return self.consecutive_speech >= self.required_speech_frames
    
    def check_human_freq(self, audio_data):
        """사람 목소리 주파수 대역 확인"""
        try:
            # 데이터를 float32로 변환
            count = len(audio_data) // 2
            format_str = "%dh" % count
            shorts = struct.unpack(format_str, audio_data)
            data = np.array(shorts).astype(np.float32) / 32768.0  # 정규화
            
            # FFT 수행
            fft_data = fft(data)
            # 주파수 성분 계산
            fft_freqs = np.fft.fftfreq(len(data), 1.0/self.RATE)
            
            # 사람 목소리 주파수 대역의 파워 계산
            voice_freq_mask = (fft_freqs >= self.human_freq_low) & (fft_freqs <= self.human_freq_high)
            all_freq_power = np.sum(np.abs(fft_data))
            
            if all_freq_power == 0:
                return False
                
            voice_freq_power = np.sum(np.abs(fft_data[voice_freq_mask]))
            voice_power_ratio = voice_freq_power / all_freq_power
            
            # 사람 목소리 대역의 파워가 전체의 10% 이상이면 사람 목소리로 판단 (20% → 10%로 완화)
            return voice_power_ratio > 0.1
            
        except Exception as e:
            if self.debug_mode:
                print(f"주파수 분석 오류: {e}")
            return True  # 오류 시 기본값으로 True 반환
    
    def get_rms(self, audio_data):
        """오디오 데이터의 RMS(Root Mean Square) 값 계산"""
        count = len(audio_data) // 2
        format_str = "%dh" % count
        try:
            shorts = struct.unpack(format_str, audio_data)
            shorts_array = np.array(shorts).astype(np.float32)
            sum_squares = np.sum(shorts_array ** 2)
            rms = np.sqrt(max(0, sum_squares / count))
            return rms
        except Exception as e:
            if self.debug_mode:
                print(f"RMS 계산 오류: {e}")
            return 0
    
    def get_format_name(self, format_value):
        """포맷 값을 사람이 읽을 수 있는 이름으로 변환"""
        format_names = {
            pyaudio.paInt8: "8-bit Integer",
            pyaudio.paInt16: "16-bit Integer",
            pyaudio.paInt24: "24-bit Integer",
            pyaudio.paInt32: "32-bit Integer",
            pyaudio.paFloat32: "32-bit Float"
        }
        return format_names.get(format_value, f"Unknown ({format_value})")
    
    def get_audio_settings_summary(self):
        """현재 오디오 설정 요약 정보 반환"""
        return {
            "format": self.get_format_name(self.FORMAT),
            "channels": self.CHANNELS,
            "rate": f"{self.RATE} Hz",
            "chunk": f"{self.CHUNK} samples ({self.CHUNK / self.RATE * 1000:.1f} ms)"
        }

        
        
    
# 사용 예시
if __name__ == "__main__":
    # 디버그 모드로 설정
    detector = VoiceDetector(debug_mode=True)
    
    # 오디오 설정 요약 정보 가져오기
    audio_settings = detector.get_audio_settings_summary()
    
    # 모든 설정값 가져오기
    all_settings = detector.get_current_settings()
    
    # 출력
    print("===== 오디오 샘플링 정보 =====")
    print(f"포맷: {audio_settings['format']}")
    print(f"채널: {audio_settings['channels']}")
    print(f"샘플링 레이트: {audio_settings['rate']}")
    print(f"청크 크기: {audio_settings['chunk']}")
    
    print("\n===== VAD 관련 설정 =====")
    print(f"VAD 모드: {all_settings['vad_mode']} (0: 낮음 ~ 3: 높음)")
    print(f"VAD 지원 샘플링 레이트: {detector.SUPPORTED_VAD_RATES}")
    
    # 프레임 크기 검증 (VAD 호환성)
    chunk_samples = detector.CHUNK
    chunk_ms = (chunk_samples * 1000) / detector.RATE
    
    print(f"\n현재 청크 크기: {chunk_samples} 샘플 ({chunk_ms:.1f}ms)")
    
    # VAD 유효 프레임 크기 (16kHz 기준)
    valid_ms = [10, 20, 30]
    valid_samples = [detector.RATE // 100, detector.RATE // 50, detector.RATE // 33]
    
    print("VAD 유효 프레임 크기:")
    for ms, samples in zip(valid_ms, valid_samples):
        print(f"- {ms}ms = {samples} 샘플")
    
    # 현재 설정이 유효한지 확인
    if chunk_samples in valid_samples:
        print(f"\n현재 청크 크기 {chunk_samples}는 VAD에 유효합니다.")
    else:
        print(f"\n경고: 현재 청크 크기 {chunk_samples}는 VAD에 유효하지 않을 수 있습니다.")
        print("VAD는 10ms, 20ms, 30ms 프레임 길이만 지원합니다.")
     
    # 스트림 초기화 (기본 마이크 사용)
    detector.initialize_stream()
    
    print("VAD 테스트 시작... Ctrl+C로 종료")
    
    try:
        while True:
            # 오디오 데이터 읽기
            audio_data = detector.stream.read(detector.CHUNK, exception_on_overflow=False)
            
            # 음성 감지 (디버그 출력 자동으로 표시됨)
            detector.detect_speech(audio_data)
            
            # CPU 사용량 줄이기
            time.sleep(0.01)
    
    except KeyboardInterrupt:
        print("\n테스트 종료")
    finally:
        # 리소스 정리
        detector.close_stream()