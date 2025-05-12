# TTS App Server

TTS App Server는 **텍스트-투-스피치(TTS)** 기능을 TCP 소켓으로 제공하는 경량 서버입니다.  
`facebook/mms-tts-kor` 모델을 기본으로 사용하며, CUDA GPU가 있으면 자동으로 활용합니다.

## 환경변수

| 변수명             | 기본값      | 설명            |
| --------------- | -------- | ------------- |
| `TTS_HOST`      | 0.0.0.0  | 바인딩 IP        |
| `TTS_PORT`      | 2501     | 리스닝 포트        |
| `TTS_TIMEOUT`   | 10       | 응답지연 타임아웃(초) |
| `TTS_CHECKCODE` | 20250326 | 프로토콜 버전/검증 코드 |

## run

```bash
python app.py --env ../.env

pm2 start app.py --name "ttsApp Server" --interpreter python -- --env ../.env
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

