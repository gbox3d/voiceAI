# YouTube 자막 생성기 개선 TODO 리스트

## 우선 순위 높음 (안정성 개선)

- [ ] **스레드 안전성 개선**
  - `_process_audio_in_chunks` 메소드 내 UI 업데이트 수정
  - `self.log_message()` 호출을 메인 스레드로 이동
  - `self.root.update()` 호출을 메인 스레드로 이동
  ```python
  # 변경 전
  self.log_message(f"청크 {chunk_index}/{total_chunks} 처리 중...")
  self.root.update()
  
  # 변경 후
  self.root.after(0, lambda: self.log_message(f"청크 {chunk_index}/{total_chunks} 처리 중..."))
  self.root.after(0, self.root.update)
  ```

- [ ] **자막 파일 자동 저장 기능 추가**
  - 생성된 자막을 로그에 표시할 뿐만 아니라 파일로도 저장
  ```python
  output_path = os.path.join(output_dir, f"{safe_title}.{'txt' if output_format == '텍스트 (.txt)' else 'srt'}")
  with open(output_path, 'w', encoding='utf-8') as f:
      f.write(complete_text)
  self.log_message(f"자막 파일 저장 완료: {output_path}")
  ```

- [ ] **청크 수 계산 수정**
  - 정확한 청크 수 계산을 위해 `math.ceil` 사용
  ```python
  import math
  # 변경 전
  total_chunks = (length_ms // 30000) + 1
  
  # 변경 후
  total_chunks = math.ceil(length_ms / 30000)
  ```

## 우선 순위 중간 (기능 개선)

- [ ] **진행 상태 표시 개선**
  - indeterminate 모드 대신 determinate 모드로 변경하여 실제 진행률 표시
  ```python
  # 초기화 시
  self.progress["mode"] = "determinate"
  self.progress["value"] = 0
  self.progress["maximum"] = 100
  
  # 청크 처리 시
  progress_value = (chunk_index / total_chunks) * 100
  self.root.after(0, lambda v=progress_value: self.progress.configure(value=v))
  ```

- [ ] **메모리 관리 개선**
  - 사용 후 큰 객체 명시적 해제
  ```python
  # 청크 처리 후
  del audio_chunk
  # 전체 처리 후
  del audio
  ```

- [ ] **설정 저장 기능 추가**
  - 언어, 출력 형식, 출력 디렉토리 등의 설정을 파일에 저장
  ```python
  def save_settings(self):
      settings = {
          "language": self.language_var.get(),
          "output_format": self.format_var.get(),
          "output_dir": self.output_dir_entry.get()
      }
      with open("settings.json", "w") as f:
          json.dump(settings, f)
  
  def load_settings(self):
      try:
          with open("settings.json", "r") as f:
              settings = json.load(f)
              self.language_var.set(settings.get("language", "자동 감지"))
              self.format_var.set(settings.get("output_format", "텍스트 (.txt)"))
              self.output_dir_entry.delete(0, tk.END)
              self.output_dir_entry.insert(0, settings.get("output_dir", os.path.join(os.path.expanduser("~"), "Downloads")))
      except:
          pass
  ```

## 우선 순위 낮음 (품질 향상)

- [ ] **변수 이름 개선**
  - `_format_timestamp` 함수 내 변수명 수정
  ```python
  def _format_timestamp(self, seconds):
      hours = int(seconds / 3600)
      minutes = int((seconds % 3600) / 60)
      remain_sec = seconds % 60
      milliseconds = int((remain_sec - int(remain_sec)) * 1000)
      
      return f"{hours:02d}:{minutes:02d}:{int(remain_sec):02d},{milliseconds:03d}"
  ```

- [ ] **오류 메시지 명확화**
  - 사용자가 이해하기 쉬운 오류 메시지 제공
  ```python
  try:
      # 코드...
  except FileNotFoundError:
      self.log_message("파일을 찾을 수 없습니다.")
  except PermissionError:
      self.log_message("파일에 접근할 권한이 없습니다.")
  except Exception as e:
      self.log_message(f"처리 중 오류 발생: {str(e)}")
  ```

- [ ] **Whisper 경고 처리**
  - Whisper 경고 메시지 필터링 또는 로깅 수준 조정
  ```python
  import logging
  # Whisper 라이브러리 로깅 레벨 조정
  logging.getLogger("transformers").setLevel(logging.ERROR)
  ```

- [ ] **코드 주석 및 문서화**
  - 주요 함수에 docstring 추가
  ```python
  def _process_audio_in_chunks(self, audio_file_path, language_code=None):
      """
      오디오 파일을 30초 단위 청크로 분할하여 처리합니다.
      
      Args:
          audio_file_path (str): 처리할 오디오 파일 경로
          language_code (str, optional): 언어 코드 (예: 'ko', 'en'). None이면 자동 감지
          
      Returns:
          str: 생성된 자막 텍스트 (텍스트 또는 SRT 형식)
          
      Raises:
          Exception: 오디오 처리 중 발생하는 모든 예외
      """
      # 함수 내용...
  ```

## 향후 고려 사항

- [ ] **병렬 처리 구현**
  - 청크별 병렬 처리로 속도 향상 (복잡도 높음)
- [ ] **WhisperTimeStampLogitsProcessor 적용 검토**
  - 타임스탬프 경고 해결을 위한 로직 추가
- [ ] **사용자 인터페이스 개선**
  - 테마 옵션 추가
  - 언어 선택 확장
  - 자막 미리보기 기능