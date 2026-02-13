from __future__ import annotations

import argparse
from pathlib import Path

from miso_stt.backends.hf_generate import GenerateTranscriber
from miso_stt.core.audio import load_audio
from miso_stt.core.config import normalize_language
from miso_stt.core.timeline import split_segments_by_words


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("wav", nargs="?", default="asset/sample01.wav")
    parser.add_argument("--model", default="small")
    parser.add_argument("--model-path", default=None)
    parser.add_argument("--language", default="ko")
    parser.add_argument("--task", default="transcribe", choices=["transcribe", "translate"])
    parser.add_argument("--device", default="auto")
    parser.add_argument("--no-fp16", action="store_true")
    parser.add_argument("--print-info", action="store_true")
    args = parser.parse_args()

    transcriber = GenerateTranscriber(
        model_name=args.model,
        model_path=args.model_path,
        device=args.device,
        fp16=not args.no_fp16,
    )
    if args.print_info:
        transcriber.print_model_info()
    waveform, sample_rate = load_audio(Path(args.wav))

    text, segments = transcriber.transcribe_full_timeline(
        waveform=waveform,
        sample_rate=sample_rate,
        language=normalize_language(args.language),
        task=args.task,
    )

    print(f"Model: {transcriber.model_id}")
    print("\n=== RESULT (FULLTEXT) ===")
    print(text)
    print("\n=== TIMELINE (WORD) ===")
    for seg in split_segments_by_words(segments): 
        print(f"{seg.start:.2f}:{seg.end:.2f} | {seg.text}")


if __name__ == "__main__":
    main()
