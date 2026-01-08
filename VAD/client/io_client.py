# io_client.py
import socket, struct, time, threading
from queue import Queue
from typing import Optional

from utils import (
    read_exact, pack_send_audio, pack_send_ping,
    mp4_to_chunks, REQ_AUDIO_DATA, REQ_PING, REQ_VAD_RESULT
)

class IOClient(threading.Thread):
    """
    - 서버와 1개의 소켓으로 송수신.
    - mp4_to_chunks(또는 실시간 PCM)로 0x01 전송
    - 서버 응답:
        * 0x01/99 -> 1B status ACK
        * 0x0A(VAD) -> 1B fmt + 4B size + payload(WAV) → vad_q로 push
    """
    def __init__(self, host: str, port: int, checkcode: int,
                 mp4_path: Optional[str],
                 out_rate=16000, channels=1, chunk_ms=40,
                 ping_interval=5.0,
                 vad_q: Optional[Queue] = None,
                 stop_evt: Optional[threading.Event] = None):
        super().__init__(daemon=True)
        self.host, self.port, self.checkcode = host, port, checkcode
        self.mp4_path = mp4_path
        self.out_rate, self.channels, self.chunk_ms = out_rate, channels, chunk_ms
        self.ping_interval = ping_interval
        self.vad_q = vad_q
        self.stop_evt = stop_evt or threading.Event()
        self.sock: Optional[socket.socket] = None
        self.stats = {"chunks": 0, "bytes": 0, "failed": 0}

    def _connect(self):
        s = socket.create_connection((self.host, self.port), timeout=None)
        s.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        self.sock = s
        print(f"[IO] 연결 성공 -> {self.host}:{self.port}")

    def _tx_loop(self):
        """송신 루프: mp4 파일을 청크로 전송(실사용 시 실시간 입력으로 대체 가능)"""
        if not self.mp4_path:
            return
        try:
            for pcm in mp4_to_chunks(self.mp4_path, self.out_rate, self.channels, self.chunk_ms):
                if self.stop_evt.is_set():
                    break
                pack_send_audio(self.sock, self.checkcode, pcm)
                self.stats["chunks"] += 1
                self.stats["bytes"] += len(pcm)
        except Exception as e:
            print(f"[IO:TX] 송신 실패: {e}")
            self.stats["failed"] += 1
        finally:
            print("[IO:TX] 전송 종료(소켓은 유지)")

    def _rx_once(self):
        """단일 이벤트 수신 처리(블로킹)."""
        head = read_exact(self.sock, 8)  # !ii
        _, request_code = struct.unpack("!ii", head)

        if request_code in (REQ_AUDIO_DATA, REQ_PING):
            _status = struct.unpack("!B", read_exact(self.sock, 1))[0]
            # print(f"[IO:RX] ACK req={request_code} status={_status}")
            return

        if request_code == REQ_VAD_RESULT:
            fmt = struct.unpack("!B", read_exact(self.sock, 1))[0]
            (size,) = struct.unpack("!i", read_exact(self.sock, 4))
            payload = read_exact(self.sock, size) if size > 0 else b""
            print(f"[IO:RX] VAD fmt={fmt} size={size}")
            if self.vad_q is not None:
                try:
                    self.vad_q.put_nowait((fmt, payload))
                except Exception:
                    try:
                        _ = self.vad_q.get_nowait()
                        self.vad_q.put_nowait((fmt, payload))
                    except Exception:
                        print("[IO:RX] 경고: VAD 큐 가득")
            return

        print(f"[IO:RX] UNKNOWN req={request_code}")

    def run(self):
        self._connect()
        last_ping = 0.0

        # 파일 기반 송신(실시간 입력으로 교체 가능)
        tx_thread = threading.Thread(target=self._tx_loop, daemon=True)
        tx_thread.start()

        try:
            while not self.stop_evt.is_set():
                if self.ping_interval > 0.0 and (time.time() - last_ping) >= self.ping_interval:
                    try:
                        pack_send_ping(self.sock, self.checkcode)
                        last_ping = time.time()
                    except Exception as e:
                        print(f"[IO:TX] PING 실패: {e}")
                        break

                self._rx_once()  # 블로킹 1 이벤트 처리
        except ConnectionError:
            print("[IO] 소켓 종료 감지")
        except Exception as e:
            print(f"[IO] 예외: {e}")
