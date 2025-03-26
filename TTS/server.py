# filename: tts_server.py
# Author: gbox3d
# Created: 2025-03-26
# Description: This file is a part of TTS App Server
# 위의 소스정보 부분을 수정하지 않습니다. 아래 부터 수정할수있습니다.

import asyncio
import struct
import sys
import os
import io

import torch
import numpy as np
import scipy.io.wavfile

from transformers import VitsModel, AutoTokenizer

#---------------------------------------------------------
# 1. 오디오 데이터 인코딩 함수
#---------------------------------------------------------
def encode_audio(waveform, sample_rate, audio_format='wav'):
    """
    numpy 배열을 바이트 형식의 오디오 데이터로 변환
    
    Parameters:
    waveform (numpy.ndarray): 오디오 파형 데이터
    sample_rate (int): 샘플링 레이트
    audio_format (str): 변환할 오디오 포맷 ('wav', 'mp3', 등)
    
    Returns:
    bytes: 인코딩된 오디오 데이터
    """
    # 임시 파일로 WAV 저장
    temp_wav = io.BytesIO()
    # 오디오 데이터가 [-1, 1] 범위이면 int16 범위로 변환
    if waveform.max() <= 1.0 and waveform.min() >= -1.0:
        waveform = (waveform * 32767).astype(np.int16)
    scipy.io.wavfile.write(temp_wav, sample_rate, waveform)
    temp_wav.seek(0)
    
    # 요청된 포맷으로 변환
    from pydub import AudioSegment
    audio = AudioSegment.from_wav(temp_wav)
    
    output = io.BytesIO()
    if audio_format == 'wav':
        audio.export(output, format='wav')
    elif audio_format == 'mp3':
        audio.export(output, format='mp3')
    elif audio_format == 'webm':
        audio.export(output, format='webm')
    elif audio_format == 'mp4':
        audio.export(output, format='mp4')
    else:
        # 기본값은 wav
        audio.export(output, format='wav')
    
    output.seek(0)
    return output.read()

