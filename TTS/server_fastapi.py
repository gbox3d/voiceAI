# filename: server_fastapi_class.py
# author: gbox3d
# created: 2025-05-20
# 이 주석은 수정하지 마세요.

import os, io, tempfile, argparse
from typing import Literal

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel
from melo.api import TTS
from pydub import AudioSegment
import uvicorn

from fastapi.middleware.cors import CORSMiddleware

class TTSRequest(BaseModel):
    text: str
    format: Literal["wav", "mp3"] = "mp3"
    speed: float = 1.0             # 0.5 ~ 2.0

class TTSWebAPI:
    """MeloTTS + FastAPI 서버를 하나의 클래스에 캡슐화"""
    def __init__(self, host="0.0.0.0", port=8000,
                 language="KR", device="cuda", spk_id=0):
        self.host, self.port = host, port
        self.engine = TTS(language=language, device=device)
        self.spk_id = spk_id
        self.app = FastAPI(
            title="MeloTTS Web API",
            version="1.0.0",
            description="클래스 기반 FastAPI TTS 서비스",
        )
        
        # CORS 설정
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["http://106.255.251.154:21038"],  # 또는 ["*"]
            allow_methods=["POST", "OPTIONS"],
            allow_headers=["Content-Type", "Authorization"],
            expose_headers=["Content-Disposition"],        # 다운로드용
            allow_credentials=True,                        # 필요 시
        )
        
        self.register_routes()

    # ──────────────────────────────────────────────
    # 내부 유틸
    # ──────────────────────────────────────────────
    def _synthesize_wav(self, text: str, speed: float) -> bytes:
        tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        path = tmp.name
        tmp.close()
        self.engine.tts_to_file(text, self.spk_id, path, speed=speed, quiet=True)
        with open(path, "rb") as f:
            data = f.read()
        os.remove(path)
        return data

    @staticmethod
    def _wav_to_mp3(wav_bytes: bytes) -> bytes:
        buf_in = io.BytesIO(wav_bytes)
        audio = AudioSegment.from_file(buf_in, format="wav")
        buf_out = io.BytesIO()
        audio.export(buf_out, format="mp3", bitrate="192k")
        buf_out.seek(0)
        return buf_out.read()

    # ──────────────────────────────────────────────
    # 라우트 등록
    # ──────────────────────────────────────────────
    def register_routes(self):
        """클로저 함수를 사용해 self 참조를 노출하지 않는다"""

        @self.app.get("/", response_class=JSONResponse)
        async def root():
            return {
                "service": "MeloTTS REST API (class version)",
                "version": "1.0.0",
                "endpoints": {
                    "POST /tts": "텍스트를 오디오로 변환",
                },
            }

        @self.app.post("/tts")
        async def tts_endpoint(req: TTSRequest):
            text = req.text.strip()
            if not text:
                raise HTTPException(400, "text 파라미터가 비어 있습니다.")

            wav_bytes = self._synthesize_wav(text, req.speed)

            if req.format == "wav":
                audio_bytes, media_type, fname = wav_bytes, "audio/wav", "speech.wav"
            else:
                audio_bytes = self._wav_to_mp3(wav_bytes)
                media_type, fname = "audio/mpeg", "speech.mp3"

            return StreamingResponse(
                io.BytesIO(audio_bytes),
                media_type=media_type,
                headers={"Content-Disposition": f'attachment; filename="{fname}"'},
            )

    # ──────────────────────────────────────────────
    # 서버 구동
    # ──────────────────────────────────────────────
    def run(self):
        uvicorn.run(self.app, host=self.host, port=self.port, log_level="info")


# 직접 실행
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--language", default="KR")
    parser.add_argument("--device", default="cuda")
    args = parser.parse_args()

    server = TTSWebAPI(
        host=args.host,
        port=args.port,
        language=args.language,
        device=args.device,
    )
    server.run()
