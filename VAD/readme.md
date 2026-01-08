## 실행법

```bash
# 사용 가능한 오디오 출력 장치 목록

python TcpVadServer.py # 오디오 캡처 및 VAD 서버 실행 (기본값: 16000Hz, 모노)

python TcpVadServer.py --list-devices

python .\mp4_to_server.py .\media\test2.mp4 # mp4 파일을 서버로 스트리밍
python .\mp4_to_server.py .\media\test2.mp4 --delay 50 # 0.1초 지연 추가



```


## 환경 변수
- 서버 설정

VAD_HOST (서버 호스트, 기본 None → localhost 사용됨)

VAD_PORT (기본 26070)

VAD_TIMEOUT (기본 10초)

VAD_CHECKCODE (기본 20250918)

- 오디오 설정

VAD_AUTO_PLAY (True/False, 기본 True)

VAD_AUDIO_SAMPLE_RATE (기본 16000)

VAD_AUDIO_CHANNELS (기본 1)

VAD_AUDIO_DEVICE_INDEX (기본 -1 → None)

VAD_THRESHOLD (VAD 판정 임계값, 기본 0.5)

VAD_MIN_SPEECH_MS (최소 발화 길이, 기본 150ms)

VAD_MIN_SILENCE_MS (발화 종료 기준 침묵, 기본 300ms)

VAD_PRE_BUFFER_MS (발화 시작부 보호 버퍼, 기본 200ms)

- 재생 설정

VAD_PLAY_CHUNK_COUNT (기본 5개 청크 단위)

VAD_PLAY_INTERVAL (기본 0.1초 간격)

- 세그먼트 저장 설정

VAD_OUT_DIR (세그먼트 wav 저장 폴더, 기본 vad_segments)


## env 예시
```bash
# TCP 서버 설정
VAD_HOST=0.0.0.0
VAD_PORT=26070
VAD_TIMEOUT=10
VAD_CHECKCODE=20250918

# 오디오 입력/재생 설정
VAD_AUTO_PLAY=true
VAD_AUDIO_SAMPLE_RATE=16000
VAD_AUDIO_CHANNELS=1
VAD_AUDIO_DEVICE_INDEX=-1
VAD_THRESHOLD=0.5

# VAD 동작 파라미터
VAD_MIN_SPEECH_MS=150
VAD_MIN_SILENCE_MS=300
VAD_PRE_BUFFER_MS=200

# 오디오 재생 루프 설정
VAD_PLAY_CHUNK_COUNT=5
VAD_PLAY_INTERVAL=0.1

# 발화 구간 저장 설정
VAD_OUT_DIR=vad_segments
```