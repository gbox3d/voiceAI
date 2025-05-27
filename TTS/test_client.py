# filename: tts_client_ui.py
# Author: [based on tts_client.py]
# Created: 2025-03-26
# Description: TTS Client with Tkinter UI

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
import socket
import struct
import sys
import io
import os
import threading
import pygame  # pip install pygame
import time
import tempfile

class TTSClientApp:
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
    
    def __init__(self, root):
        self.root = root
        self.root.title("TTS Client")
        self.root.geometry("600x650")
        self.root.resizable(True, True)
        
        # 오디오 포맷 매핑
        self.formats = {
            "WAV": 1,
            "MP3": 2
        }
        
        # 에러 코드 매핑
        self.error_codes = {
            self.SUCCESS: "성공",
            self.ERR_CHECKCODE_MISMATCH: "체크코드 불일치",
            self.ERR_INVALID_DATA: "잘못된 데이터",
            self.ERR_INVALID_REQUEST: "잘못된 요청",
            self.ERR_INVALID_PARAMETER: "잘못된 매개변수",
            self.ERR_INVALID_FORMAT: "잘못된 포맷",
            self.ERR_UNKNOWN_CODE: "알 수 없는 코드",
            self.ERR_EXCEPTION: "서버 예외 발생",
            self.ERR_TIMEOUT: "시간 초과"
        }
        
        # Pygame 초기화 (오디오 재생용)
        pygame.mixer.init()
        
        # 메모리에 오디오 데이터 저장
        self.audio_data = None
        self.audio_format = None
        
        # UI 구성
        self.setup_ui()
        
        # 설정 불러오기
        self.loadConfig()
        
    def setup_ui(self):
        # 프레임 구성
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # === 서버 설정 영역 ===
        server_frame = ttk.LabelFrame(main_frame, text="서버 설정", padding="10")
        server_frame.pack(fill=tk.X, pady=5)
        
        # 호스트, 포트 입력
        ttk.Label(server_frame, text="호스트:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        self.host_entry = ttk.Entry(server_frame)
        self.host_entry.insert(0, "localhost")
        self.host_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=5, pady=5)
        
        ttk.Label(server_frame, text="포트:").grid(row=0, column=2, sticky=tk.W, padx=5, pady=5)
        self.port_entry = ttk.Entry(server_frame, width=10)
        self.port_entry.insert(0, "2501")
        self.port_entry.grid(row=0, column=3, sticky=tk.W, padx=5, pady=5)
        
        ttk.Label(server_frame, text="포맷:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        self.format_combo = ttk.Combobox(server_frame, values=list(self.formats.keys()), width=8)
        self.format_combo.current(0)  # WAV를 기본값으로 설정
        self.format_combo.grid(row=1, column=1, sticky=tk.W, padx=5, pady=5)
        
        # 요청 유형 선택 라디오 버튼
        self.request_type = tk.IntVar(value=self.REQ_TTS)
        ttk.Label(server_frame, text="요청 유형:").grid(row=1, column=2, sticky=tk.W, padx=5, pady=5)
        request_frame = ttk.Frame(server_frame)
        request_frame.grid(row=1, column=3, sticky=tk.W, padx=5, pady=5)
        ttk.Radiobutton(request_frame, text="TTS", variable=self.request_type, value=self.REQ_TTS).pack(side=tk.LEFT)
        ttk.Radiobutton(request_frame, text="Ping", variable=self.request_type, value=self.REQ_PING).pack(side=tk.LEFT)
        
        # === 텍스트 입력 영역 ===
        text_frame = ttk.LabelFrame(main_frame, text="변환할 텍스트", padding="10")
        text_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        self.text_input = scrolledtext.ScrolledText(text_frame, height=8, wrap=tk.WORD)
        self.text_input.insert(tk.END, """안녕하세요, T T S 시스템 테스트입니다. 지금부터 시작 하겠습니다. 
간장 공장 공장장은 강 공장장이고 된장 공장 공장장은 장 공장장이다. 
강된장 공장 공장장은 공 공장장이다.
내가 그린 기린 그림은 목이 긴 기린 그린 그림이고, 네가 그린 기린 그림은 목이 안 긴 기린 그린 그림이다.
                               """
                               
                               
                               )
        self.text_input.pack(fill=tk.BOTH, expand=True)
        
        # === 버튼 영역 ===
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=5)
        
        self.convert_button = ttk.Button(button_frame, text="요청 전송", command=self.send_request)
        self.convert_button.pack(side=tk.LEFT, padx=5)
        
        self.play_button = ttk.Button(button_frame, text="음성 재생", command=self.play_audio, state=tk.DISABLED)
        self.play_button.pack(side=tk.LEFT, padx=5)
        
        self.save_button = ttk.Button(button_frame, text="다른 이름으로 저장", command=self.save_audio, state=tk.DISABLED)
        self.save_button.pack(side=tk.LEFT, padx=5)
        
        self.saveConfig_button = ttk.Button(button_frame, text="설정 저장", command=self.saveConfig)
        self.saveConfig_button.pack(side=tk.LEFT, padx=5)
        
        # === 로그 영역 ===
        log_frame = ttk.LabelFrame(main_frame, text="로그", padding="10")
        log_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        self.log_area = scrolledtext.ScrolledText(log_frame, height=10, wrap=tk.WORD)
        self.log_area.pack(fill=tk.BOTH, expand=True)
        self.log_area.config(state=tk.DISABLED)
        
        # === 상태바 ===
        self.status_var = tk.StringVar()
        self.status_var.set("준비됨")
        status_bar = ttk.Label(main_frame, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.pack(fill=tk.X, pady=5)
        
    def log(self, message):
        """로그 영역에 메시지 추가"""
        self.log_area.config(state=tk.NORMAL)
        self.log_area.insert(tk.END, message + "\n")
        self.log_area.see(tk.END)  # 스크롤을 항상 마지막으로
        self.log_area.config(state=tk.DISABLED)
        
    def create_request_header(self, req_code, format_code=0):
        """요청 헤더 생성 (32바이트)"""
        header = bytearray(self.HEADER_SIZE)
        
        # 체크코드 삽입 (0-3 바이트)
        header[0:4] = self.CHECKCODE
        
        # 요청 코드 (4 바이트)
        header[4] = req_code
        
        # 포맷 코드 (5 바이트)
        header[5] = format_code
        
        # 타임스탬프 (8-15 바이트)
        timestamp = int(time.time())
        struct.pack_into('!Q', header, 8, timestamp)
        
        # 나머지는 0으로 둠
        
        return header
    
    def send_request(self):
        """요청을 서버로 전송"""
        # 요청 유형 가져오기
        req_code = self.request_type.get()
        
        if req_code == self.REQ_TTS:
            self.convert_text()
        elif req_code == self.REQ_PING:
            self.send_ping()
        else:
            messagebox.showwarning("경고", "지원하지 않는 요청 유형입니다.")
    
    def send_ping(self):
        """핑 요청 전송"""
        # UI 상태 업데이트
        self.convert_button.config(state=tk.DISABLED)
        self.status_var.set("핑 요청 중...")
        self.log("핑 요청 시작...")
        
        # 입력 값 가져오기
        host = self.host_entry.get()
        port = int(self.port_entry.get())
        
        # 스레드에서 실행 (UI 응답성 유지)
        thread = threading.Thread(target=self.send_ping_thread, args=(host, port))
        thread.daemon = True
        thread.start()
    
    def send_ping_thread(self, host, port):
        """별도 스레드에서 핑 요청 전송"""
        try:
            # 소켓 연결
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(10)  # 10초 타임아웃
            
            self.log(f"서버 연결 중: {host}:{port}")
            sock.connect((host, port))
            
            # 헤더 생성 및 전송
            header = self.create_request_header(self.REQ_PING)
            sock.sendall(header)
            
            self.log("핑 요청 전송 완료")
            
            # 응답 헤더 수신 (32바이트)
            response_header = sock.recv(self.HEADER_SIZE)
            
            # 체크코드 확인 (0-3 바이트)
            checkcode = response_header[0:4]
            
            if checkcode != self.CHECKCODE:
                error_msg = f"체크코드 불일치: 기대값={self.CHECKCODE}, 수신값={checkcode}"
                self.log(error_msg)
                self.root.after(0, lambda: messagebox.showerror("오류", error_msg))
                return
            
            # 상태 코드 확인 (4 바이트)
            status = response_header[4]
            
            if status != self.SUCCESS:
                error_msg = f"서버 오류 발생: {self.error_codes.get(status, '알 수 없는 오류')}"
                self.log(error_msg)
                self.root.after(0, lambda: messagebox.showerror("오류", error_msg))
                return
            
            self.log("핑 응답 수신 성공 (Pong)!")
            self.root.after(0, lambda: self.status_var.set("서버가 응답했습니다: Pong!"))
            
        except Exception as e:
            error_msg = f"오류 발생: {str(e)}"
            self.log(error_msg)
            self.root.after(0, lambda: messagebox.showerror("오류", error_msg))
            self.root.after(0, lambda: self.status_var.set("오류 발생"))
        finally:
            sock.close()
            self.root.after(0, lambda: self.convert_button.config(state=tk.NORMAL))
    
    def convert_text(self):
        """텍스트를 음성으로 변환하는 기능"""
        # UI 상태 업데이트
        self.convert_button.config(state=tk.DISABLED)
        self.status_var.set("변환 중...")
        self.log("변환 시작...")
        
        # 입력 값 가져오기
        host = self.host_entry.get()
        port = int(self.port_entry.get())
        format_name = self.format_combo.get()
        format_code = self.formats[format_name]
        text = self.text_input.get("1.0", tk.END).strip()
        
        if not text:
            messagebox.showwarning("경고", "변환할 텍스트를 입력해주세요.")
            self.convert_button.config(state=tk.NORMAL)
            self.status_var.set("준비됨")
            return
        
        # 스레드에서 실행 (UI 응답성 유지)
        thread = threading.Thread(target=self.send_text_to_tts_thread, 
                                 args=(host, port, text, format_code))
        thread.daemon = True
        thread.start()
    
    def send_text_to_tts_thread(self, host, port, text, format_code):
        """별도 스레드에서 TTS 서버에 요청 전송"""
        try:
            # 포맷 코드에 따른 확장자 매핑
            format_extensions = {1: 'wav', 2: 'mp3'}
            
            # 소켓 연결
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(30)  # 30초 타임아웃 
            
            self.log(f"서버 연결 중: {host}:{port}")
            sock.connect((host, port))
            
            # 헤더 생성 및 전송
            header = self.create_request_header(self.REQ_TTS, format_code)
            sock.sendall(header)
            
            # 텍스트 데이터 전송
            text_bytes = text.encode('utf-8')
            sock.sendall(struct.pack('!I', len(text_bytes)))
            sock.sendall(text_bytes)
            
            self.log(f"텍스트 전송 완료: {len(text_bytes)} 바이트")
            
            # 응답 헤더 수신 (32바이트)
            response_header = sock.recv(self.HEADER_SIZE)
            
            # 체크코드 확인 (0-3 바이트)
            checkcode = response_header[0:4] 
            
            if checkcode != self.CHECKCODE:
                error_msg = f"체크코드 불일치: 기대값={self.CHECKCODE}, 수신값={checkcode}"
                self.log(error_msg)
                self.root.after(0, lambda: messagebox.showerror("오류", error_msg))
                return
            
            # 상태 코드 확인 (4 바이트)
            status = response_header[4]
            
            if status != self.SUCCESS:
                error_msg = f"서버 오류 발생: {self.error_codes.get(status, '알 수 없는 오류')}"
                self.log(error_msg)
                self.root.after(0, lambda: messagebox.showerror("오류", error_msg))
                return
            
            # 페이로드 크기 확인 (16-19 바이트)
            audio_size = struct.unpack('!I', response_header[16:20])[0]
            self.log(f"수신할 오디오 데이터 크기: {audio_size} 바이트")
            
            # 오디오 데이터 수신
            audio_data = b''
            while len(audio_data) < audio_size:
                chunk = sock.recv(min(4096, audio_size - len(audio_data)))
                if not chunk:
                    break
                audio_data += chunk
            
            self.log(f"오디오 데이터 수신 완료: {len(audio_data)} 바이트")
            
            # 메모리에 오디오 데이터 저장
            self.audio_data = audio_data
            self.audio_format = format_extensions.get(format_code, 'wav')
            
            # UI 업데이트 (메인 스레드에서)
            self.root.after(0, lambda: self.status_var.set(f"변환 완료: 메모리에 {len(audio_data)} 바이트 저장됨"))
            self.root.after(0, lambda: self.convert_button.config(state=tk.NORMAL))
            self.root.after(0, lambda: self.play_button.config(state=tk.NORMAL))
            self.root.after(0, lambda: self.save_button.config(state=tk.NORMAL))
            
        except Exception as e:
            error_msg = f"오류 발생: {str(e)}"
            self.log(error_msg)
            self.root.after(0, lambda: messagebox.showerror("오류", error_msg))
            self.root.after(0, lambda: self.status_var.set("오류 발생"))
            self.root.after(0, lambda: self.convert_button.config(state=tk.NORMAL))
        finally:
            sock.close()
    
    def play_audio(self):
        """메모리에 저장된 오디오 데이터 재생"""
        if self.audio_data is None:
            messagebox.showwarning("경고", "재생할 오디오 데이터가 없습니다.")
            return
            
        try:
            # 현재 재생 중인 오디오 중지
            pygame.mixer.music.stop()
            
            # 임시 파일 생성 (pygame은 파일이나 파일 객체가 필요함)
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=f".{self.audio_format}")
            temp_file.write(self.audio_data)
            temp_file.close()
            
            # 새 오디오 로드 및 재생
            pygame.mixer.music.load(temp_file.name)
            pygame.mixer.music.play()
            
            self.status_var.set(f"재생 중: 메모리에 저장된 오디오")
            self.log(f"오디오 재생 중 (크기: {len(self.audio_data)} 바이트)")
            
            # 임시 파일 삭제 (Windows에서는 재생 중에 삭제할 수 없으므로 나중에 삭제)
            def delete_temp_file():
                # 재생이 끝날 때까지 기다림
                while pygame.mixer.music.get_busy():
                    time.sleep(0.1)
                try:
                    os.unlink(temp_file.name)
                except:
                    pass  # 삭제 실패 무시
                    
            # 별도 스레드에서 임시 파일 삭제
            cleanup_thread = threading.Thread(target=delete_temp_file)
            cleanup_thread.daemon = True
            cleanup_thread.start()
            
        except Exception as e:
            messagebox.showerror("재생 오류", f"오디오 재생 중 오류 발생: {str(e)}")
    
    def save_audio(self):
        """메모리에 저장된 오디오 데이터를 파일로 저장"""
        if self.audio_data is None:
            messagebox.showwarning("경고", "저장할 오디오 데이터가 없습니다.")
            return
            
        filetypes = [(f"{self.audio_format.upper()} 파일", f"*.{self.audio_format}")]
        default_name = f"tts_output.{self.audio_format}"
        
        filename = filedialog.asksaveasfilename(
            defaultextension=f".{self.audio_format}",
            filetypes=filetypes,
            initialfile=default_name,
            title="오디오 파일 저장"
        )
        
        if filename:
            try:
                # 파일로 저장
                with open(filename, 'wb') as f:
                    f.write(self.audio_data)
                self.log(f"파일을 저장했습니다: {filename}")
                self.status_var.set(f"파일 저장 완료: {os.path.basename(filename)}")
            except Exception as e:
                messagebox.showerror("저장 오류", f"파일 저장 중 오류 발생: {str(e)}")
                
    def saveConfig(self):
        host = self.host_entry.get()
        port = self.port_entry.get()
        format_name = self.format_combo.get()
        with open('config.txt', 'w') as f:
            f.write(f"{host}\n{port}\n{format_name}")
        self.log("설정을 저장했습니다.")
        self.status_var.set("설정 저장 완료")
        
    def loadConfig(self) : 
        try:
            with open('TTS/config.txt', 'r') as f:
                lines = f.readlines()
                host = lines[0].strip()
                port = lines[1].strip()
                format_name = lines[2].strip()
                self.host_entry.delete(0, tk.END)
                self.host_entry.insert(0, host)
                self.port_entry.delete(0, tk.END)
                self.port_entry.insert(0, port)
                self.format_combo.set(format_name)
                self.log("설정을 불러왔습니다.")
                self.status_var.set("설정 불러오기 완료")
        except Exception as e:
            self.log(f"설정 불러오기 실패: {str(e)}")
            self.status_var.set("설정 불러오기 실패")

def main():
    root = tk.Tk()
    app = TTSClientApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()