#%%
import os
import socket
import struct
import argparse
import sys
import numpy as np
from dotenv import load_dotenv

load_dotenv()

server_host = os.getenv("ASR_HOST")
server_port = int(os.getenv("ASR_PORT"))
checkcode = int(os.getenv("ASR_CHECKCODE"))

print(f"[INFO] 서버 주소: {server_host}:{server_port}, checkcode: {checkcode}")

#%%
try:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client_socket:
        client_socket.connect((server_host, server_port))
        # 요청 패킷 생성: checkcode(4 bytes) + code(4 bytes)
        # checkcode = 20250122
        code = 99  # Ping 요청
        packet = struct.pack('!ii', checkcode, code)
        client_socket.sendall(packet)

        # 응답 패킷 수신
        response = client_socket.recv(9)  # checkcode(4) + code(4) + status_code(1)
        if len(response) != 9:
            print("[ERROR] 응답 패킷 길이가 잘못되었습니다.")
            # return
        else:
            res_checkcode, res_code, status_code = struct.unpack('!iiB', response)
            print(f"[INFO] 응답 - checkcode: {res_checkcode}, code: {res_code}, status_code: {status_code}")
except Exception as e:
    print(f"[ERROR] Ping 요청 실패: {e}")
# %%
