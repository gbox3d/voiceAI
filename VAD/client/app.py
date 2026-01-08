# app.py
import threading, time
from queue import Queue, Empty

from config import load_config
from io_client import IOClient
from stt_sender import UpstreamSttSender

class App:
    def __init__(self):
        self.cfg = load_config()
        self.stop_evt = threading.Event()

        # 공용 큐
        self.vad_q: Queue = Queue(maxsize=2048)   # IOClient → UpstreamSttSender
        self.tts_q: Queue = Queue(maxsize=1024)   # UpstreamSttSender → (선택) TTS/로그

        # 구성 요소
        self.io = IOClient(
            host=self.cfg.io_host, port=self.cfg.io_port, checkcode=self.cfg.io_checkcode,
            mp4_path=self.cfg.input_mp4, out_rate=self.cfg.input_rate,
            channels=self.cfg.input_channels, chunk_ms=self.cfg.input_chunk_ms,
            ping_interval=self.cfg.io_ping_interval,
            vad_q=self.vad_q, stop_evt=self.stop_evt
        )
        self.stt = UpstreamSttSender(
            host=self.cfg.stt_host, port=self.cfg.stt_port, checkcode=self.cfg.stt_checkcode,
            in_q=self.vad_q, text_out_q=self.tts_q,
            stop_evt=self.stop_evt,
            per_request=self.cfg.stt_per_request
        )

    def start(self):
        print("[APP] start (using .env config)")
        self.io.start()
        self.stt.start()

    def run(self):
        try:
            while True:
                try:
                    txt = self.tts_q.get(timeout=0.5)
                    print(f"[APP] STT_TEXT: {txt}")
                    # TODO: 여기서 TTS 등 후속 파이프라인 수행
                except Empty:
                    pass
        except KeyboardInterrupt:
            print("\n[APP] 종료 신호 수신")
        finally:
            self.stop_evt.set()
            self.io.join(timeout=2.0)
            self.stt.join(timeout=2.0)
            print("[APP] stopped")

def main():
    app = App()
    app.start()
    app.run()

if __name__ == "__main__":
    main()
