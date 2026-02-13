# whisper_example

Whisper 기반 STT 실험/운영용 프로젝트입니다. 현재 구조는 `miso_stt` 패키지를 중심으로 동작하며, 예제 실행은 `miso_stt.examples.*` 모듈을 사용합니다.

## 1. Setup

필수:
- Python 3.11+
- `uv`

설치:
```bash
uv sync
uv pip install -e .
```

## 2. 환경 변수

`.env`에서 모델 저장 루트를 지정할 수 있습니다.

```env
WHISPER_MODEL_DIR=./models
```

캐시는 아래로 분리됩니다.
- HF: `models/huggingface`
- CT2: `models/faster_whisper`

## 3. 유틸리티

### 3.1 GPU 체크
```bash
uv run python -m utils.check_gpu
```

### 3.2 모델 다운로드
```bash
# HF
uv run python -m utils.download_model small
uv run python -m utils.download_model openai/whisper-large-v3-turbo

# CT2
uv run python -m utils.download_model small --ct2
uv run python -m utils.download_model Systran/faster-whisper-large-v3 --ct2

# 둘 다
uv run python -m utils.download_model small --all

# 목록
uv run python -m utils.download_model --list
```

옵션:
```bash
uv run python -m utils.download_model small --device cpu
uv run python -m utils.download_model small --no-fp16
```

## 4. 실행 예제

### 4.1 HF Generate
```bash
uv run python -m miso_stt.examples.ex01_generate asset/sample01.wav
```

### 4.2 HF Pipeline
```bash
uv run python -m miso_stt.examples.ex02_pipeline_full asset/sample01.wav
```

### 4.3 CT2
```bash
uv run python -m miso_stt.examples.ex03_ct2_full asset/sample01.wav
```

공통 옵션 예시:
```bash
uv run python -m miso_stt.examples.ex01_generate asset/sample01.wav --model large-v3 --language none
uv run python -m miso_stt.examples.ex02_pipeline_full asset/sample01.wav --task translate
uv run python -m miso_stt.examples.ex03_ct2_full asset/sample01.wav --print-info
```

## 5. 모델 지정 규칙

모델 지정 우선순위:
1. `--model-path` (명시적 로컬 경로)
2. `--model` (별칭/HF ID/로컬경로 자동탐지)

예시:
```bash
# 병합된 HF 체크포인트 디렉토리
uv run python -m miso_stt.examples.ex01_generate asset/sample01.wav --model-path C:/models/my-whisper-merged

# CT2 변환 모델 디렉토리
uv run python -m miso_stt.examples.ex03_ct2_full asset/sample01.wav --model-path C:/models/my-ct2-model
```

LoRA 정책(HF):
- 미병합 adapter-only 경로는 지원하지 않습니다.
- `config.json`이 있는 병합된 Whisper 체크포인트를 `--model-path`로 지정하세요.

## 6. 백엔드 선택 가이드

- `hf_generate`: 세밀한 제어/연구용
- `hf_pipeline`: 구현 단순/운영 편의
- `ct2`: 빠른 추론/경량 운영

## 7. 통합 API 예시

```python
from pathlib import Path
from miso_stt import WhisperTranscriber
from miso_stt.core.audio import load_audio, TARGET_SR
from miso_stt.core.config import normalize_language

waveform, sr = load_audio(Path("asset/sample01.wav"), target_sr=TARGET_SR)

t = WhisperTranscriber(
    backend="ct2",
    model_name="small",
    model_path=None,
    device="auto",
    fp16=True,
)

text, segments = t.transcribe_full_timeline(
    waveform=waveform,
    sample_rate=sr,
    language=normalize_language("ko"),
    task="transcribe",
)
print(text)
```

## 8. 콘솔 스크립트

`pyproject.toml`에 아래 엔트리가 등록되어 있습니다.
- `miso-stt-ex01`
- `miso-stt-ex02`
- `miso-stt-ex03`

## 9. 배포

```bash
uv run python -m build
uv pip install ./dist/whisper_example-0.1.0-py3-none-any.whl
```
