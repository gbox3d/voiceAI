# filename: main.py
# Author: [based on gbox3d's code]
# Created: 2025-03-26
# Description: Main entry point for the TTS App Server

import os
import sys
import argparse
import asyncio
from dotenv import load_dotenv
from server import TtsServer

import torch
import numpy as np
from transformers import VitsModel, AutoTokenizer

# FutureWarning 제거
import warnings
warnings.filterwarnings("ignore", category=FutureWarning)

def main():
    # 1) 커맨드라인 인자 파서 설정
    parser = argparse.ArgumentParser(description="Run the TTS server with a custom .env file path.")
    parser.add_argument('--env', default='.env', help="Path to the .env file (default: .env)")
    args = parser.parse_args()

    # 2) .env 파일 로드
    if os.path.exists(args.env):
        load_dotenv(dotenv_path=args.env)
        print(f"[INFO] Loaded environment file: {args.env}")
    else:
        print(f"[WARNING] .env file not found: {args.env}")
        
    # 3) 모델 로드
    device = "cuda:0" if torch.cuda.is_available() else "cpu"
    torch_dtype = torch.float16 if torch.cuda.is_available() else torch.float32

    print("[INFO] TTS 모델과 토크나이저 로딩 중...")
    print(f"[INFO] 사용 디바이스: {device}, 데이터 타입: {torch_dtype}")
    
    try:
        # 모델과 토크나이저 로드
        model = VitsModel.from_pretrained(
            "facebook/mms-tts-kor",
            torch_dtype=torch_dtype,
            low_cpu_mem_usage=True,
            use_safetensors=True
        ).to(device)
        
        # 모델을 평가 모드로 설정 (배치 정규화, 드롭아웃 등을 비활성화)
        model.eval()
        
        tokenizer = AutoTokenizer.from_pretrained("facebook/mms-tts-kor")
        print(f"[INFO] TTS 모델 및 토크나이저 로딩 완료")
    
    except Exception as e:
        print(f"[ERROR] 모델 로딩 중 오류 발생: {e}")
        sys.exit(1)
    
    # 4) 서버 실행
    try:
        host = os.getenv("TTS_HOST", "0.0.0.0")
        port = int(os.getenv("TTS_PORT", "2501"))
        checkcode = int(os.getenv("TTS_CHECKCODE", "20250326"))
        timeout = os.getenv("TTS_TIMEOUT", "10")
        
        server = TtsServer(
            host=host,
            port=port,
            checkcode=checkcode,
            timeout=timeout,
            tts_model=model,
            tts_tokenizer=tokenizer
        )
        
        print(f"[INFO] TTS 서버 시작: {host}:{port}")
        asyncio.run(server.run_server())
        
    except KeyboardInterrupt:
        print("\n[INFO] 서버가 종료됩니다 (KeyboardInterrupt).")
    except Exception as e:
        print(f"[ERROR] 서버 실행 중 오류 발생: {e}")


if __name__ == "__main__":
    main()