#---------------------------------------------------------
# 2. 비동기 서버 클래스
#---------------------------------------------------------
class TtsServer:
    # --- status_code 정의 ---
    SUCCESS = 0
    ERR_CHECKCODE_MISMATCH = 1
    ERR_INVALID_DATA = 2
    ERR_INVALID_REQUEST = 3
    ERR_INVALID_PARAMETER = 4
    ERR_INVALID_FORMAT = 5
    ERR_UNKNOWN_CODE = 8
    ERR_EXCEPTION = 9
    ERR_TIMEOUT = 10

    def __init__(self, host=None, port=None, timeout=None, checkcode=None, tts_model=None, tts_tokenizer=None):
        # 환경 변수나 기본값으로 설정
        self.host = host or os.getenv("TTS_HOST", "0.0.0.0")
        self.port = port or int(os.getenv("TTS_PORT", 2501))
        
        # timeout 값이 문자열이면 int로 변환합니다.
        if timeout is not None:
            self.timeout = int(timeout)
        else:
            self.timeout = int(os.getenv("TTS_TIMEOUT", 10))
            
        self.checkcode = checkcode or int(os.getenv("TTS_CHECKCODE", 20250326))

        self.tts_model = tts_model
        self.tts_tokenizer = tts_tokenizer
        
        # 기본 오디오 설정
        self.default_sample_rate = 16000  # MMS-TTS의 기본 샘플레이트

    async def receive_data_with_timeout(self, reader, size, label):
        """
        비동기 방식으로 데이터 수신 (타임아웃 포함)
          - size 바이트 만큼 정확히 읽는다.
        """
        try:
            data = await asyncio.wait_for(reader.readexactly(size), timeout=self.timeout)
            return data
        except asyncio.TimeoutError:
            print(f"[ERROR] {label} 수신 타임아웃 발생")
            return None
        except Exception as e:
            print(f"[ERROR] {label} 수신 중 예외 발생: {e}")
            return None

    async def handle_client(self, reader, writer):
        addr = writer.get_extra_info('peername')
        print(f"[INFO] 클라이언트 연결됨: {addr}")

        try:
            #------------------------------------------------
            # 1) 헤더(8바이트) 수신: checkcode(4) + request_code(4)
            #------------------------------------------------
            header = await reader.readexactly(8)
            checkcode, request_code = struct.unpack('!ii', header)
            print(f"[INFO] 요청 - checkcode: {checkcode}, code: {request_code}")

            #------------------------------------------------
            # 2) checkcode 확인
            #------------------------------------------------
            if checkcode != self.checkcode:
                print("[ERROR] 잘못된 checkcode")
                response = struct.pack('!iiB', self.checkcode, request_code, self.ERR_CHECKCODE_MISMATCH)
                writer.write(response)
                await writer.drain()
                return

            #------------------------------------------------
            # 3) 요청 코드별 처리
            #------------------------------------------------
            if request_code == 99:
                # Ping
                print("[INFO] Ping 요청 수신")
                response = struct.pack('!iiB', self.checkcode, request_code, self.SUCCESS)
                writer.write(response)
                await writer.drain()

            elif request_code == 0x01:
                #------------------------------------------------
                # (A) 오디오 포맷코드(예: 1바이트) 수신
                #------------------------------------------------
                format_byte = await self.receive_data_with_timeout(reader, 1, "Audio Format Code")
                if not format_byte:
                    print("[ERROR] 오디오 포맷 코드 수신 실패")
                    response = struct.pack('!iiB', self.checkcode, request_code, self.ERR_INVALID_FORMAT)
                    writer.write(response)
                    await writer.drain()
                    return

                format_code = struct.unpack('!B', format_byte)[0]

                # 포맷 매핑 예시 (원하는 방식으로 확장 가능)
                format_map = {
                    1: "wav",
                    2: "mp3",
                    3: "webm",
                    4: "mp4"
                }

                if format_code not in format_map:
                    print(f"[ERROR] 지원하지 않는 포맷 코드: {format_code}")
                    response = struct.pack('!iiB', self.checkcode, request_code, self.ERR_INVALID_FORMAT)
                    writer.write(response)
                    await writer.drain()
                    return

                audio_format_str = format_map[format_code]
                print(f"[INFO] 오디오 출력 포맷: {audio_format_str}")

                #------------------------------------------------
                # (B) 텍스트 데이터 길이(4바이트) 수신 후, 텍스트 데이터
                #------------------------------------------------
                size_bytes = await self.receive_data_with_timeout(reader, 4, "Text Data Size")
                if not size_bytes:
                    print("[ERROR] 텍스트 데이터 길이 정보 수신 실패")
                    response = struct.pack('!iiB', self.checkcode, request_code, self.ERR_INVALID_DATA)
                    writer.write(response)
                    await writer.drain()
                    return
                
                text_size = struct.unpack('!i', size_bytes)[0]
                print(f"[INFO] 텍스트 데이터 길이: {text_size} 바이트")
                text_data = await self.receive_data_with_timeout(reader, text_size, "Text Data")
                if not text_data:
                    print("[ERROR] 텍스트 데이터 수신 실패")
                    response = struct.pack('!iiB', self.checkcode, request_code, self.ERR_INVALID_DATA)
                    writer.write(response)
                    await writer.drain()
                    return

                text = text_data.decode('utf-8')
                print(f"[INFO] 변환할 텍스트: {text}")

                #------------------------------------------------
                # (C) MMS-TTS 모델 TTS 처리
                #------------------------------------------------
                if not self.tts_model or not self.tts_tokenizer:
                    print("[ERROR] TTS 모델 또는 토크나이저가 초기화되지 않음")
                    response = struct.pack('!iiB', self.checkcode, request_code, self.ERR_INVALID_REQUEST)
                    writer.write(response)
                    await writer.drain()
                    return

                try:
                    # 1) 텍스트를 토큰화
                    inputs = self.tts_tokenizer(text, return_tensors="pt")
                    
                    # 2) TTS 모델로 오디오 생성
                    with torch.no_grad():
                        output = self.tts_model(**inputs).waveform[0].cpu().numpy()
                    
                    print(f"[INFO] 오디오 생성 완료: shape={output.shape}")

                    # 3) 오디오 인코딩 (요청된 포맷으로)
                    audio_data = encode_audio(output, self.default_sample_rate, audio_format_str)
                    
                except Exception as e:
                    print(f"[ERROR] TTS 변환 중 예외 발생: {e}")
                    response = struct.pack('!iiB', self.checkcode, request_code, self.ERR_EXCEPTION)
                    writer.write(response)
                    await writer.drain()
                    return

                #------------------------------------------------
                # (D) 변환 결과 전송
                #------------------------------------------------
                response_header = struct.pack('!iiB', self.checkcode, request_code, self.SUCCESS)
                response_length = struct.pack('!i', len(audio_data))
                response = response_header + response_length + audio_data

                writer.write(response)
                await writer.drain()

            else:
                print(f"[ERROR] 알 수 없는 요청 코드: {request_code}")
                response = struct.pack('!iiB', self.checkcode, request_code, self.ERR_UNKNOWN_CODE)
                writer.write(response)
                await writer.drain()

        except asyncio.IncompleteReadError:
            print("[ERROR] 클라이언트 데이터 수신 실패")
        except Exception as e:
            print(f"[ERROR] 처리 중 예외 발생: {e}")
        finally:
            writer.close()
            await writer.wait_closed()
            print(f"[INFO] 클라이언트 연결 종료: {addr}")

    async def run_server(self):
        server = await asyncio.start_server(self.handle_client, self.host, self.port)
        addr = server.sockets[0].getsockname()
        print(f"[INFO] TTS 서버 시작: {addr}, TIMEOUT={self.timeout}s, CHECKCODE={self.checkcode}")

        try:
            async with server:
                await server.serve_forever()
        except KeyboardInterrupt:
            # Ctrl+C(KeyInterrupt) 시, 에러 메시지 없이 종료
            print("\n[INFO] 서버가 종료됩니다 (KeyboardInterrupt).")
            server.close()
            await server.wait_closed()
            sys.exit(0)
