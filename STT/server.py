# filename: server.py
# Author: gbox3d (modified for torchaudio)
# Created: 2025-02-18
# Description: STT App Server with torchaudio for offline multi-format decoding

import asyncio
import struct
import sys
import os
import io
import re

import torch
import numpy as np
import torchaudio

from transformers import AutoModelForSpeechSeq2Seq, AutoProcessor, pipeline

#---------------------------------------------------------
# 1. 다양한 포맷을 처리하기 위한 디코딩 함수 (torchaudio)
#---------------------------------------------------------
def decode_audio(audio_data: bytes, audio_format: str):
    """
    - audio_data: raw bytes from client
    - audio_format: str format label (wav, mp3, webm, mp4, ...)
    Returns: (waveform: np.ndarray [T], sample_rate: int)
    """
    # torchaudio.load은 파일 경로 또는 file-like 객체 지원
    buf = io.BytesIO(audio_data)
    waveform, sample_rate = torchaudio.load(buf)
    # waveform: Tensor [channels, time]
    # 멀티채널일 경우 mono로 변환
    if waveform.size(0) > 1:
        waveform = waveform.mean(dim=0, keepdim=True)
    # 1채널으로 축소 후 numpy array
    samples = waveform.squeeze(0).cpu().numpy().astype(np.float32)
    return samples, sample_rate

#---------------------------------------------------------
# 2. 비동기 서버 클래스
#---------------------------------------------------------
class AsrServer:
    SUCCESS = 0
    ERR_CHECKCODE_MISMATCH = 1
    ERR_INVALID_DATA = 2
    ERR_INVALID_REQUEST = 3
    ERR_INVALID_PARAMETER = 4
    ERR_INVALID_FORMAT = 5
    ERR_UNKNOWN_CODE = 8
    ERR_EXCEPTION = 9
    ERR_TIMEOUT = 10

    __VERSION__ = "1.0.1"

    def __init__(self, host=None, port=None, timeout=None, checkcode=None, stt_pipeline=None,
                 min_text_length=5, no_voice_text="novoice"):
        print(f"torch.__version__={torch.__version__}")
        print(f"torchaudio.__version__={torchaudio.__version__}")
        self.host = host or os.getenv("ASR_HOST", "localhost")
        self.port = port or int(os.getenv("ASR_PORT", 26070))
        self.timeout = int(timeout) if timeout is not None else int(os.getenv("ASR_TIMEOUT", 10))
        self.checkcode = checkcode or int(os.getenv("ASR_CHECKCODE", 20250122))
        self.stt_pipeline = stt_pipeline
        self.min_text_length = min_text_length
        self.no_voice_text = no_voice_text

    async def receive_data_with_timeout(self, reader, size, label):
        try:
            data = await asyncio.wait_for(reader.readexactly(size), timeout=self.timeout)
            return data
        except asyncio.TimeoutError:
            print(f"[ERROR] {label} 수신 타임아웃 발생")
            return None
        except Exception as e:
            print(f"[ERROR] {label} 수신 중 예외 발생: {e}")
            return None

    def is_meaningful_speech(self, text):
        if text is None or len(text.strip()) < self.min_text_length:
            return False
        noise_patterns = ["음", "어", "아", "흠", "음...", "어...", "아...", "음~", "어~", "아~"]
        words = text.strip().split()
        if all(w in noise_patterns for w in words):
            return False
        if re.match(r'^[\d\W]+$', text.strip()):
            return False
        return True

    async def process_audio(self, waveform, sr):
        try:
            result = self.stt_pipeline({"array": waveform, "sampling_rate": sr})
            text = result.get("text", "").strip()
            return text if self.is_meaningful_speech(text) else self.no_voice_text
        except Exception as e:
            print(f"[ERROR] 음성 처리 중 오류 발생: {e}")
            return self.no_voice_text

    async def handle_client(self, reader, writer):
        addr = writer.get_extra_info('peername')
        print(f"[INFO] 클라이언트 연결됨: {addr}")
        try:
            header = await reader.readexactly(8)
            checkcode, request_code = struct.unpack('!ii', header)
            if checkcode != self.checkcode:
                writer.write(struct.pack('!iiB', self.checkcode, request_code, self.ERR_CHECKCODE_MISMATCH))
                await writer.drain()
                return

            if request_code == 99:
                writer.write(struct.pack('!iiB', self.checkcode, request_code, self.SUCCESS))
                await writer.drain()
                return

            if request_code == 0x01:
                fmt_byte = await self.receive_data_with_timeout(reader, 1, "Format Code")
                fmt_code = struct.unpack('!B', fmt_byte)[0]
                fmt_map = {1:"wav",2:"mp3",3:"webm",4:"mp4"}
                if fmt_code not in fmt_map:
                    writer.write(struct.pack('!iiB', self.checkcode, request_code, self.ERR_INVALID_FORMAT))
                    await writer.drain()
                    return
                fmt_str = fmt_map[fmt_code]
                size_b = await self.receive_data_with_timeout(reader, 4, "Audio Size")
                size = struct.unpack('!i', size_b)[0]
                audio_bytes = await self.receive_data_with_timeout(reader, size, "Audio Data")

                # decode with torchaudio
                waveform, sr = decode_audio(audio_bytes, fmt_str)
                print(f"[INFO] Decoded: sr={sr}, len={len(waveform)}")
                text = await self.process_audio(waveform, sr)

                resp = text.encode('utf-8')
                header = struct.pack('!iiB', self.checkcode, request_code, self.SUCCESS)
                writer.write(header + struct.pack('!i', len(resp)) + resp)
                await writer.drain()
                return

            writer.write(struct.pack('!iiB', self.checkcode, request_code, self.ERR_UNKNOWN_CODE))
            await writer.drain()
        except Exception as e:
            print(f"[ERROR] 처리 예외: {e}")
        finally:
            writer.close()
            await writer.wait_closed()

    async def run_server(self):
        server = await asyncio.start_server(self.handle_client, self.host, self.port)
        print(f"[INFO] 서버 시작: {self.host}:{self.port}, TIMEOUT={self.timeout}s, CHECKCODE={self.checkcode}")
        async with server:
            await server.serve_forever()

if __name__ == "__main__":
    device = "cuda:0" if torch.cuda.is_available() else "cpu"
    torch_dtype = torch.float16 if torch.cuda.is_available() else torch.float32
    model_id="openai/whisper-large-v3"
    model = AutoModelForSpeechSeq2Seq.from_pretrained(model_id, torch_dtype=torch_dtype, low_cpu_mem_usage=True, use_safetensors=True).to(device)
    proc = AutoProcessor.from_pretrained(model_id)
    stt = pipeline(task="automatic-speech-recognition", model=model, tokenizer=proc.tokenizer, feature_extractor=proc.feature_extractor, device=0 if device.startswith("cuda") else -1)
    srv=AsrServer(host="0.0.0.0", port=2500, timeout=10, checkcode=20250122, stt_pipeline=stt, min_text_length=5, no_voice_text="novoice")
    asyncio.run(srv.run_server())
