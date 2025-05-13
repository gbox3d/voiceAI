"""
STT 클라이언트 헬퍼 사용 예제

이 모듈은 STT 클라이언트 헬퍼의 사용 방법을 보여주는 예제입니다.
"""

import os
from dotenv import load_dotenv
from stt_client import STTClient

# 환경변수 로드
load_dotenv()
test_file_path = os.getenv("ASR_TEST_FILE_PATH")


# 스레드 기반 STT 클라이언트 사용 예제
def thread_example():
    """스레드 기반 STT 클라이언트 사용 예제"""
    print("=== 스레드 기반 STT 클라이언트 사용 예제 ===")
    
    stt_client = STTClient(
        host=os.getenv("ASR_HOST"),
        port=int(os.getenv("ASR_PORT")),
        checkcode=int(os.getenv("ASR_CHECKCODE"))
    )
    
    def on_result(text, error):
        if error:
            print(f"[ERROR] STT 요청 실패: {error}")
        else:
            # print("[INFO] 인식된 텍스트:")
            print(text)
    
    # 파일 경로에서 STT 요청
    print(f"[INFO] 파일 인식 요청 중: {test_file_path}")
    stt_client.recognize_file(test_file_path, on_result)
    
    # 오디오 데이터로 직접 STT 요청 (예제)
    with open(test_file_path, "rb") as f:
        audio_data = f.read()
    
    print("[INFO] 오디오 데이터로 직접 인식 요청 중...")
    stt_client.recognize_audio(audio_data, on_result)
    
    # 모든 요청이 완료될 때까지 대기
    stt_client.wait()
    print("=== 요청 완료 ===")



# 메인 실행 함수
if __name__ == "__main__":
    """이 스크립트를 직접 실행할 경우"""
    
    # 실행할 예제 선택 (주석 처리를 해제하여 사용)
    
    # 1. 스레드 기반 예제 실행
    thread_example()
    
    