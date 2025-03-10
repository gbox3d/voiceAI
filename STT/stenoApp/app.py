import os
import sys
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import torch
from transformers import AutoModelForSpeechSeq2Seq, AutoProcessor, pipeline
import yt_dlp  # pip install yt-dlp
import urllib.request
import re
import tempfile
import shutil
from pydub import AudioSegment # pip install pydub
import time

class YouTubeTranscriptionApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Stone Steno 자막생성기 v0.1")
        self.root.geometry("800x600")
        self.root.configure(padx=20, pady=20)
        
        # 디바이스 설정
        self.device = "cuda:0" if torch.cuda.is_available() else "cpu"
        self.torch_dtype = torch.float16 if torch.cuda.is_available() else torch.float32
        
        # 상태 변수
        self.model_loaded = False
        self.is_processing = False
        
        # 임시 디렉토리 생성
        self.temp_dir = tempfile.mkdtemp()
        
        # 종료 시 임시 파일 정리
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # UI 구성
        self.create_widgets()
        
    def create_widgets(self):
        # 상단 프레임 (YouTube URL 입력)
        top_frame = ttk.Frame(self.root)
        top_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(top_frame, text="YouTube URL:").pack(side=tk.LEFT, padx=5)
        
        # 기본값 https://youtu.be/UsxcCSA4jA4?si=VwDbj7UzDPrNOfE1
        self.url_entry = ttk.Entry(top_frame, width=60)
        self.url_entry.insert(0, "https://youtu.be/UsxcCSA4jA4?si=VwDbj7UzDPrNOfE1")
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
        log_frame = ttk.LabelFrame(self.root, text="로그 및 자막 결과")
        log_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.log_text = scrolledtext.ScrolledText(log_frame, wrap=tk.WORD, height=15)
        self.log_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 로그 텍스트 영역의 폰트 설정
        font = ('Consolas', 10)
        self.log_text.configure(font=font)
        
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
    
    def _process_audio_in_chunks(self, audio_file_path, language_code=None):
        """오디오 파일을 30초 청크로 직접 분할하여 처리"""
        self.root.after(0, lambda: self.log_message("오디오 파일을 30초 단위로 분할하여 처리 중..."))
        
        try:
            # 오디오 로드
            audio = AudioSegment.from_file(audio_file_path)
            length_ms = len(audio)
            
            # 진행 정보
            import math
            total_chunks = math.ceil(length_ms / 30000)
            self.root.after(0, lambda: self.log_message(f"총 오디오 길이: {length_ms/1000:.1f}초, 청크 수: {total_chunks}개"))
            
            # 출력 형식
            output_format = self.format_var.get()
            
            # 모든 텍스트를 저장할 변수
            all_text = ""
            all_chunks = []
            
            # 30초(30000ms) 단위로 처리
            chunk_start = 0
            chunk_index = 1
            
            while chunk_start < length_ms:
                # 30초 단위로 잘라내기 (겹침 없음)
                chunk_end = min(chunk_start + 30000, length_ms)
                audio_chunk = audio[chunk_start:chunk_end]
                
                # 임시 파일에 청크 저장
                temp_path = os.path.join(self.temp_dir, f"chunk_{chunk_index}.wav")
                audio_chunk.export(temp_path, format="wav")
                
                # 진행 상황 표시
                self.root.after(0, lambda start=chunk_start, end=chunk_end, idx=chunk_index: 
                    self.log_message(f"청크 {idx}/{total_chunks} 처리 중... ({start/1000:.1f}s ~ {end/1000:.1f}s)"))
                
                # 진행 상태바 업데이트
                progress_value = (chunk_index / total_chunks) * 100
                self.root.after(0, lambda v=progress_value: self.progress.configure(value=v))
                
                # 청크 처리 옵션
                chunk_options = {
                    "batch_size": 16,
                    "return_timestamps": True
                }
                
                # 언어 설정 적용
                if language_code:
                    chunk_options["generate_kwargs"] = {"task": "transcribe", "language": language_code}
                
                # 청크 처리 (이 부분이 blocking됨)
                chunk_result = self.asr_pipe(temp_path, **chunk_options)
                
                # 청크 결과 처리
                if output_format == "텍스트 (.txt)":
                    chunk_text = chunk_result["text"].strip()
                    self.root.after(0, lambda idx=chunk_index, text=chunk_text: 
                        self.log_message(f"[{idx}] {text}"))
                    all_text += " " + chunk_text
                else:  # SRT
                    # 시간 오프셋 적용 (각 청크의 시작 시간 기준)
                    base_time = chunk_start / 1000  # ms -> s
                    
                    if "chunks" in chunk_result:
                        for i, segment in enumerate(chunk_result["chunks"]):
                            # 시간 조정 (청크 내 상대 시간 -> 전체 오디오 절대 시간)
                            start_time = base_time + segment["timestamp"][0]
                            end_time = base_time + segment["timestamp"][1]
                            
                            # SRT 항목 생성
                            srt_index = len(all_chunks) + 1
                            srt_entry = f"{srt_index}\n"
                            srt_entry += f"{self._format_timestamp(start_time)} --> {self._format_timestamp(end_time)}\n"
                            srt_entry += f"{segment['text'].strip()}\n\n"
                            
                            self.root.after(0, lambda entry=srt_entry: self.log_message(entry))
                            all_chunks.append({
                                "index": srt_index,
                                "start": start_time,
                                "end": end_time,
                                "text": segment['text'].strip()
                            })
                    else:
                        # 청크에 타임스탬프가 없는 경우 청크 전체에 대한 시간 설정
                        end_time = base_time + (chunk_end - chunk_start) / 1000
                        srt_index = len(all_chunks) + 1
                        srt_entry = f"{srt_index}\n"
                        srt_entry += f"{self._format_timestamp(base_time)} --> {self._format_timestamp(end_time)}\n"
                        srt_entry += f"{chunk_result['text'].strip()}\n\n"
                        
                        self.root.after(0, lambda entry=srt_entry: self.log_message(entry))
                        all_chunks.append({
                            "index": srt_index,
                            "start": base_time,
                            "end": end_time,
                            "text": chunk_result['text'].strip()
                        })
                
                # 임시 파일 삭제
                try:
                    os.remove(temp_path)
                except:
                    pass
                    
                # 메모리 관리 개선
                del audio_chunk
                
                # UI 업데이트 (중요!)
                self.root.after(0, self.root.update)
                
                # 다음 청크로
                chunk_start = chunk_end
                chunk_index += 1
            
            # 처리 완료 후 전체 결과 정리
            self.root.after(0, lambda: self.log_message("\n===== 전체 자막 텍스트 ====="))
            
            # 메모리 관리 - 큰 객체 해제
            del audio
            
            if output_format == "텍스트 (.txt)":
                final_text = all_text.strip()
                self.root.after(0, lambda t=final_text: self.log_message(t))
                return final_text
            else:  # SRT 전체 재구성
                combined_srt = ""
                for chunk in sorted(all_chunks, key=lambda x: x["start"]):
                    combined_srt += f"{chunk['index']}\n"
                    combined_srt += f"{self._format_timestamp(chunk['start'])} --> {self._format_timestamp(chunk['end'])}\n"
                    combined_srt += f"{chunk['text']}\n\n"
                self.root.after(0, lambda s=combined_srt: self.log_message(s))
                return combined_srt
            
        except Exception as e:
            self.root.after(0, lambda e=str(e): self.log_message(f"청크 처리 중 오류 발생: {e}"))
            raise

    def _process_video_thread(self, youtube_url, output_dir):
        try:
            # YouTube 비디오 정보 가져오기
            self.root.after(0, lambda url=youtube_url: self.log_message(f"YouTube 비디오 정보 가져오는 중: {url}"))
            
            # yt-dlp 옵션 설정 (다운로드 파일 경로를 명확히 추적)
            ydl_opts = {
                'format': 'bestaudio/best',
                'outtmpl': os.path.join(output_dir, '%(title)s.%(ext)s'),
                'quiet': True,
                'no_warnings': True,
                'noplaylist': True,
                'postprocessor_args': []  # FFmpeg 관련 후처리 제거
            }
            
            # 비디오 정보 가져오기
            with yt_dlp.YoutubeDL({'quiet': True, 'no_warnings': True}) as ydl:
                info = ydl.extract_info(youtube_url, download=False)
                video_title = info.get('title', 'video')
                safe_title = ''.join(c for c in video_title if c.isalnum() or c in ' ._-').strip()
                audio_file_path = os.path.join(output_dir, f"{safe_title}.mp3")
                
            self.root.after(0, lambda title=video_title: self.log_message(f"비디오 제목: {title}"))
            
            # 오디오 다운로드 및 파일 경로 직접 추적
            self.root.after(0, lambda: self.log_message("오디오 다운로드 중..."))
            
            # 다운로드 전 디렉토리 내용 기록
            before_files = set(os.path.join(output_dir, f) for f in os.listdir(output_dir))
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(youtube_url, download=True)
                
            # 다운로드 후 디렉토리 내용 확인
            after_files = set(os.path.join(output_dir, f) for f in os.listdir(output_dir))
            new_files = after_files - before_files
            
            if new_files:
                # 새로 추가된 파일 중 가장 큰 파일을 선택 (보통 오디오 파일이 가장 큼)
                audio_file_path = max(new_files, key=os.path.getsize)
                self.root.after(0, lambda path=os.path.basename(audio_file_path): 
                    self.log_message(f"다운로드된 파일: {path}"))
            else:
                # info에서 파일명 직접 찾기 시도
                if 'requested_downloads' in info:
                    for download in info['requested_downloads']:
                        if 'filepath' in download:
                            audio_file_path = download['filepath']
                            self.root.after(0, lambda path=os.path.basename(audio_file_path): 
                                self.log_message(f"다운로드된 파일: {path}"))
                            break
            
            self.root.after(0, lambda path=audio_file_path: self.log_message(f"오디오 다운로드 완료: {path}"))
            
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
            self.root.after(0, lambda: self.log_message("자막 생성 중..."))
            
            transcription_options = {
                "chunk_length_s": 30,
                "batch_size": 16,
                "return_timestamps": True
            }
            
            # Whisper large-v3-turbo는 forced_decoder_ids를 사용합니다
            if language_code and language != "자동 감지":
                # 언어 토큰 ID를 직접 설정하지 않고, 생성 시점에 task와 language 설정
                self.root.after(0, lambda code=language_code: self.log_message(f"언어 설정: {code}"))
                transcription_options["generate_kwargs"] = {"task": "transcribe", "language": language_code}
            
            # 자막 생성 - 30초 단위로 직접 분할하여 처리
            self.root.after(0, lambda: self.log_message("자막 생성 중..."))
            
            # 언어 코드 전달하여 직접 분할 처리 함수 호출
            complete_text = self._process_audio_in_chunks(audio_file_path, language_code)
            
            self.root.after(0, lambda: self.log_message("\n===== 자막 생성 완료 ====="))
            
            # 자막 파일 자동 저장
            output_ext = "txt" if self.format_var.get() == "텍스트 (.txt)" else "srt"
            output_path = os.path.join(output_dir, f"{safe_title}.{output_ext}")
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(complete_text)
            self.root.after(0, lambda path=output_path: self.log_message(f"자막 파일 저장 완료: {path}"))
            
            # 임시 오디오 파일 삭제
            try:
                os.remove(audio_file_path)
                self.root.after(0, lambda: self.log_message("임시 오디오 파일 삭제 완료"))
            except Exception as e:
                self.root.after(0, lambda e=str(e): self.log_message(f"임시 파일 삭제 중 오류: {e}"))
            
            # 완료 메시지
            self.root.after(0, lambda: messagebox.showinfo("완료", "자막 생성이 완료되었습니다!"))
            
        except Exception as e:
            self.root.after(0, lambda e=str(e): self.log_message(f"처리 중 오류 발생: {e}"))
            self.root.after(0, lambda e=str(e): messagebox.showerror("오류", f"처리 중 오류 발생: {e}"))
        
        finally:
            self.is_processing = False
            self.root.after(0, self._update_ui_after_processing)
    
    def _generate_srt_content(self, result):
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
        
        return srt_content
    
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
    
    def on_closing(self):
        """프로그램 종료 시 임시 파일 정리"""
        try:
            shutil.rmtree(self.temp_dir)
        except:
            pass
        self.root.destroy()

def main():
    root = tk.Tk()
    app = YouTubeTranscriptionApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()