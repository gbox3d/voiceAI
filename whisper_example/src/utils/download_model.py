"""
Download Whisper models into local cache directories.

Usage examples:
    uv run python -m utils.download_model small
    uv run python -m utils.download_model large-v3 --ct2
    uv run python -m utils.download_model small --all
    uv run python -m utils.download_model openai/whisper-large-v3-turbo
    uv run python -m utils.download_model Systran/faster-whisper-large-v3 --ct2
    uv run python -m utils.download_model --list
"""
from __future__ import annotations

import argparse
import time
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from miso_stt.backends.hf_generate import GenerateTranscriber
from miso_stt.core.config import (
    MODEL_DIR,
    HF_CACHE_DIR,
    CT2_CACHE_DIR,
    get_device,
    get_compute_type,
    resolve_ct2_model_id,
)

console = Console()


def download_transformers(model_name: str, device: str = "auto", fp16: bool = True) -> None:
    """Transformers (openai/whisper-*) 모델을 models/huggingface/ 에 다운로드."""
    console.print(Panel.fit(
        f"[bold]Model:[/bold]  {model_name}\n"
        f"[bold]Type:[/bold]   Transformers\n"
        f"[bold]Cache:[/bold]  {HF_CACHE_DIR}",
        title="Download",
    ))

    t0 = time.perf_counter()
    backend = GenerateTranscriber(
        model_name=model_name,
        device=device,
        fp16=fp16,
    )
    model_id = backend.model_id
    torch_device = backend.torch_device
    console.print("[green]Processor OK[/green]")
    elapsed = time.perf_counter() - t0
    console.print(f"[bold]Resolved:[/bold] {model_id} ({torch_device})")
    console.print(f"[bold green]Transformers 모델 다운로드 완료 ({elapsed:.1f}s)[/bold green]")


def download_ct2(model_name: str, device: str = "auto", fp16: bool = True) -> None:
    """CT2 (Systran/faster-whisper-*) 모델을 models/faster_whisper/ 에 다운로드."""
    import torch
    from faster_whisper import WhisperModel

    model_id = resolve_ct2_model_id(model_name)
    torch_device = get_device(device)
    compute_type = get_compute_type(torch_device, fp16=fp16)

    console.print(Panel.fit(
        f"[bold]Model:[/bold]         {model_id}\n"
        f"[bold]Type:[/bold]          CT2 (faster-whisper)\n"
        f"[bold]Compute Type:[/bold]  {compute_type}\n"
        f"[bold]Cache:[/bold]         {CT2_CACHE_DIR}",
        title="Download",
    ))

    t0 = time.perf_counter()
    model = WhisperModel(
        model_id,
        device=torch_device.type,
        compute_type=compute_type,
        download_root=str(CT2_CACHE_DIR),
    )
    elapsed = time.perf_counter() - t0
    console.print(f"[bold green]CT2 모델 다운로드 완료 ({elapsed:.1f}s)[/bold green]")


def _find_hf_models(cache_dir: Path) -> list[tuple[str, str]]:
    """HF 캐시 구조에서 다운로드된 모델 목록 반환. [(name, path), ...]"""
    results = []
    for d in sorted(cache_dir.iterdir()) if cache_dir.exists() else []:
        if d.is_dir() and d.name.startswith("models--"):
            name = d.name.replace("models--", "").replace("--", "/")
            # snapshots 아래 실제 파일이 있는지 확인
            snapshots = d / "snapshots"
            if snapshots.exists() and any(snapshots.iterdir()):
                snap = next(snapshots.iterdir())
                results.append((name, str(snap)))
    return results


def list_models() -> None:
    """다운로드된 모델 목록 출력."""
    console.rule("[bold]Downloaded Models[/bold]")

    # Transformers
    table = Table(title="Transformers (HuggingFace)")
    table.add_column("Model", style="cyan")
    table.add_column("Path")
    for name, path in _find_hf_models(HF_CACHE_DIR):
        table.add_row(name, path)
    console.print(table)

    # CT2
    console.print()
    table2 = Table(title="CT2 (faster-whisper)")
    table2.add_column("Model", style="cyan")
    table2.add_column("Path")
    for name, path in _find_hf_models(CT2_CACHE_DIR):
        table2.add_row(name, path)
    console.print(table2)

    console.print(f"\n[dim]모델 저장 위치: {MODEL_DIR}[/dim]")


def main() -> None:
    p = argparse.ArgumentParser(description="Whisper 모델 다운로드")
    p.add_argument("model", type=str, nargs="?", default="small",
                    help="모델 크기(tiny/base/small/medium/large-v3) 또는 HF ID(openai/whisper-large-v3-turbo)")
    p.add_argument("--ct2", action="store_true", help="CT2 (faster-whisper) 모델 다운로드")
    p.add_argument("--all", action="store_true", help="Transformers + CT2 모두 다운로드")
    p.add_argument("--device", type=str, default="auto")
    p.add_argument("--no-fp16", action="store_true")
    p.add_argument("--list", action="store_true", help="다운로드된 모델 목록 확인")
    args = p.parse_args()

    if args.list:
        list_models()
        return

    fp16 = not args.no_fp16
    model = args.model
    is_hf_id = "/" in model  # HF ID 직접 지정 여부

    # HF ID에 'faster-whisper' 또는 'ct2'가 포함되면 자동으로 CT2 모드
    auto_ct2 = is_hf_id and ("faster-whisper" in model.lower() or "ct2" in model.lower())

    if args.all:
        if is_hf_id and not auto_ct2:
            download_transformers(model, args.device, fp16)
        elif auto_ct2:
            download_ct2(model, args.device, fp16)
        else:
            download_transformers(model, args.device, fp16)
            console.print()
            download_ct2(model, args.device, fp16)
    elif args.ct2 or auto_ct2:
        download_ct2(model, args.device, fp16)
    else:
        download_transformers(model, args.device, fp16)


if __name__ == "__main__":
    main()
