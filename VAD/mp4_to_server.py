# mp4_to_server_threaded.py
import argparse, socket, struct, time, threading, os
from queue import Queue, Empty

import av, numpy as np

# ===== 프로토콜 상수 =====
REQ_AUDIO_DATA = 0x01
REQ_PING       = 99
REQ_VAD_RESULT = 0x0A  # 10

SUCCESS = 0
ERR_CHECKCODE_MISMATCH = 1
ERR_INVALID_DATA = 2
ERR_UNKNOWN_CODE = 8
ERR_EXCEPTION = 9
ERR_TIMEOUT = 10

CHUNK_BYTES = 64 * 1024  # 64KB 단위로 본문 분할 전송

def read_exact(sock: socket.socket, n: int, timeout: float | None) -> bytes:
    sock.settimeout(timeout)
    buf = b""
    while len(buf) < n:
        chunk = sock.recv(n - len(buf))
        if not chunk:
            raise ConnectionError("socket closed by peer")
        buf += chunk
    return buf

def pack_send_audio(sock: socket.socket, checkcode: int, data: bytes):
    # [checkcode:int32BE][request:int32BE][size:int32BE][data]
    msg = struct.pack("!iii", checkcode, REQ_AUDIO_DATA, len(data)) + data
    sock.sendall(msg)

def pack_send_ping(sock: socket.socket, checkcode: int):
    # [checkcode:int32BE][request:int32BE]
    sock.sendall(struct.pack("!ii", checkcode, REQ_PING))

def mp4_to_chunks(mp4_path: str, out_rate=16000, out_channels=1, chunk_ms=40):
    container = av.open(mp4_path)
    audio_stream = next((s for s in container.streams if s.type == "audio"), None)
    if audio_stream is None:
        raise RuntimeError("이 MP4에는 오디오 트랙이 없습니다.")
    resampler = av.audio.resampler.AudioResampler(
        format="s16",
        layout="mono" if out_channels == 1 else "stereo",
        rate=out_rate,
    )
    sample_width = 2  # s16
    chunk_samples = int(out_rate * (chunk_ms / 1000.0))
    chunk_bytes = chunk_samples * out_channels * sample_width
    buf = bytearray()
    try:
        for packet in container.demux(audio_stream):
            for frame in packet.decode():
                outs = resampler.resample(frame)
                if not outs:
                    continue
                for out in outs:
                    arr = out.to_ndarray()
                    if arr.dtype != np.int16:
                        arr = arr.astype(np.int16, copy=False)
                    buf.extend(arr.tobytes(order="C"))
                    while len(buf) >= chunk_bytes:
                        yield bytes(buf[:chunk_bytes])
                        del buf[:chunk_bytes]
        outs = resampler.resample(None)
        if outs:
            for out in outs:
                arr = out.to_ndarray()
                if arr.dtype != np.int16:
                    arr = arr.astype(np.int16, copy=False)
                buf.extend(arr.tobytes(order="C"))
                while len(buf) >= chunk_bytes:
                    yield bytes(buf[:chunk_bytes])
                    del buf[:chunk_bytes]
        if buf:
            yield bytes(buf)
    finally:
        container.close()

