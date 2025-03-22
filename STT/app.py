import os
import sys
import argparse
import asyncio
from dotenv import load_dotenv
from server import AsrServer


import torch
import numpy as np
from pydub import AudioSegment # pip install pydub

# pydub.AudioSegment는 ffmpeg/avconv가 설치되어 있어야 mp3, webm 등을 처리 가능
# (pip install pydub, 그리고 OS에 ffmpeg 설치 필요)

from transformers import AutoModelForSpeechSeq2Seq, AutoProcessor, pipeline # pip install transformers

# FutureWarning 제거
import warnings
warnings.filterwarnings("ignore", category=FutureWarning)



def main():
    # 1) 커맨드라인 인자 파서 설정
    parser = argparse.ArgumentParser(description="Run the async server with a custom .env file path.")
    parser.add_argument('--env', default='.env', help="Path to the .env file (default: .env)")
    args = parser.parse_args()
    
    # print(f"[INFO] .env file path: {args.env}")

    # 2) .env 파일 로드
    if os.path.exists(args.env):
        load_dotenv(dotenv_path=args.env)
        print(f"[INFO] Loaded environment file: {args.env}")
    else:
        print(f"[WARNING] .env file not found: {args.env}")
        
    # model load
    device = "cuda:0" if torch.cuda.is_available() else "cpu"
    torch_dtype = torch.float16 if torch.cuda.is_available() else torch.float32

    model_id = "openai/whisper-large-v3-turbo"
    print("[INFO] 모델과 프로세서 로딩 중...")
    model = AutoModelForSpeechSeq2Seq.from_pretrained(
        model_id,
        torch_dtype=torch_dtype,
        low_cpu_mem_usage=True,
        use_safetensors=True
    ).to(device)
    processor = AutoProcessor.from_pretrained(model_id)

    # STT 파이프라인 구성
    stt_pipeline = pipeline(
        task="automatic-speech-recognition",
        model=model,
        tokenizer=processor.tokenizer,
        feature_extractor=processor.feature_extractor,
        device=0 if device.startswith("cuda") else -1
    )
    
    print(f"[INFO] STT 파이프라인 구성 완료. (device: {device})")
    
    # 서버 실행
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
            stt_pipeline=stt_pipeline
        )
        asyncio.run(server.run_server())
        
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(e)


if __name__ == "__main__":
    main()