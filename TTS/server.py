# filename: server.py
# author: gbox3d
# created: 2025-03-26
# 이 주석은 수정하지 마세요.

import os
import asyncio
import struct
import io
import sys
import time
import tempfile

from melo.api import TTS             # MeloTTS 기본 한국어 TTS 엔진
from pydub import AudioSegment

class TTSServer:
    # 상태 코드 정의
    SUCCESS = 0
    ERR_CHECKCODE_MISMATCH = 1
    ERR_INVALID_DATA = 2
    ERR_INVALID_REQUEST = 3
    ERR_INVALID_PARAMETER = 4
    ERR_INVALID_FORMAT = 5
    ERR_UNKNOWN_CODE = 8
    ERR_EXCEPTION = 9
    ERR_TIMEOUT = 10
    
    # 요청 코드 정의
    REQ_TTS = 0x01
    REQ_PING = 99
    
    # 헤더 사이즈
    HEADER_SIZE = 32
    
    # 체크코드 (고정값)
    CHECKCODE = b'TTS1'

    def __init__(self, host="0.0.0.0", port=2501, language="KR", device="cuda"):
        self.host = host
        self.port = port
        # MeloTTS 모델 초기화
        self.tts = TTS(language=language, device=device)
        # 기본 화자 ID (단일/기본 화자 사용)
        self.spk_id = 0

    def generate_wav_bytes(self, text, speed=1.0):
        """텍스트에서 WAV 포맷 바이트를 생성"""
        # 임시 파일 생성
        tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        tmp_path = tmp.name
        tmp.close()
        # 파일로 합성
        self.tts.tts_to_file(text, self.spk_id, tmp_path, speed=speed)
        # 파일 읽기
        with open(tmp_path, 'rb') as f:
            wav_bytes = f.read()
        os.remove(tmp_path)
        return wav_bytes

    def convert_to_mp3_bytes(self, wav_bytes):
        """WAV 바이트를 MP3 바이트로 변환"""
        buf = io.BytesIO(wav_bytes)
        audio = AudioSegment.from_file(buf, format="wav")
        out_buf = io.BytesIO()
        audio.export(out_buf, format="mp3", bitrate="192k")
        out_buf.seek(0)
        return out_buf.read()

    def create_response_header(self, status_code, payload_size=0):
        """응답 헤더 생성"""
        header = bytearray(self.HEADER_SIZE)
        header[0:4] = self.CHECKCODE
        header[4:5] = struct.pack('!B', status_code)
        timestamp = int(time.time())
        header[8:16] = struct.pack('!Q', timestamp)
        header[16:20] = struct.pack('!I', payload_size)
        return header

    async def handle_tts_request(self, reader, writer, format_code):
        """TTS 요청 처리"""
        size_bytes = await reader.readexactly(4)
        text_size = int.from_bytes(size_bytes, 'big')
        text = (await reader.readexactly(text_size)).decode('utf-8')
        format_map = {1: 'wav', 2: 'mp3'}
        audio_format = format_map.get(format_code, 'mp3')
        try:
            # WAV 우선 생성
            wav_bytes = self.generate_wav_bytes(text)
            if audio_format == 'wav':
                audio_data = wav_bytes
            else:
                audio_data = self.convert_to_mp3_bytes(wav_bytes)
            # 응답 헤더 생성 및 전송
            header = self.create_response_header(self.SUCCESS, len(audio_data))
            writer.write(header + audio_data)
            await writer.drain()
            return True
        except Exception as e:
            print(f"[ERROR] 오디오 생성 오류: {e}")
            header = self.create_response_header(self.ERR_EXCEPTION)
            writer.write(header)
            await writer.drain()
            return False

    async def handle_ping_request(self, reader, writer):
        """Ping 요청 처리"""
        header = self.create_response_header(self.SUCCESS)
        writer.write(header)
        await writer.drain()
        return True

    async def handle_client(self, reader, writer):
        addr = writer.get_extra_info('peername')
        try:
            header = await reader.readexactly(self.HEADER_SIZE)
            if header[0:4] != self.CHECKCODE:
                writer.write(self.create_response_header(self.ERR_CHECKCODE_MISMATCH))
                await writer.drain()
                return
            req_code = header[4]
            fmt_code = header[5]
            if req_code == self.REQ_TTS:
                await self.handle_tts_request(reader, writer, fmt_code)
            elif req_code == self.REQ_PING:
                await self.handle_ping_request(reader, writer)
            else:
                writer.write(self.create_response_header(self.ERR_UNKNOWN_CODE))
                await writer.drain()
        except asyncio.IncompleteReadError:
            writer.write(self.create_response_header(self.ERR_INVALID_DATA))
            await writer.drain()
        finally:
            writer.close()
            await writer.wait_closed()

    async def run_server(self):
        server = await asyncio.start_server(self.handle_client, self.host, self.port)
        addr = server.sockets[0].getsockname()
        print(f"[INFO] MeloTTS 서버 시작: {addr}")
        async with server:
            await server.serve_forever()


def start_server(host="0.0.0.0", port=2501, language="KR", device="cuda"):
    tts_server = TTSServer(host, port, language, device)
    asyncio.run(tts_server.run_server())

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description="MeloTTS 기반 TTS 서버")
    parser.add_argument('--host', default="0.0.0.0")
    parser.add_argument('--port', type=int, default=2501)
    parser.add_argument('--language', default="KR")
    parser.add_argument('--device', default="cuda")
    args = parser.parse_args()
    start_server(args.host, args.port, args.language, args.device)