class UpstreamSttSender(threading.Thread):
    """
    VAD 결과를 STT 서버로 즉시 릴레이하는 전용 스레드.
    - 프로토콜(요청하신 명세):
        pack('!ii', stt_checkcode, 1)   # 헤더
        pack('!B', fmt)                 # 포맷 코드 1B
        pack('!i', size)                # 길이 4B
        payload                         # 본문
    - 연결이 끊기면 자동 재연결
    """
    def __init__(self, host: str, port: int, checkcode: int, in_q: Queue, stop_evt: threading.Event):
        super().__init__(daemon=True)
        self.host = host
        self.port = port
        self.checkcode = checkcode
        self.q = in_q
        self.stop_evt = stop_evt
        self.sock: socket.socket | None = None

        # 보조: 정확히 n바이트 읽기
    def _recv_exact(self, n: int, timeout: float = 10.0) -> bytes:
        self.sock.settimeout(timeout)
        buf = b""
        while len(buf) < n:
            chunk = self.sock.recv(n - len(buf))
            if not chunk:
                raise ConnectionError("socket closed by peer")
            buf += chunk
        return buf

    def _recv_stt_response(self):
        # 응답 헤더: !iiB  (checkcode, request_code, status)
        hdr = self._recv_exact(9)
        cc, rc, status = struct.unpack("!iiB", hdr)
        if rc != 1:
            raise RuntimeError(f"STT 응답 request_code 불일치: {rc}")
        if status != 0:
            # 실패면 payload 없음 (프로토콜 사양)
            print(f"[STT] RESP status={status} (오류)")
            return None
        # 성공: 길이(4B) + payload(UTF-8)
        lb = self._recv_exact(4)
        (ln,) = struct.unpack("!i", lb)
        txt = self._recv_exact(ln).decode("utf-8", errors="replace") if ln > 0 else ""
        print(f"[STT] TEXT: {txt}")
        return txt
    
    def _connect(self):
        # 재연결 루프
        while not self.stop_evt.is_set():
            try:
                s = socket.create_connection((self.host, self.port), timeout=10)
                # 송신 안정화 옵션
                s.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
                try:
                    s.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 1024 * 1024)  # 1MB
                except OSError:
                    pass
                try:
                    s.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
                except OSError:
                    pass
                self.sock = s
                print(f"[STT] 연결 성공 -> {self.host}:{self.port}")
                return
            except Exception as e:
                print(f"[STT] 연결 실패: {e}; 1초 후 재시도")
                time.sleep(1.0)

    # >>> 여기에 추가: 큰 데이터를 안전하게 분할 전송
    def _send_all(self, data: bytes):
        """OS send 버퍼/필터에 안전하게 분할 전송"""
        view = memoryview(data)
        sent = 0
        while sent < len(view):
            n = self.sock.send(view[sent: sent + CHUNK_BYTES])
            if n == 0:
                raise ConnectionError("socket send returned 0")
            sent += n

    def _send_one(self, fmt: int, payload: bytes):
        if self.sock is None:
            self._connect()
        try:
            # --- 요청 보냄 ---
            head = struct.pack("!ii", self.checkcode, 1)
            self._send_all(head)
            self._send_all(struct.pack("!B", fmt))
            self._send_all(struct.pack("!i", len(payload)))
            if payload:
                self._send_all(payload)
            print(f"[STT] TX fmt={fmt} size={len(payload)}")

            # --- 응답 받음 (프로토콜 필수) ---
            self._recv_stt_response()  # <= 중요!

        except Exception as e:
            print(f"[STT] 전송/수신 실패: {e}; 소켓 재설정 및 재시도 준비")
            try: self.sock.close()
            except Exception: pass
            self.sock = None
            # 유실 방지: 재큐잉
            try:
                self.q.put_nowait((fmt, payload))
            except Exception:
                try:
                    _ = self.q.get_nowait()
                    self.q.put_nowait((fmt, payload))
                except Exception:
                    print("[STT] 경고: 큐 가득 — 패킷 드롭")

    def run(self):
        self._connect()
        while not self.stop_evt.is_set():
            try:
                fmt, payload = self.q.get(timeout=0.5)
            except Empty:
                continue
            self._send_one(fmt, payload)

