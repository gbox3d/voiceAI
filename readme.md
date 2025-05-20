## environment setup

```bash
#STT 서버 설정
ASR_HOST=0.0.0.0
ASR_PORT=21030
ASR_CHECKCODE=20250218
ASR_TIMEOUT=10

# TTS 서버 설정
TTS_HOST=0.0.0.0
TTS_PORT=21031
TTS_TIMEOUT=10
TTS_CHECKCODE=20250326

# rest api 서버 설정
MONGO_URL=mongodb+srv://clusert_name:passwd@clustermisoagidev.dysrt.mongodb.net/
DB_NAME=devdb_001
JWT_SECRET=**********

STATIC_ASSET = ./public
ELEVENLABS_API_KEY=sk_**********
PORT=21040


SSL=False
```

## STT

[STT readme.md](STT/readme.md)

## TTS

[TTS readme.md](TTS/readme.md)

### setup

```bash

# 가상환경 설정
cd ~/work/voiceAI          # 프로젝트 루트
python -m venv .venv_ov
source .venv_ov/bin/activate   # Windows면 .venv_ov\Scripts\activate
python -m pip install -U pip

# PyTorch + Torchaudio
pip install torch==2.2.2+cu118 torchaudio==2.2.2+cu118 \
    --index-url https://download.pytorch.org/whl/cu118

# 가상환경 권장
pip install git+https://github.com/myshell-ai/OpenVoice.git
pip install git+https://github.com/myshell-ai/MeloTTS.git
python -m unidic download           # 일본어 토크나이저 의존성

```
### Api server




