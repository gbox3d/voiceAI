# STT App 서버

STT App 서버는 실시간 음성 스트리밍을 통해 오디오 데이터를 텍스트로 변환해 주는 고성능 비동기 STT(음성-텍스트 변환) 서비스입니다. TCP 기반 통신 프로토콜을 사용하여 다양한 클라이언트(C/C++, C#, Java, Python 등)에서 손쉽게 연동할 수 있도록 설계되었습니다.

## 주요 기능

* **비동기 처리**: 대기 시간을 최소화하고 서버 처리량을 극대화합니다.
* **다중 오디오 포맷 지원**: WAV, MP3, WebM, MP4 등 다양한 포맷 처리
* **간단한 TCP 프로토콜**: 구조화된 헤더와 페이로드로 안정적인 데이터 전송
* **플랫폼 독립성**: 데스크탑, 임베디드 시스템, 모바일 환경 모두 지원

## 설치
```bash

pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu128

pip install transformers accelerate pydub python-dotenv
```


## 실행
```bash
pm2 start app.py --name "sttApp Server" --interpreter python -- --env ../.env

python app.py --env ../.env
```

## 프로토콜 사양

서버-클라이언트 통신에 사용하는 TCP 기반 메시지 프레임워크는 별도의 [프로토콜 문서](asr_protocol.md)에서 상세히 설명합니다.


## 참고
https://huggingface.co/openai/whisper-large-v3-turbo  
https://huggingface.co/ghost613/whisper-large-v3-turbo-korean  



