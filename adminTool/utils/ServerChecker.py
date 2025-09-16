# filename: utils/server_checker.py
# author: gbox3d
# created: 2025-07-31
# description: Server checker utility functions

import asyncio
import struct
import time
from typing import Tuple
import os

class ServerChecker:
    """서버 상태 확인 클래스"""

    def __init__(self):
        self.timeout = 5.0

    async def check_asr_server(self, host: str, port: int, checkcode: int = 20250122) -> Tuple[bool, str, float]:
        """ASR 서버 핑(Ping) 확인"""
        start_time = time.time()
        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(host, port),
                timeout=self.timeout
            )

            # Ping 요청 (request_code = 99)
            header = struct.pack('!ii', checkcode, 99)
            writer.write(header)
            await writer.drain()

            # 응답 받기
            response = await asyncio.wait_for(
                reader.readexactly(9),
                timeout=self.timeout
            )

            recv_checkcode, recv_request_code, status = struct.unpack('!iiB', response)
            elapsed = time.time() - start_time

            writer.close()
            await writer.wait_closed()

            if recv_checkcode == checkcode and status == 0:
                return True, f"서버 응답 확인 (응답 시간: {elapsed:.3f}초)", elapsed
            else:
                return False, f"잘못된 응답 (status: {status})", elapsed

        except asyncio.TimeoutError:
            elapsed = time.time() - start_time
            return False, f"타임아웃 ({self.timeout}초)", elapsed
        except ConnectionRefusedError:
            elapsed = time.time() - start_time
            return False, "연결 거부됨", elapsed
        except Exception as e:
            elapsed = time.time() - start_time
            return False, f"오류: {str(e)}", elapsed

    async def check_asr_transcription(self, host: str, port: int, checkcode: int, audio_filepath: str) -> Tuple[bool, str, float]:
        """ASR 서버 음성 인식 기능 테스트"""
        start_time = time.time()
        if not os.path.exists(audio_filepath):
            return False, f"오디오 파일을 찾을 수 없음: {audio_filepath}", 0.0

        try:
            # 오디오 파일 읽기
            with open(audio_filepath, 'rb') as f:
                audio_bytes = f.read()

            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(host, port),
                timeout=self.timeout
            )

            # 1. 헤더 전송 (checkcode, request_code = 1)
            request_code = 1
            header = struct.pack('!ii', checkcode, request_code)
            writer.write(header)

            # 2. 포맷 코드 전송 (wav: 1)
            # 파일 확장자에 따라 포맷 코드 결정 (예시)
            fmt_map = {".wav": 1, ".mp3": 2, ".webm": 3, ".mp4": 4}
            ext = os.path.splitext(audio_filepath)[1].lower()
            fmt_code = fmt_map.get(ext)
            if fmt_code is None:
                 return False, f"지원하지 않는 오디오 포맷: {ext}", 0.0
            writer.write(struct.pack('!B', fmt_code))

            # 3. 오디오 데이터 크기 및 데이터 전송
            writer.write(struct.pack('!i', len(audio_bytes)))
            writer.write(audio_bytes)
            await writer.drain()

            # 응답 헤더 수신
            response_header = await asyncio.wait_for(reader.readexactly(9), timeout=self.timeout)
            recv_checkcode, recv_request_code, status = struct.unpack('!iiB', response_header)

            if status != 0:
                elapsed = time.time() - start_time
                return False, f"서버 오류 응답 (status: {status})", elapsed

            # 인식 결과 텍스트 수신
            result_size_bytes = await asyncio.wait_for(reader.readexactly(4), timeout=self.timeout)
            result_size = struct.unpack('!i', result_size_bytes)[0]
            
            result_bytes = await asyncio.wait_for(reader.readexactly(result_size), timeout=self.timeout)
            text_result = result_bytes.decode('utf-8')

            elapsed = time.time() - start_time
            writer.close()
            await writer.wait_closed()

            return True, f"'{text_result}'", elapsed

        except asyncio.TimeoutError:
            elapsed = time.time() - start_time
            return False, f"타임아웃 ({self.timeout}초)", elapsed
        except ConnectionRefusedError:
            elapsed = time.time() - start_time
            return False, "연결 거부됨", elapsed
        except Exception as e:
            elapsed = time.time() - start_time
            return False, f"오류: {str(e)}", elapsed


    async def check_tts_server(self, host: str, port: int) -> Tuple[bool, str, float]:
        """TTS 서버 핑 확인"""
        start_time = time.time()
        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(host, port),
                timeout=self.timeout
            )

            # TTS 서버 헤더 생성 (Ping 요청)
            header = bytearray(32)
            header[0:4] = b'TTS1'  # CHECKCODE
            header[4] = 99  # REQ_PING
            header[5] = 0  # format_code (사용하지 않음)

            writer.write(header)
            await writer.drain()

            # 응답 받기 (32바이트 헤더)
            response = await asyncio.wait_for(
                reader.readexactly(32),
                timeout=self.timeout
            )

            recv_checkcode = response[0:4]
            status = response[4]
            elapsed = time.time() - start_time

            writer.close()
            await writer.wait_closed()

            if recv_checkcode == b'TTS1' and status == 0:
                return True, f"응답 시간: {elapsed:.3f}초", elapsed
            else:
                return False, f"잘못된 응답 (status: {status})", elapsed

        except asyncio.TimeoutError:
            elapsed = time.time() - start_time
            return False, f"타임아웃 ({self.timeout}초)", elapsed
        except ConnectionRefusedError:
            elapsed = time.time() - start_time
            return False, "연결 거부됨", elapsed
        except Exception as e:
            elapsed = time.time() - start_time
            return False, f"오류: {str(e)}", elapsed

def run_async(coro):
    """비동기 함수를 동기적으로 실행"""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    return loop.run_until_complete(coro)