# config.py
import os
from dataclasses import dataclass

def _load_dotenv_if_available():
    # python-dotenv 있으면 사용, 없으면 간단 파서
    try:
        from dotenv import load_dotenv
        load_dotenv()
        return
    except Exception:
        pass
    # fallback: .env 직접 파싱 (키=값, # 주석)
    path = ".env"
    if not os.path.exists(path):
        return
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            k, v = k.strip(), v.strip()
            # 따옴표 제거
            if (v.startswith('"') and v.endswith('"')) or (v.startswith("'") and v.endswith("'")):
                v = v[1:-1]
            os.environ.setdefault(k, v)

def _to_bool(s: str, default=False):
    if s is None:
        return default
    return s.strip().lower() in ("1", "true", "yes", "on")

def _to_int(s: str, default: int):
    try:
        return int(s)
    except Exception:
        return default

def _to_float(s: str, default: float):
    try:
        return float(s)
    except Exception:
        return default

@dataclass
class Config:
    # IO / VAD 서버
    io_host: str
    io_port: int
    io_checkcode: int
    io_ping_interval: float

    # 입력 (파일 테스트용)
    input_mp4: str | None
    input_rate: int
    input_channels: int
    input_chunk_ms: int

    # STT 서버
    stt_host: str
    stt_port: int
    stt_checkcode: int
    stt_per_request: bool

def load_config() -> Config:
    _load_dotenv_if_available()

    return Config(
        io_host=os.getenv("IO_HOST", "127.0.0.1"),
        io_port=_to_int(os.getenv("IO_PORT"), 26070),
        io_checkcode=_to_int(os.getenv("IO_CHECKCODE"), 20250918),
        io_ping_interval=_to_float(os.getenv("IO_PING_INTERVAL"), 5.0),

        input_mp4=os.getenv("INPUT_MP4", None),
        input_rate=_to_int(os.getenv("INPUT_RATE"), 16000),
        input_channels=_to_int(os.getenv("INPUT_CHANNELS"), 1),
        input_chunk_ms=_to_int(os.getenv("INPUT_CHUNK_MS"), 40),

        stt_host=os.getenv("STT_HOST", "127.0.0.1"),
        stt_port=_to_int(os.getenv("STT_PORT"), 22270),
        stt_checkcode=_to_int(os.getenv("STT_CHECKCODE"), 20250218),
        stt_per_request=_to_bool(os.getenv("STT_PER_REQUEST"), False),
    )
