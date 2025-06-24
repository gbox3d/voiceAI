# TTS App Server

TTS App Server는 **텍스트-투-스피치(TTS)** 기능을 TCP 소켓으로 제공하는 경량 서버입니다.  
이 서버는 **OpenVoice**와 **MeloTTS** 라이브러리를 기반으로 하며, 다양한 음성 합성 모델을 지원합니다.

## 환경변수

| 변수명             | 기본값      | 설명            |
| --------------- | -------- | ------------- |
| `TTS_HOST`      | 0.0.0.0  | 바인딩 IP        |
| `TTS_PORT`      | 2501     | 리스닝 포트        |
| `TTS_TIMEOUT`   | 10       | 응답지연 타임아웃(초) |
| `TTS_CHECKCODE` | 20250326 | 프로토콜 버전/검증 코드 |

## setup

### openvoice environment


**python3.10 버전 권장**   

```bash

# 가상환경 설정
cd ~/work/voiceAI          # 프로젝트 루트
python -m venv .venv_ov
source .venv_ov/bin/activate   # Windows면 .venv_ov\Scripts\activate
python -m pip install -U pip

# PyTorch + Torchaudio
#pip install torch==2.2.2+cu118 torchaudio==2.2.2+cu118 --index-url https://download.pytorch.org/whl/cu118 
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu128

# 가상환경 권장
pip install git+https://github.com/myshell-ai/OpenVoice.git
pip install git+https://github.com/myshell-ai/MeloTTS.git
python -m unidic download           # 일본어 토크나이저 의존성

pip install python-dotenv

```


## run

```bash
python app.py --env ../.env

pm2 start app.py --name "ttsApp Server" --interpreter python -- --env ../.env


# web api
python server_fastapi.py --port 21032
pm2 start server_fastapi.py --name "ttsAPI Server" --interpreter python -- --port 21032

```

## 예시

```python
import socket, struct

HOST, PORT = '127.0.0.1', 2501
text = "안녕하세요, TTS 서버 테스트입니다."
body = struct.pack('!I', len(text)) + text.encode()

header = bytearray(32)
header[0:4] = b'TTS1'         # CHECKCODE
header[4]   = 0x01            # REQ_TTS
header[5]   = 0x02            # FORMAT: 2 = mp3
# 나머지 필드는 서버에서 채움

with socket.create_connection((HOST, PORT)) as s:
    s.sendall(header + body)
    resp_hdr = s.recv(32)
    status = resp_hdr[4]
    size   = struct.unpack('!I', resp_hdr[16:20])[0]
    audio  = s.recv(size)
    open('out.mp3', 'wb').write(audio)
```


