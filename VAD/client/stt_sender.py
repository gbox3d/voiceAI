# stt_sender.py
import socket, struct, time, threading
from queue import Queue, Empty
from typing import Optional, Tuple

from utils import send_all

class UpstreamSttSender(threading.Thread):
    """
    in_q에서 (fmt:int, wav_payload:bytes)를 받아
    STT 서버(0x01)로 전송하고 텍스트 응답을 text_out_q로 전달.
    - fmt==1은 WAV(PCM16 mono 16kHz) 규약
    - per_request=True면 요청마다 연결 생성-응답후 종료
    """
    def __init__(self, host: str, port: int, checkcode: int,
                 in_q: Queue, text_out_q: Optional[Queue],
                 stop_evt: threading.Event, per_request: bool = False):
        super().__init__(daemon=True)
        self.host = host
        self.port = port
        self.checkcode = checkcode
        self.q = in_q
        self.text_q = text_out_q
        self.stop_evt = stop_evt
        self.per_request = per_request
        self.sock: Optional[socket.socket] = None

    def _connect(self):
        while not self.stop_evt.is_set():
            try:
                s = socket.create_connection((self.host, self.port), timeout=10)
                s.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
                try: s.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 1024 * 1024)
                except OSError: pass
                try: s.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
                except OSError: pass
                self.sock = s
                print(f"[STT] 연결 성공 -> {self.host}:{self.port}")
                return
            except Exception as e:
                print(f"[STT] 연결 실패: {e}; 1s 후 재시도")
                time.sleep(1.0)

    def _recv_exact(self, n: int) -> bytes:
        from utils import read_exact
        return read_exact(self.sock, n)  # 타임아웃 없이 블로킹

    def _recv_stt_response(self) -> Optional[str]:
        # 응답: !iiB + (status==0) !i + payload(utf-8)
        hdr = self._recv_exact(9)
        cc, rc, status = struct.unpack("!iiB", hdr)
        if rc != 1:
            raise RuntimeError(f"STT 응답 request_code 불일치: {rc}")
        if status != 0:
            print(f"[STT] RESP status={status} (오류)")
            return None
        (ln,) = struct.unpack("!i", self._recv_exact(4))
        txt = self._recv_exact(ln).decode("utf-8", errors="replace") if ln > 0 else ""
        print(f"[STT] TEXT: {txt}")
        return txt

    def _send_one(self, fmt: int, wav_payload: bytes):
        if self.sock is None or self.per_request:
            self._connect()
        try:
            # --- 요청 ---
            send_all(self.sock, struct.pack("!ii", self.checkcode, 1))
            send_all(self.sock, struct.pack("!B", fmt))
            send_all(self.sock, struct.pack("!i", len(wav_payload)))
            if wav_payload:
                send_all(self.sock, wav_payload)
            print(f"[STT] TX fmt={fmt} size={len(wav_payload)}")

            # --- 응답 ---
            txt = self._recv_stt_response()
            if txt and self.text_q is not None:
                try:
                    self.text_q.put_nowait(txt)
                except Exception:
                    try:
                        _ = self.text_q.get_nowait()
                        self.text_q.put_nowait(txt)
                    except Exception:
                        pass

            if self.per_request:
                try: self.sock.shutdown(socket.SHUT_RDWR)
                except Exception: pass
                try: self.sock.close()
                except Exception: pass
                self.sock = None

        except Exception as e:
            print(f"[STT] 전송/수신 실패: {e}; 소켓 재설정 및 재시도 준비")
            try:
                if self.sock: self.sock.close()
            except Exception: pass
            self.sock = None
            # 유실 방지: 재큐잉(최신성 우선 정책은 필요 시 조정)
            try:
                self.q.put_nowait((fmt, wav_payload))
            except Exception:
                try:
                    _ = self.q.get_nowait()
                    self.q.put_nowait((fmt, wav_payload))
                except Exception:
                    print("[STT] 경고: 큐 가득 — 패킷 드롭")

    def run(self):
        while not self.stop_evt.is_set():
            try:
                fmt, wav_payload = self.q.get(timeout=0.5)
            except Empty:
                continue
            self._send_one(fmt, wav_payload)
