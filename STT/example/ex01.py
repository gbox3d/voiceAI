import os
import sys
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import torch
from transformers import AutoModelForSpeechSeq2Seq, AutoProcessor, pipeline
import yt_dlp  # pytube 대신 yt-dlp 사용
import urllib.request
import re

class YouTubeTranscriptionApp:
    def __init__(self, root):
        self.root = root
        self.root.title("YouTube 자동 자막 생성기")
        self.root.geometry("800x600")
        self.root.configure(padx=20, pady=20)
        
        # 디바이스 설정
        self.device = "cuda:0" if torch.cuda.is_available() else "cpu"
        self.torch_dtype = torch.float16 if torch.cuda.is_available() else torch.float32
        
        # 상태 변수
        self.model_loaded = False
        self.is_processing = False
        
        # UI 구성
        self.create_widgets()
        
    def create_widgets(self):
        # 상단 프레임 (YouTube URL 입력)
        top_frame = ttk.Frame(self.root)
        top_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(top_frame, text="YouTube URL:").pack(side=tk.LEFT, padx=5)
        
        self.url_entry = ttk.Entry(top_frame, width=60)
        self.url_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        self.process_btn = ttk.Button(top_frame, text="자막 생성", command=self.start_processing)
        self.process_btn.pack(side=tk.LEFT, padx=5)
        
        # 중간 프레임 (출력 디렉토리 선택)
        dir_frame = ttk.Frame(self.root)
        dir_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(dir_frame, text="출력 폴더:").pack(side=tk.LEFT, padx=5)
        
        self.output_dir_entry = ttk.Entry(dir_frame, width=60)
        self.output_dir_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        self.output_dir_entry.insert(0, os.path.join(os.path.expanduser("~"), "Downloads"))
        
        self.browse_btn = ttk.Button(dir_frame, text="찾아보기", command=self.browse_directory)
        self.browse_btn.pack(side=tk.LEFT, padx=5)
        
        # 옵션 프레임
        options_frame = ttk.LabelFrame(self.root, text="옵션")
        options_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # 언어 선택
        lang_frame = ttk.Frame(options_frame)
        lang_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(lang_frame, text="언어:").pack(side=tk.LEFT, padx=5)
        
        self.language_var = tk.StringVar(value="자동 감지")
        languages = ["자동 감지", "한국어", "영어", "일본어", "중국어"]
        self.language_combo = ttk.Combobox(lang_frame, textvariable=self.language_var, values=languages, width=15)
        self.language_combo.pack(side=tk.LEFT, padx=5)
        
        # 포맷 선택
        format_frame = ttk.Frame(options_frame)
        format_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(format_frame, text="출력 형식:").pack(side=tk.LEFT, padx=5)
        
        self.format_var = tk.StringVar(value="텍스트 (.txt)")
        formats = ["텍스트 (.txt)", "자막 (.srt)"]
        self.format_combo = ttk.Combobox(format_frame, textvariable=self.format_var, values=formats, width=15)
        self.format_combo.pack(side=tk.LEFT, padx=5)
        
        # 모델 로드 버튼
        self.load_model_btn = ttk.Button(options_frame, text="모델 로드", command=self.load_model)
        self.load_model_btn.pack(side=tk.LEFT, padx=5, pady=5)
        
        self.model_status_label = ttk.Label(options_frame, text="모델 상태: 로드되지 않음")
        self.model_status_label.pack(side=tk.LEFT, padx=5, pady=5)
        
        # 로그 및 상태 표시 영역
        log_frame = ttk.LabelFrame(self.root, text="로그")
        log_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.log_text = scrolledtext.ScrolledText(log_frame, wrap=tk.WORD, height=15)
        self.log_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 진행 상태 표시
        self.progress = ttk.Progressbar(self.root, orient=tk.HORIZONTAL, length=100, mode='indeterminate')
        self.progress.pack(fill=tk.X, padx=5, pady=5)
        
        self.status_label = ttk.Label(self.root, text="준비됨")
        self.status_label.pack(pady=5)
    
    def browse_directory(self):
        directory = filedialog.askdirectory()
        if directory:
            self.output_dir_entry.delete(0, tk.END)
            self.output_dir_entry.insert(0, directory)
    
    def log_message(self, message):
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)
    
    def load_model(self):
        if self.model_loaded:
            self.log_message("모델이 이미 로드되어 있습니다.")
            return
        
        # 비동기로 모델 로드
        threading.Thread(target=self._load_model_thread, daemon=True).start()
        
        self.progress.start()
        self.load_model_btn.configure(state="disabled")
        self.status_label.configure(text="모델 로드 중...")
    
    def _load_model_thread(self):
        try:
            self.log_message("Whisper 모델 로드 중...")
            
            # 모델 및 프로세서 불러오기
            model_id = "openai/whisper-large-v3-turbo"
            self.model = AutoModelForSpeechSeq2Seq.from_pretrained(
                model_id,
                torch_dtype=self.torch_dtype,
                low_cpu_mem_usage=True,
                use_safetensors=True
            )
            self.model.to(self.device)
            self.processor = AutoProcessor.from_pretrained(model_id)
            
            # 파이프라인 생성
            self.asr_pipe = pipeline(
                "automatic-speech-recognition",
                model=self.model,
                tokenizer=self.processor.tokenizer,
                feature_extractor=self.processor.feature_extractor,
                torch_dtype=self.torch_dtype,
                device=self.device
            )
            
            self.model_loaded = True
            self.root.after(0, self._update_ui_after_model_load)
            self.log_message("모델 로드 완료!")
            
        except Exception as e:
            self.log_message(f"모델 로드 중 오류 발생: {str(e)}")
            self.root.after(0, self._update_ui_on_error)
    
    def _update_ui_after_model_load(self):
        self.progress.stop()
        self.load_model_btn.configure(state="normal")
        self.model_status_label.configure(text="모델 상태: 로드됨")
        self.status_label.configure(text="준비됨")
    
    def _update_ui_on_error(self):
        self.progress.stop()
        self.load_model_btn.configure(state="normal")
        self.status_label.configure(text="오류 발생")
    
    def start_processing(self):
        if self.is_processing:
            messagebox.showwarning("처리 중", "이미 처리 중입니다. 완료될 때까지 기다려주세요.")
            return
        
        if not self.model_loaded:
            messagebox.showwarning("모델 로드 필요", "먼저 모델을 로드해주세요.")
            return
        
        youtube_url = self.url_entry.get().strip()
        if not youtube_url:
            messagebox.showerror("URL 오류", "YouTube URL을 입력해주세요.")
            return
        
        if not self.is_valid_youtube_url(youtube_url):
            messagebox.showerror("URL 오류", "유효한 YouTube URL이 아닙니다.")
            return
        
        output_dir = self.output_dir_entry.get().strip()
        if not os.path.isdir(output_dir):
            try:
                os.makedirs(output_dir)
            except Exception as e:
                messagebox.showerror("폴더 오류", f"출력 폴더를 만들 수 없습니다: {str(e)}")
                return
        
        # 비동기로 처리 시작
        threading.Thread(target=self._process_video_thread, args=(youtube_url, output_dir), daemon=True).start()
        
        self.is_processing = True
        self.progress.start()
        self.process_btn.configure(state="disabled")
        self.status_label.configure(text="처리 중...")
    
    def is_valid_youtube_url(self, url):
        # YouTube URL 검증
        youtube_regex = (
            r'(https?://)?(www\.)?'
            r'(youtube|youtu|youtube-nocookie)\.(com|be)/'
            r'(watch\?v=|embed/|v/|.+\?v=)?([^&=%\?]{11})')
        
        match = re.match(youtube_regex, url)
        return match is not None
    
    def _process_video_thread(self, youtube_url, output_dir):
        try:
            # YouTube 비디오 정보 가져오기
            self.log_message(f"YouTube 비디오 정보 가져오는 중: {youtube_url}")
            
            # yt-dlp 옵션 설정 (FFmpeg 없이)
            ydl_opts = {
                'format': 'bestaudio/best',
                # FFmpeg 관련 후처리 제거
                'outtmpl': os.path.join(output_dir, '%(title)s.%(ext)s'),
                'quiet': True,
                'no_warnings': True
            }
            
            # 비디오 정보 가져오기
            with yt_dlp.YoutubeDL({'quiet': True, 'no_warnings': True}) as ydl:
                info = ydl.extract_info(youtube_url, download=False)
                video_title = info.get('title', 'video')
                safe_title = ''.join(c for c in video_title if c.isalnum() or c in ' ._-').strip()
                audio_file_path = os.path.join(output_dir, f"{safe_title}.mp3")
                
            self.log_message(f"비디오 제목: {video_title}")
            
            # 오디오 다운로드
            self.log_message("오디오 다운로드 중...")
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([youtube_url])
            
            # 다운로드된 파일 경로 확인
            audio_file_path = os.path.join(output_dir, f"{safe_title}.mp3")
            if not os.path.exists(audio_file_path):
                # mp3로 변환이 안 된 경우 원본 파일 찾기
                for file in os.listdir(output_dir):
                    if file.startswith(safe_title) and os.path.isfile(os.path.join(output_dir, file)):
                        audio_file_path = os.path.join(output_dir, file)
                        break
            
            self.log_message(f"오디오 다운로드 완료: {audio_file_path}")
            
            # 언어 설정
            language = self.language_var.get()
            language_code = None
            forced_decoder_ids = None
            
            if language == "한국어":
                language_code = "ko"
            elif language == "영어":
                language_code = "en"
            elif language == "일본어":
                language_code = "ja"
            elif language == "중국어":
                language_code = "zh"
            
            # 자막 생성
            self.log_message("자막 생성 중...")
            
            transcription_options = {
                "chunk_length_s": 30,
                "batch_size": 16,
                "return_timestamps": True
            }
            
            # Whisper large-v3-turbo는 forced_decoder_ids를 사용합니다
            if language_code and language != "자동 감지":
                # 언어 토큰 ID를 직접 설정하지 않고, 생성 시점에 task와 language 설정
                self.log_message(f"언어 설정: {language_code}")
                transcription_options["generate_kwargs"] = {"task": "transcribe", "language": language_code}
            
            # 파일 확장자 확인 및 처리
            self.log_message(f"오디오 파일 처리 중: {audio_file_path}")
            result = self.asr_pipe(audio_file_path, **transcription_options)
            
            # 결과 저장
            output_format = self.format_var.get()
            if output_format == "텍스트 (.txt)":
                output_file = os.path.join(output_dir, f"{safe_title}.txt")
                with open(output_file, "w", encoding="utf-8") as f:
                    f.write(result["text"])
            else:  # SRT 파일 생성
                output_file = os.path.join(output_dir, f"{safe_title}.srt")
                self._create_srt_file(result, output_file)
            
            self.log_message(f"자막 생성 완료: {output_file}")
            
            # 임시 오디오 파일 삭제
            try:
                os.remove(audio_file_path)
                self.log_message("임시 오디오 파일 삭제 완료")
            except Exception as e:
                self.log_message(f"임시 파일 삭제 중 오류: {str(e)}")
            
            # 완료 메시지
            self.root.after(0, lambda: messagebox.showinfo("완료", f"자막 생성이 완료되었습니다.\n저장 위치: {output_file}"))
            
        except Exception as e:
            self.log_message(f"처리 중 오류 발생: {str(e)}")
            self.root.after(0, lambda: messagebox.showerror("오류", f"처리 중 오류 발생: {str(e)}"))
        
        finally:
            self.is_processing = False
            self.root.after(0, self._update_ui_after_processing)
    
    def _create_srt_file(self, result, output_file):
        srt_content = ""
        chunk_index = 1
        
        if "chunks" in result:
            # 타임스탬프가 있는 경우
            for chunk in result["chunks"]:
                start_time = chunk["timestamp"][0]
                end_time = chunk["timestamp"][1]
                text = chunk["text"]
                
                # SRT 형식으로 포맷팅
                srt_content += f"{chunk_index}\n"
                srt_content += f"{self._format_timestamp(start_time)} --> {self._format_timestamp(end_time)}\n"
                srt_content += f"{text.strip()}\n\n"
                
                chunk_index += 1
        else:
            # 타임스탬프가 없는 경우, 전체 텍스트를 하나의 자막으로
            srt_content += f"{chunk_index}\n"
            srt_content += f"00:00:00,000 --> 00:10:00,000\n"  # 기본 10분 지정
            srt_content += f"{result['text'].strip()}\n"
        
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(srt_content)
    
    def _format_timestamp(self, seconds):
        # 초를 SRT 타임스탬프 형식(HH:MM:SS,mmm)으로 변환
        hours = int(seconds / 3600)
        minutes = int((seconds % 3600) / 60)
        seconds = seconds % 60
        milliseconds = int((seconds - int(seconds)) * 1000)
        
        return f"{hours:02d}:{minutes:02d}:{int(seconds):02d},{milliseconds:03d}"
    
    def _update_ui_after_processing(self):
        self.progress.stop()
        self.process_btn.configure(state="normal")
        self.status_label.configure(text="완료")

def main():
    root = tk.Tk()
    app = YouTubeTranscriptionApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()