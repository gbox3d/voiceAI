import asyncio
import struct
import sys
import os

class AsrServer:
    # --- status_code 정의 ---
    SUCCESS = 0
    ERR_CHECKCODE_MISMATCH = 1
    ERR_INVALID_DATA = 2
    ERR_INVALID_REQUEST = 3
    ERR_INVALID_PARAMETER = 4
    ERR_INVALID_FORMAT = 5
    ERR_UNKNOWN_CODE = 8
    ERR_EXCEPTION = 9
    ERR_TIMEOUT = 10

    def __init__(self, host=None, port=None, timeout=None, checkcode=None):
        # 환경 변수나 기본값으로 설정
        self.host = host or os.getenv("ASR_HOST", "0.0.0.0")
        self.port = port or int(os.getenv("ASR_PORT", 2500))
        self.timeout = timeout or int(os.getenv("ASR_TIMEOUT", 10))
        self.checkcode = checkcode or int(os.getenv("ASR_CHECKCODE", 20250122))

    async def receive_data_with_timeout(self, reader, label):
        """
        비동기 방식으로 데이터 수신 (타임아웃 포함)
        """
        try:
            size_data = await asyncio.wait_for(reader.readexactly(4), timeout=self.timeout)
            size = struct.unpack('!i', size_data)[0]
            received_data = await asyncio.wait_for(reader.readexactly(size), timeout=self.timeout)
            return received_data
        except asyncio.TimeoutError:
            print(f"[ERROR] {label} 수신 타임아웃 발생")
            return None
        except Exception as e:
            print(f"[ERROR] {label} 수신 중 예외 발생: {e}")
            return None

    async def handle_client(self, reader, writer):
        addr = writer.get_extra_info('peername')
        print(f"[INFO] 클라이언트 연결됨: {addr}")

        try:
            # 헤더 수신
            header = await reader.readexactly(8)
            checkcode, request_code = struct.unpack('!ii', header)
            
            print(f"[INFO] 요청 - checkcode: {checkcode}, code: {request_code}")

            # checkcode 확인
            if checkcode != self.checkcode:
                print("[ERROR] 잘못된 checkcode")
                response = struct.pack('!iiB', self.checkcode, request_code, self.ERR_CHECKCODE_MISMATCH)
                writer.write(response)
                await writer.drain()
                return

            # 요청 코드별 처리
            if request_code == 99:  # Ping 테스트
                print("[INFO] Ping 요청 수신")
                response = struct.pack('!iiB', self.checkcode, request_code, self.SUCCESS)
                writer.write(response)
                await writer.drain()
            elif request_code == 0x01:  # STT 요청
                pass
                # 음성 데이터 수신
                # ASR 처리
                # 결과 전송 
            else:
                print(f"[ERROR] 알 수 없는 요청 코드: {request_code}")
                response = struct.pack('!iiB', self.checkcode, request_code, self.ERR_UNKNOWN_CODE)
                writer.write(response)
                await writer.drain()

        except asyncio.IncompleteReadError:
            print("[ERROR] 클라이언트 데이터 수신 실패")
        except Exception as e:
            print(f"[ERROR] 처리 중 예외 발생: {e}")
        finally:
            writer.close()
            await writer.wait_closed()
            print(f"[INFO] 클라이언트 연결 종료: {addr}")

    async def run_server(self):
        server = await asyncio.start_server(self.handle_client, self.host, self.port)
        addr = server.sockets[0].getsockname()
        print(f"[INFO] 서버 시작: {addr}, TIMEOUT={self.timeout}s, CHECKCODE={self.checkcode}")
        
        try:
            async with server:
                await server.serve_forever()
        except KeyboardInterrupt:
            # Ctrl+C(KeyInterrupt) 시, 에러 메시지 없이 종료
            print("\n[INFO] 서버가 종료됩니다 (KeyboardInterrupt).")
            server.close()
            await server.wait_closed()
            # 필요한 추가 정리 작업 수행 후 종료
            sys.exit(0)

# 직접 실행 예시
# if __name__ == "__main__":
#     asr_server = AsrServer()
#     asyncio.run(asr_server.run_server())
