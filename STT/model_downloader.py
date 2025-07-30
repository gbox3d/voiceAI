# download_models.py
from huggingface_hub import snapshot_download

from dotenv import load_dotenv


import os


try :
    # .env 파일 로드
    load_dotenv()

    MODEL_ID = os.getenv("MODEL_ID", "openai/whisper-large-v3-turbo")
    MODEL_DIR = os.getenv("MODEL_DIR", "./models/whisper-large-v3-turbo")

    print(f"[INFO] 모델 다운로드 시작: {MODEL_ID} -> {MODEL_DIR}")

    # 저장소 전체를 MODEL_DIR에 내려받음
    # snapshot_download(repo_id=MODEL_ID, cache_dir=MODEL_DIR)

    snapshot_download(
        repo_id=MODEL_ID,
        local_dir=MODEL_DIR,
        local_dir_use_symlinks=False
    )

    print(f"[INFO] 모델 다운로드 완료: {MODEL_DIR}")

except Exception as e:
    print(f"[ERROR] 모델 다운로드 중 오류 발생: {e}")
    exit(1) 
