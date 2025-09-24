# server.py
# 0x01 요청: [size(int32 BE)] + [data] -> 내부 버퍼에 누적만 수행 (재생 없음)
# 단일 클라이언트 전용

import asyncio
import os
import struct
from typing import Optional, List
from collections import deque


class Server:
    # 상태코드
    SUCCESS = 0
    ERR_CHECKCODE_MISMATCH = 1
    ERR_INVALID_DATA = 2
    ERR_INVALID_REQUEST = 3
    ERR_INVALID_PARAMETER = 4
    ERR_INVALID_FORMAT = 5
    ERR_UNKNOWN_CODE = 8
    ERR_EXCEPTION = 9
    ERR_TIMEOUT = 10

    __VERSION__ = "1.0.0"

    def __init__(self,
                 host: Optional[str] = None,
                 port: Optional[int] = None,
                 timeout: Optional[int] = None,
                 checkcode: Optional[int] = None):
        self.host = host or os.getenv("VAD_HOST", "0.0.0.0")
        self.port = port or int(os.getenv("VAD_PORT", 26070))
        self.timeout = int(timeout) if timeout is not None else int(os.getenv("VAD_TIMEOUT", 10))
        self.checkcode = checkcode or int(os.getenv("VAD_CHECKCODE", 20250918))

        # 단일 클라이언트용 버퍼 (큐 형식)
        self.chunk_queue: deque[bytes] = deque()

        # 송신을 위한 상태
        self._writer: Optional[asyncio.StreamWriter] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None

    async def _read_exactly(self, reader: asyncio.StreamReader, n: int) -> bytes:
        return await asyncio.wait_for(reader.readexactly(n), timeout=self.timeout)

    async def handle_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        addr = writer.get_extra_info("peername")
        buf_chunks = 0
        buf_bytes = 0
        
        print(f"[INFO] 연결: {addr}")
        
        # 새 클라이언트 연결 시 기존 버퍼 초기화
        self.chunk_queue.clear()

        # 최신 클라이언트 writer 보관
        self._writer = writer

        try:
            while True:
                # 8바이트: checkcode(int32 BE) + request_code(int32 BE)
                header = await self._read_exactly(reader, 8)
                checkcode, request_code = struct.unpack("!ii", header)

                if checkcode != self.checkcode:
                    print(f"[WARN] CHECKCODE mismatch: recv={checkcode}, expected={self.checkcode}")
                    writer.write(struct.pack("!iiB", self.checkcode, request_code, self.ERR_CHECKCODE_MISMATCH))
                    await writer.drain()
                    break

                if request_code == 99:  # ping
                    writer.write(struct.pack("!iiB", self.checkcode, request_code, self.SUCCESS))
                    await writer.drain()
                    continue

                if request_code == 0x01:
                    # 0x01 프로토콜: size(int32 BE) + data
                    size_bytes = await self._read_exactly(reader, 4)
                    (size,) = struct.unpack("!i", size_bytes)

                    if size < 0:
                        print(f"[WARN] 잘못된 데이터 크기: {size}")
                        writer.write(struct.pack("!iiB", self.checkcode, request_code, self.ERR_INVALID_DATA))
                        await writer.drain()
                        continue

                    data = await self._read_exactly(reader, size) if size > 0 else b""

                    # 버퍼에 저장 (큐 뒤쪽에 추가)
                    self.chunk_queue.append(data)
                    buf_chunks += 1
                    buf_bytes += len(data)

                    print(f"[INFO] received chunk: {len(data)} bytes from {addr} (total: {buf_chunks} chunks, {buf_bytes} bytes)")
                    
                    # 성공 응답 전송
                    writer.write(struct.pack("!iiB", self.checkcode, request_code, self.SUCCESS))
                    await writer.drain()
                    continue

                # 알 수 없는 요청
                print(f"[WARN] unknown request: {request_code} from {addr}")
                writer.write(struct.pack("!iiB", self.checkcode, request_code, self.ERR_UNKNOWN_CODE))
                await writer.drain()

        except asyncio.IncompleteReadError:
            print(f"[INFO] EOF: {addr}")
        except asyncio.TimeoutError:
            print(f"[WARN] TIMEOUT: {addr}")
        except Exception as e:
            print(f"[ERROR] 예외: {e}")
            try:
                writer.write(struct.pack("!iiB", self.checkcode, 0, self.ERR_EXCEPTION))
                await writer.drain()
            except Exception:
                pass
        finally:
            # 연결 종료 시 writer 해제
            if self._writer is writer:
                self._writer = None
            writer.close()
            try:
                await writer.wait_closed()
            except Exception:
                pass
            print(f"[INFO] 종료: {addr} (received {buf_chunks} chunks, {buf_bytes} bytes)")

    def get_buffer(self) -> List[bytes]:
        """현재 버퍼의 모든 청크 반환"""
        return list(self.chunk_queue)

    def clear_buffer(self) -> int:
        """버퍼 초기화, 삭제된 청크 수 반환"""
        chunk_count = len(self.chunk_queue)
        self.chunk_queue.clear()
        return chunk_count

    def get_total_bytes(self) -> int:
        """버퍼에 저장된 총 바이트 수 반환"""
        return sum(len(chunk) for chunk in self.chunk_queue)

    def get_chunk_count(self) -> int:
        """버퍼에 저장된 청크 수 반환"""
        return len(self.chunk_queue)

    def pop_chunks(self, count: int) -> List[bytes]:
        """큐 앞에서부터 지정된 개수만큼 청크를 빼내서 반환"""
        if count <= 0:
            return []
        
        result = []
        actual_count = min(count, len(self.chunk_queue))
        
        for _ in range(actual_count):
            if self.chunk_queue:
                result.append(self.chunk_queue.popleft())
        
        return result

    def peek_chunks(self, count: int) -> List[bytes]:
        """큐 앞에서부터 지정된 개수만큼 청크를 조회 (제거하지 않음)"""
        if count <= 0:
            return []
        
        actual_count = min(count, len(self.chunk_queue))
        return [self.chunk_queue[i] for i in range(actual_count)]

    def pop_bytes(self, byte_count: int) -> bytes:
        """큐 앞에서부터 지정된 바이트 수만큼 데이터를 빼내서 반환"""
        if byte_count <= 0:
            return b""
        
        result = b""
        remaining = byte_count
        
        while remaining > 0 and self.chunk_queue:
            chunk = self.chunk_queue[0]  # 첫 번째 청크 확인
            
            if len(chunk) <= remaining:
                # 청크 전체를 사용
                result += self.chunk_queue.popleft()
                remaining -= len(chunk)
            else:
                # 청크 일부만 사용하고 나머지는 큐에 남김
                result += chunk[:remaining]
                self.chunk_queue[0] = chunk[remaining:]
                remaining = 0
        
        return result

    def get_available_bytes(self) -> int:
        """현재 사용 가능한 총 바이트 수"""
        return self.get_total_bytes()

    def has_chunks(self, min_count: int = 1) -> bool:
        """지정된 개수 이상의 청크가 있는지 확인"""
        return len(self.chunk_queue) >= min_count

    def has_bytes(self, min_bytes: int) -> bool:
        """지정된 바이트 수 이상의 데이터가 있는지 확인"""
        return self.get_total_bytes() >= min_bytes

    # --------- 외부 호출용: 발화 세그먼트 전송 API ----------
    async def _async_send_segment(self, format_code: int, audio_bytes: bytes):
        """
        프로토콜:
        1) '!ii'  : (checkcode, request_code=10)
        2) '!B'   : format_code (1바이트)
        3) '!i'   : audio_size  (int32)
        4) bytes  : audio_bytes
        """
        if self._writer is None:
            # 현재 연결 없음
            return False
        try:
            header = struct.pack("!ii", self.checkcode, 10)
            fmt    = struct.pack("!B", format_code & 0xFF)
            size   = struct.pack("!i", len(audio_bytes))
            self._writer.write(header + fmt + size + audio_bytes)
            await self._writer.drain()
            return True
        except Exception as e:
            print(f"[WARN] 세그먼트 전송 실패: {e}")
            return False

    def send_segment(self, format_code: int, audio_bytes: bytes) -> None:
        """
        다른 스레드(예: 오디오 재생 스레드)에서도 호출 가능.
        이벤트 루프에 코루틴을 안전하게 스케줄링한다.
        """
        if self._loop is None:
            return
        if self._writer is None:
            return
        # 루프 스레드로 안전하게 스케줄링
        asyncio.run_coroutine_threadsafe(
            self._async_send_segment(format_code, audio_bytes),
            self._loop
        )

    async def run(self):
        # server = await asyncio.start_server(self.handle_client, self.host, self.port)
        # 이벤트 루프 보관
        self._loop = asyncio.get_running_loop()
        server = await asyncio.start_server(self.handle_client, self.host, self.port)

        print(f"[INFO] 서버 시작: {self.host}:{self.port}")
        async with server:
            await server.serve_forever()


if __name__ == "__main__":
    try:
        asyncio.run(Server().run())
    except KeyboardInterrupt:
        print("\n[INFO] 서버 종료")