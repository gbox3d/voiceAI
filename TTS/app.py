# filename: app.py
# Author: [based on gbox3d's code]
# Created: 2025-03-26
# Description: Main entry point for the TTS App Server using MeloTTS

import os
import sys
import argparse
import asyncio
from dotenv import load_dotenv
from server import TTSServer

import torch
import warnings

# FutureWarning 제거
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
        
    # 3) 서버 설정
    host = os.getenv("TTS_HOST", "0.0.0.0")
    port = int(os.getenv("TTS_PORT", "2501"))
    device = "cuda:0" if torch.cuda.is_available() else "cpu"
    language = os.getenv("TTS_LANGUAGE", "KR")

    print(f"[INFO] TTS 서버 설정 - 호스트: {host}, 포트: {port}, 언어: {language}, 디바이스: {device}")
    
    # 4) 서버 실행
    try:
        server = TTSServer(
            host=host,
            port=port,
            language=language,
            device=device
        )
        asyncio.run(server.run_server())
    except KeyboardInterrupt:
        print("\n[INFO] 서버가 종료됩니다 (KeyboardInterrupt).")
    except Exception as e:
        print(f"[ERROR] 서버 실행 중 오류 발생: {e}")


if __name__ == "__main__":
    main()