class ResponseReader(threading.Thread):
    """
    서버 응답/이벤트 수신 전용:
      - ACK(0x01/99): '!iiB'
      - VAD(0x0A)  : '!ii' + '!B' + '!i' + payload
    resp_q로 튜플을 push:
      ('ack', request_code, status, t)
      ('vad', fmt, payload, t)
      ('unknown', request_code, raw, t)
    또한 VAD 수신 시 즉시 stt_q로 (fmt, payload) 전달
    """
    def __init__(self, sock: socket.socket, resp_q: Queue, stt_q: Queue,
                 stop_evt: threading.Event, timeout: float = 5.0):
        super().__init__(daemon=True)
        self.sock = sock
        self.q = resp_q
        self.stt_q = stt_q
        self.stop_evt = stop_evt
        self.timeout = timeout

    def run(self):
        try:
            while not self.stop_evt.is_set():
                try:
                    # 공통 헤더 8바이트
                    head = read_exact(self.sock, 8, self.timeout)
                    checkcode, request_code = struct.unpack("!ii", head)

                    if request_code in (REQ_AUDIO_DATA, REQ_PING):
                        # ACK: 상태 1바이트
                        status_b = read_exact(self.sock, 1, self.timeout)
                        (status,) = struct.unpack("!B", status_b)
                        self.q.put(('ack', request_code, status, time.time()))
                    #     if request_code == REQ_AUDIO_DATA:
                    #         print(f"[RX] ACK 0x01 status={status}")
                    #     else:
                    #         print(f"[RX] PING status={status}")
                        continue

                    if request_code == REQ_VAD_RESULT:
                        # fmt(1B) + size(4B) + payload
                        fmt_b   = read_exact(self.sock, 1, self.timeout)
                        size_b  = read_exact(self.sock, 4, self.timeout)
                        fmt     = struct.unpack("!B", fmt_b)[0]
                        (size,) = struct.unpack("!i", size_b)
                        payload = read_exact(self.sock, size, self.timeout) if size > 0 else b""
                        self.q.put(('vad', fmt, payload, time.time()))
                        print(f"[RX] VAD fmt={fmt} size={size}")

                        # === 즉시 STT 서버로 릴레이 ===
                        try:
                            self.stt_q.put_nowait((fmt, payload))
                        except Exception:
                            # 큐가 찬 경우 블로킹 방지: 가장 오래된 것 버리고 새 것 삽입 (선택 정책)
                            try:
                                _ = self.stt_q.get_nowait()
                                self.stt_q.put_nowait((fmt, payload))
                            except Exception:
                                print("[RX] 경고: STT 큐에 넣지 못했습니다.")

                        continue

                    # 모르는 이벤트
                    self.q.put(('unknown', request_code, b"", time.time()))
                    print(f"[RX] UNKNOWN req={request_code}")

                except socket.timeout:
                    continue
        except ConnectionError:
            print("[RX] 소켓 종료 감지")
        except Exception as e:
            print(f"[RX] 예외: {e}")

class Sender(threading.Thread):
    def __init__(self, sock: socket.socket, mp4_path: str, checkcode: int,
                 chunk_ms=40, out_rate=16000, out_channels=1,
                 delay_ms=0, stop_evt: threading.Event | None = None):
        super().__init__(daemon=True)
        self.sock = sock
        self.mp4_path = mp4_path
        self.checkcode = checkcode
        self.chunk_ms = chunk_ms
        self.out_rate = out_rate
        self.out_channels = out_channels
        self.delay_ms = delay_ms
        self.stop_evt = stop_evt or threading.Event()
        self.stats = {"chunks": 0, "bytes": 0, "failed": 0, "start": None, "end": None}

    def run(self):
        self.stats["start"] = time.time()
        try:
            for pcm in mp4_to_chunks(self.mp4_path, self.out_rate, self.out_channels, self.chunk_ms):
                if self.stop_evt.is_set():
                    break
                try:
                    pack_send_audio(self.sock, self.checkcode, pcm)
                    self.stats["chunks"] += 1
                    self.stats["bytes"] += len(pcm)
                except Exception as e:
                    print(f"[TX] 송신 실패: {e}")
                    self.stats["failed"] += 1
                    break
                if self.delay_ms > 0:
                    time.sleep(self.delay_ms / 1000.0)
        finally:
            self.stats["end"] = time.time()
            print("[TX] 전송 완료(소켓은 유지, VAD 수신 대기 중)")

