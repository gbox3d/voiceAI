import os
import sys
import argparse
import asyncio
from dotenv import load_dotenv
from server import AsrServer

import torch

# transformers
from transformers import AutoModelForSpeechSeq2Seq, AutoProcessor, pipeline

# FutureWarning 제거
import warnings
warnings.filterwarnings("ignore", category=FutureWarning)

def main():
    parser = argparse.ArgumentParser(
        description="Run the async server with offline model files from a local folder."
    )
    parser.add_argument('--env', default='.env', help="Path to the .env file (default: .env)")

    args = parser.parse_args()

    # .env 파일 로드
    if os.path.exists(args.env):
        load_dotenv(dotenv_path=args.env)
        print(f"[INFO] Loaded environment file: {args.env}")
    else:
        print(f"[WARNING] .env file not found: {args.env}")

    # 환경 변수에서 설정값 읽기
    model_dir = os.getenv("MODEL_DIR", "./models")
    model_id = os.getenv("MODEL_ID", "openai/whisper-large-v3-turbo")
    min_text_length = int(os.getenv("MIN_TEXT_LENGTH", 5))
    no_voice_text = os.getenv("NO_VOICE_TEXT", "novoice")


    print(f"[INFO] 모델 ID: {model_id}")
    print(f"[INFO] 모델 디렉토리: {model_dir}")
    print(f"[INFO] 최소 텍스트 길이: {min_text_length}")
    print(f"[INFO] 음성 없음 텍스트: {no_voice_text}")


    # 디바이스 및 dtype 설정
    device = "cuda:0" if torch.cuda.is_available() else "cpu"
    torch_dtype = torch.float16 if torch.cuda.is_available() else torch.float32

    print(f"[INFO] 로컬 모델 로드 중... path: {model_dir}, device: {device}")
    # ① 모델 디렉토리에서 실제 파일을 로드할 때만 local_files_only 사용
    processor = AutoProcessor.from_pretrained(
        model_dir,
        local_files_only=True
    )

    model = AutoModelForSpeechSeq2Seq.from_pretrained(
        model_dir,
        local_files_only=True
    ).to(device)

    stt_pipeline = pipeline(
    "automatic-speech-recognition",
    model=model,
    tokenizer=processor.tokenizer,
    feature_extractor=processor.feature_extractor,
    device=device,           # GPU 인덱스(예: 0) 또는 "cuda:0"    
    )
    print(f"[INFO] STT 파이프라인 구성 완료. (device: {device})")

    try:
        host = os.getenv("ASR_HOST")
        port = int(os.getenv("ASR_PORT"))
        checkcode = int(os.getenv("ASR_CHECKCODE"))
        timeout = os.getenv("ASR_TIMEOUT")

        server = AsrServer(
            host=host,
            port=port,
            checkcode=checkcode,
            timeout=timeout,
            stt_pipeline=stt_pipeline,
            min_text_length=min_text_length,
            no_voice_text=no_voice_text
        )
        asyncio.run(server.run_server())
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(e)

if __name__ == "__main__":
    main()
