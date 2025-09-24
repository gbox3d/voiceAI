import sys
import av 
import pyaudio
import numpy as np


def play_mp4_audio_stream(file_path: str, device_index: int | None = None,
                          force_stereo: bool = True, out_rate: int | None = None):
    """
    MP4 오디오를 프레임 단위로 디코드하여 PyAudio로 즉시 출력.
    - force_stereo=True  -> 출력을 스테레오(2ch)로 강제 (권장)
      False              -> 출력 모노(1ch)로 강제
    - out_rate=None      -> 입력 샘플레이트 유지, 필요 시 48000 등으로 강제 가능
    """
    container = av.open(file_path)
    audio_stream = next((s for s in container.streams if s.type == "audio"), None)
    if audio_stream is None:
        print("❌ 오디오 트랙이 없습니다.")
        return

    cc = audio_stream.codec_context
    src_rate = cc.sample_rate or 48000

    # 출력 타겟 포맷/레이아웃 설정 (입력 레이아웃에 의존하지 않음)
    target_layout = "stereo" if force_stereo else "mono"
    target_channels = 2 if force_stereo else 1
    target_rate = out_rate or src_rate

    # 항상 int16 + interleaved 로 출력
    resampler = av.audio.resampler.AudioResampler(
        format="s16",
        layout=target_layout,
        rate=target_rate,
    )

    p = pyaudio.PyAudio()
    stream = p.open(
        format=pyaudio.paInt16,
        channels=target_channels,
        rate=target_rate,
        output=True,
        output_device_index=device_index,
        frames_per_buffer=1024, # 버퍼 크기 (낮추면 지연시간 감소, 너무 낮추면 끊김 발생)
    )

    print(f"▶ 재생 중: {file_path}  -> {target_layout}, {target_rate} Hz, s16")

    try:
        for packet in container.demux(audio_stream):
            for frame in packet.decode():
                outs = resampler.resample(frame)
                if not outs:
                    continue
                for out in outs:
                    # PyAV 15: plane.to_bytes() 없음 → ndarray로 변환 후 bytes
                    # shape: (samples, channels) (interleaved)
                    arr = out.to_ndarray()
                    if arr.dtype != np.int16:
                        arr = arr.astype(np.int16, copy=False)
                    buf = arr.tobytes(order="C")
                    if buf:
                        stream.write(buf)

        # flush (잔여 샘플 출력)
        outs = resampler.resample(None)
        if outs:
            for out in outs:
                arr = out.to_ndarray()
                if arr.dtype != np.int16:
                    arr = arr.astype(np.int16, copy=False)
                buf = arr.tobytes(order="C")
                if buf:
                    stream.write(buf)

    except KeyboardInterrupt:
        print("\n⏹️ 중지 요청(Ctrl+C)")
    finally:
        stream.stop_stream()
        stream.close()
        p.terminate()
        container.close()
        print("✔ 완료")


def list_output_devices():
    """출력 장치 목록 및 인덱스 확인용(선택)."""
    p = pyaudio.PyAudio()
    print("=== Output Devices ===")
    for i in range(p.get_device_count()):
        info = p.get_device_info_by_index(i)
        if info.get("maxOutputChannels", 0) > 0:
            print(f"[{i}] {info['name']} (ch={info['maxOutputChannels']})")
    p.terminate()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("사용법: python playmp4snd.py <mp4파일> [device_index]")
        sys.exit(0)

    path = sys.argv[1]
    dev_idx = int(sys.argv[2]) if len(sys.argv) >= 3 else None

    play_mp4_audio_stream(
        path,
        device_index=dev_idx,
        force_stereo=True,   # 모노로 강제하려면 False
        out_rate=48000       # 원본 유지하려면 None
    )
