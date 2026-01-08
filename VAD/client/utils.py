# utils.py
import socket, struct
from typing import Generator, Optional
import av, numpy as np

# ===== 프로토콜 상수 =====
REQ_AUDIO_DATA = 0x01
REQ_PING       = 99
REQ_VAD_RESULT = 0x0A  # 10

SUCCESS = 0

# 전송 안정화
CHUNK_BYTES = 64 * 1024  # 64KB 분할 전송

def read_exact(sock: socket.socket, n: int) -> bytes:
    """타임아웃 없이 정확히 n바이트 읽기(블로킹)."""
    buf = b""
    while len(buf) < n:
        chunk = sock.recv(n - len(buf))
        if not chunk:
            raise ConnectionError("socket closed by peer")
        buf += chunk
    return buf

def send_all(sock: socket.socket, data: bytes):
    """큰 데이터 안정 전송."""
    mv = memoryview(data)
    sent = 0
    while sent < len(mv):
        n = sock.send(mv[sent: sent + CHUNK_BYTES])
        if n == 0:
            raise ConnectionError("socket send returned 0")
        sent += n

def pack_send_audio(sock: socket.socket, checkcode: int, data: bytes):
    # [checkcode:int32BE][request:int32BE][size:int32BE][data]
    head = struct.pack("!iii", checkcode, REQ_AUDIO_DATA, len(data))
    send_all(sock, head)
    if data:
        send_all(sock, data)

def pack_send_ping(sock: socket.socket, checkcode: int):
    send_all(sock, struct.pack("!ii", checkcode, REQ_PING))

def mp4_to_chunks(mp4_path: str, out_rate=16000, out_channels=1, chunk_ms=40) -> Generator[bytes, None, None]:
    """
    학습/테스트용: 파일을 청크로 잘라 송신. (실시간 입력으로 교체 가능)
    반환: PCM s16 bytes
    """
    container = av.open(mp4_path)
    audio_stream = next((s for s in container.streams if s.type == "audio"), None)
    if audio_stream is None:
        raise RuntimeError("이 MP4에는 오디오 트랙이 없습니다.")
    resampler = av.audio.resampler.AudioResampler(
        format="s16",
        layout="mono" if out_channels == 1 else "stereo",
        rate=out_rate,
    )
    sample_width = 2
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
