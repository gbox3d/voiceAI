# filename: server.py
# author: gbox3d
# created: 2025-03-26
# 이 주석은 수정하지 마세요.

import os
import asyncio
import struct
import socket
import io
import sys
import time
import hashlib

import torch
import numpy as np
from transformers import VitsModel, AutoTokenizer
from pydub import AudioSegment

class TTSServer:
    # 상태 코드 정의
    SUCCESS = 0
    ERR_CHECKCODE_MISMATCH = 1
    ERR_INVALID_DATA = 2
    ERR_INVALID_REQUEST = 3
    ERR_INVALID_PARAMETER = 4
    ERR_INVALID_FORMAT = 5
    ERR_UNKNOWN_CODE = 8
    ERR_EXCEPTION = 9
    ERR_TIMEOUT = 10
    
    # 요청 코드 정의
    REQ_TTS = 0x01
    REQ_PING = 99
    
    # 헤더 사이즈
    HEADER_SIZE = 32
    
    # 체크코드 (고정값 - 서버와 클라이언트 간 약속된 값)
    CHECKCODE = b'TTS1'  # 체크코드는 4바이트

    def __init__(self, host="0.0.0.0", port=2501, model_path=None):
        self.host = host
        self.port = port
        self.model_path = model_path or "./weights/mms_tts_kor_local"
        
        # 모델 초기화
        self.load_model()

    def load_model(self):
        """모델 및 토크나이저 로드"""
        print(f"[INFO] 모델 로딩 중... (경로: {self.model_path})")
        
        # 로컬 경로에 모델이 없다면 다운로드
        if not os.path.exists(self.model_path):
            print("[INFO] 로컬에 모델이 없습니다. 다운로드 후 저장합니다...")
            os.makedirs(self.model_path, exist_ok=True)
            
            temp_model = VitsModel.from_pretrained("facebook/mms-tts-kor")
            temp_tokenizer = AutoTokenizer.from_pretrained("facebook/mms-tts-kor")
            
            temp_model.save_pretrained(self.model_path)
            temp_tokenizer.save_pretrained(self.model_path)
            
            del temp_model, temp_tokenizer
            
            print("[INFO] 모델 다운로드 및 저장 완료")
        
        # 로컬 경로에서 모델 로드
        self.model = VitsModel.from_pretrained(self.model_path)
        self.tokenizer = AutoTokenizer.from_pretrained(self.model_path)
        self.sample_rate = self.model.config.sampling_rate
        
        print(f"[INFO] 모델 로드 완료 (샘플링 레이트: {self.sample_rate}Hz)")

    def generate_audio(self, text):
        """텍스트에서 오디오 생성"""
        # 텍스트 토큰화
        inputs = self.tokenizer(text, return_tensors="pt")
        
        # 오디오 생성
        with torch.no_grad():
            output = self.model(**inputs).waveform[0]
        
        # 출력 텐서를 NumPy 배열로 변환
        waveform = output.cpu().numpy()
        
        return waveform

    def convert_to_bytes(self, waveform, format_type):
        """NumPy 배열을 오디오 바이트로 변환"""
        # 정규화 및 int16 변환
        waveform_norm = waveform / np.abs(waveform).max()
        waveform_int16 = (waveform_norm * 32767).astype(np.int16)
        
        # 바이트 스트림으로 변환
        output_buffer = io.BytesIO()
        
        if format_type == 'wav':
            import scipy.io.wavfile
            scipy.io.wavfile.write(output_buffer, self.sample_rate, waveform_int16)
        else:  # mp3, 기본값
            # AudioSegment 생성
            audio_segment = AudioSegment(
                waveform_int16.tobytes(),
                frame_rate=self.sample_rate,
                sample_width=waveform_int16.dtype.itemsize,
                channels=1
            )
            # MP3로 변환
            audio_segment.export(output_buffer, format="mp3", bitrate="192k")
        
        output_buffer.seek(0)
        return output_buffer.read()

    def create_response_header(self, status_code, payload_size=0):
        """응답 헤더 생성"""
        header = bytearray(self.HEADER_SIZE)
        
        # 체크코드 삽입 (0-3 바이트)
        header[0:4] = self.CHECKCODE
        
        # 상태 코드 (4 바이트)
        header[4:5] = struct.pack('!B', status_code)
        
        # 타임스탬프 (8-15 바이트)
        timestamp = int(time.time())
        header[8:16] = struct.pack('!Q', timestamp)
        
        # 페이로드 사이즈 (16-19 바이트)
        header[16:20] = struct.pack('!I', payload_size)
        
        # 예약된 공간은 기본값 0으로 둠
        
        return header

    async def handle_tts_request(self, reader, writer, format_code):
        """TTS 요청 처리"""
        # 텍스트 길이 수신 (4 바이트)
        size_bytes = await reader.readexactly(4)
        text_size = int.from_bytes(size_bytes, byteorder='big')
        
        # 텍스트 데이터 수신
        text_data = await reader.readexactly(text_size)
        text = text_data.decode('utf-8')
        
        print(f"[INFO] 변환 요청 텍스트: {text}")
        
        # 포맷 코드 매핑
        format_map = {1: "wav", 2: "mp3"}
        audio_format = format_map.get(format_code, "mp3")  # 기본값은 mp3
        
        print(f"[INFO] 요청 포맷: {audio_format}")
        
        try:
            # 오디오 생성
            waveform = self.generate_audio(text)
            audio_data = self.convert_to_bytes(waveform, audio_format)
            
            # 응답 헤더 생성
            response_header = self.create_response_header(self.SUCCESS, len(audio_data))
            
            # 응답 전송: 헤더 + 오디오 데이터
            writer.write(response_header + audio_data)
            await writer.drain()
            
            print(f"[INFO] 오디오 전송 완료: {len(audio_data)} 바이트")
            return True
            
        except Exception as e:
            print(f"[ERROR] 오디오 생성 중 오류: {e}")
            response_header = self.create_response_header(self.ERR_EXCEPTION)
            writer.write(response_header)
            await writer.drain()
            return False

    async def handle_ping_request(self, reader, writer):
        """Ping 요청 처리"""
        print(f"[INFO] Ping 요청 수신")
        
        # Ping 응답 (pong) 헤더 생성
        response_header = self.create_response_header(self.SUCCESS)
        
        # 응답 전송
        writer.write(response_header)
        await writer.drain()
        
        print(f"[INFO] Ping 응답 전송 완료")
        return True

    async def handle_client(self, reader, writer):
        """클라이언트 처리 - 비동기"""
        addr = writer.get_extra_info('peername')
        print(f"[INFO] 클라이언트 연결됨: {addr}")
        
        try:
            # 헤더 수신 (32 바이트)
            header = await reader.readexactly(self.HEADER_SIZE)
            
            # 체크코드 확인 (0-3 바이트)
            checkcode = header[0:4]
            if checkcode != self.CHECKCODE:
                print(f"[ERROR] 체크코드 불일치: {checkcode}")
                response_header = self.create_response_header(self.ERR_CHECKCODE_MISMATCH)
                writer.write(response_header)
                await writer.drain()
                return
            
            # 요청 코드 확인 (4 바이트)
            req_code = header[4]
            
            # 포맷 코드 확인 (5 바이트)
            format_code = header[5]
            
            # 요청 코드에 따른 처리
            if req_code == self.REQ_TTS:
                await self.handle_tts_request(reader, writer, format_code)
            elif req_code == self.REQ_PING:
                await self.handle_ping_request(reader, writer)
            else:
                print(f"[ERROR] 알 수 없는 요청 코드: {req_code}")
                response_header = self.create_response_header(self.ERR_UNKNOWN_CODE)
                writer.write(response_header)
                await writer.drain()
        
        except asyncio.IncompleteReadError:
            print("[ERROR] 클라이언트 데이터 수신 실패")
            try:
                response_header = self.create_response_header(self.ERR_INVALID_DATA)
                writer.write(response_header)
                await writer.drain()
            except:
                pass
        
        except Exception as e:
            print(f"[ERROR] 처리 중 예외 발생: {e}")
            try:
                response_header = self.create_response_header(self.ERR_EXCEPTION)
                writer.write(response_header)
                await writer.drain()
            except:
                pass
        
        finally:
            writer.close()
            await writer.wait_closed()
            print(f"[INFO] 클라이언트 연결 종료: {addr}")

    async def run_server(self):
        """서버 실행"""
        server = await asyncio.start_server(
            self.handle_client, self.host, self.port
        )
        
        addr = server.sockets[0].getsockname()
        print(f"[INFO] 개선된 TTS 서버 시작: {addr}")
        print(f"[INFO] 체크코드: {self.CHECKCODE}, 헤더 크기: {self.HEADER_SIZE}바이트")
        
        try:
            async with server:
                await server.serve_forever()
        except KeyboardInterrupt:
            print("\n[INFO] 서버가 종료됩니다.")
            server.close()
            await server.wait_closed()
            sys.exit(0)

# 서버 실행 함수
def start_server(host="0.0.0.0", port=2501, model_path=None):
    """TTS 서버 시작"""
    tts_server = TTSServer(host, port, model_path)
    asyncio.run(tts_server.run_server())

if __name__ == "__main__":
    # 커맨드라인에서 포트 지정 가능
    import argparse
    
    parser = argparse.ArgumentParser(description="개선된 TTS 서버")
    parser.add_argument('--host', default="0.0.0.0", help="서버 호스트 (기본값: 0.0.0.0)")
    parser.add_argument('--port', type=int, default=2501, help="서버 포트 (기본값: 2501)")
    parser.add_argument('--model_path', default="./weights/mms_tts_kor_local", 
                        help="모델 경로 (기본값: ./weights/mms_tts_kor_local)")
    
    args = parser.parse_args()
    
    start_server(args.host, args.port, args.model_path)