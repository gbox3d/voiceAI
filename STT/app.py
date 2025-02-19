import os
import sys
import argparse
import asyncio
from dotenv import load_dotenv
from server import AsrServer

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

    # 서버 실행
    try:
        
        host = os.getenv("ASR_HOST")
        port = int(os.getenv("ASR_PORT"))
        checkcode = int(os.getenv("ASR_CHECKCODE"))
        timeout = os.getenv("ASR_TIMEOUT")
        
        server = AsrServer(host=host, port=port, timeout=timeout, checkcode=checkcode)
        asyncio.run(server.run_server())
        
        
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(e)

if __name__ == "__main__":
    main()