def main():
    ap = argparse.ArgumentParser(description="Threaded MP4 audio sender with VAD->STT relay")
    ap.add_argument("mp4")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=26070)
    ap.add_argument("--checkcode", type=int, default=20250918)
    ap.add_argument("--chunk-ms", type=int, default=40)
    ap.add_argument("--rate", type=int, default=16000)
    ap.add_argument("--channels", type=int, default=1)
    ap.add_argument("--delay", type=int, default=0, help="청크 간 지연(ms)")
    ap.add_argument("--ping-interval", type=float, default=5.0, help="초 단위. 0이면 비활성")
    ap.add_argument("--save-vad", default="", help="VAD payload를 파일로 순차 저장 (접두사)")

    # === STT 릴레이 설정(요청하신 기본값) ===
    ap.add_argument("--stt-host", default="127.0.0.1")
    ap.add_argument("--stt-port", type=int, default=22270)
    ap.add_argument("--stt-checkcode", type=int, default=20250218)

    args = ap.parse_args()

    print(f"[INFO] 연결 시도: {args.host}:{args.port}")
    with socket.create_connection((args.host, args.port), timeout=10) as sock:
        print("[INFO] 연결 성공")

        stop_evt = threading.Event()
        resp_q: Queue = Queue()
        stt_q: Queue = Queue(maxsize=1024)  # 폭주 방지를 위한 제한
        vad_results = []  # (fmt:int, payload:bytes, t:float)

        # === STT 송신 스레드 가동 ===
        stt = UpstreamSttSender(args.stt_host, args.stt_port, args.stt_checkcode, stt_q, stop_evt)
        stt.start()

        # === 수신/송신 스레드 가동 ===
        rx = ResponseReader(sock, resp_q, stt_q, stop_evt, timeout=3.0)
        rx.start()

        tx = Sender(
            sock=sock,
            mp4_path=args.mp4,
            checkcode=args.checkcode,
            chunk_ms=args.chunk_ms,
            out_rate=args.rate,
            out_channels=args.channels,
            delay_ms=args.delay,
            stop_evt=stop_evt
        )
        tx.start()

        last_ping = 0.0
        file_idx = 0

        try:
            while True:
                # 주기적 핑(서버 읽기 타임아웃 방지)
                if args.ping_interval > 0.0 and (time.time() - last_ping) >= args.ping_interval:
                    try:
                        pack_send_ping(sock, args.checkcode)
                        last_ping = time.time()
                        print("[TX] PING 전송")
                    except Exception as e:
                        print(f"[TX] PING 실패: {e}")
                        break

                # 수신 이벤트 처리
                try:
                    evt = resp_q.get(timeout=0.2)
                except Empty:
                    evt = None

                if evt:
                    kind = evt[0]
                    if kind == 'ack':
                        _, req, status, t = evt
                    elif kind == 'vad':
                        _, fmt, payload, t = evt
                        vad_results.append((fmt, payload, t))
                        if args.save_vad:
                            path = f"{args.save_vad}_{file_idx:06d}.bin"
                            with open(path, "wb") as f:
                                f.write(payload)
                            print(f"[SAVE] VAD payload -> {path}")
                            file_idx += 1
                    else:
                        pass

                time.sleep(0.01)

        except KeyboardInterrupt:
            print("\n[MAIN] 종료 신호 수신")
        finally:
            stop_evt.set()
            tx.join(timeout=2.0)

        # 전송 통계 요약
        dur = (tx.stats["end"] - tx.stats["start"]) if tx.stats["end"] and tx.stats["start"] else 0.0
        kbps = (tx.stats["bytes"] / 1024.0) / dur if dur > 0 else 0.0
        print("[INFO] 전송 종료 요약")
        print(f"  - 청크 수: {tx.stats['chunks']}")
        print(f"  - 총 바이트: {tx.stats['bytes']:,}")
        print(f"  - 실패: {tx.stats['failed']}")
        print(f"  - 소요시간: {dur:.2f}s")
        print(f"  - 평균 전송속도: {kbps:.1f} KB/s")
        print(f"  - 수신된 VAD 이벤트: {len(vad_results)}")

if __name__ == "__main__":
    main()
