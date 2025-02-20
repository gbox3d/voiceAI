#%% STT 요청 예제 클라이언트 코드
import os
import socket
import struct
import sys
from dotenv import load_dotenv

# .env 파일에서 환경변수 로드 (ASR_HOST, ASR_PORT, ASR_CHECKCODE)
load_dotenv()

server_host = os.getenv("ASR_HOST", "127.0.0.1")
server_port = int(os.getenv("ASR_PORT", 2500))
checkcode = int(os.getenv("ASR_CHECKCODE", 20250122))

print(f"[INFO] 서버 주소: {server_host}:{server_port}, checkcode: {checkcode}")

# 전송할 오디오 파일 경로 (webm 포맷)
file_path = "/home/gbox3d/work/web_pub/uploads/recording-1739858011070-196134560_unknown.webm"

#%% 1. 오디오 파일 읽기
try:
    with open(file_path, "rb") as f:
        audio_data = f.read()
    print(f"[INFO] 파일 읽기 완료: {file_path} (크기: {len(audio_data)} bytes)")
except Exception as e:
    print(f"[ERROR] 파일 읽기 실패: {e}")
    sys.exit(1)

#%% 2. STT 요청 패킷 구성
# 헤더: checkcode(4바이트) + request_code(4바이트)
# request_code 0x01: STT 요청
request_code = 0x01
header = struct.pack('!ii', checkcode, request_code)

# 오디오 포맷 코드 (1바이트): webm은 서버의 매핑에 따라 3
format_code = 3
format_code_bytes = struct.pack('!B', format_code)

# 오디오 데이터 길이 (4바이트) + 오디오 데이터
audio_length = len(audio_data)
audio_length_bytes = struct.pack('!i', audio_length)

# 최종 패킷: header + format_code + audio_length + audio_data
packet = header + format_code_bytes + audio_length_bytes + audio_data

#%% 3. 서버로 패킷 전송 및 응답 수신
try:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client_socket:
        client_socket.connect((server_host, server_port))
        print("[INFO] 서버에 연결됨.")

        # STT 요청 패킷 전송
        client_socket.sendall(packet)
        print("[INFO] STT 요청 패킷 전송 완료.")

        # 응답 헤더 수신: checkcode(4) + request_code(4) + status(1)
        response_header = client_socket.recv(9)
        if len(response_header) != 9:
            print("[ERROR] 응답 헤더 길이가 잘못되었습니다.")
            sys.exit(1)

        res_checkcode, res_request_code, status_code = struct.unpack('!iiB', response_header)
        print(f"[INFO] 응답 헤더 - checkcode: {res_checkcode}, request_code: {res_request_code}, status: {status_code}")

        if status_code != 0:
            print(f"[ERROR] 서버에서 오류 발생. status: {status_code}")
            sys.exit(1)

        # 성공일 경우, 다음 4바이트로 텍스트 길이 정보를 받음
        response_length_bytes = client_socket.recv(4)
        if len(response_length_bytes) != 4:
            print("[ERROR] 응답 텍스트 길이 정보 수신 실패.")
            sys.exit(1)
        text_length = struct.unpack('!i', response_length_bytes)[0]

        # 텍스트 데이터 수신
        recognized_text_bytes = b""
        remaining = text_length
        while remaining > 0:
            chunk = client_socket.recv(remaining)
            if not chunk:
                break
            recognized_text_bytes += chunk
            remaining -= len(chunk)

        if len(recognized_text_bytes) != text_length:
            print("[ERROR] 텍스트 데이터 수신 길이 오류.")
            sys.exit(1)

        recognized_text = recognized_text_bytes.decode('utf-8')
        print("[INFO] 인식된 텍스트:")
        print(recognized_text)

except Exception as e:
    print(f"[ERROR] STT 요청 실패: {e}")

# %%
