#!/usr/bin/env python3
"""
Ollama 채팅 클래스
Ollama API를 사용하여 대화를 처리하는 클래스를 정의합니다.
"""
import sys
from typing import Dict, Any, List, Optional, Callable
from pathlib import Path

try:
    import ollama
    from ollama import chat
except ImportError:
    print("⚠️  'ollama' 패키지가 설치되어 있지 않습니다.")
    print("pip install ollama 명령으로 설치하세요.")
    sys.exit(1)

from chat_memory import ChatMemory


class OllamaChat:
    """Ollama 모델과 대화하는 클래스"""
    
    def __init__(
        self, 
        model: Optional[str] = None,
        chat_log_dir: str = "chat_log",
        max_messages: int = 20,
        auto_summary: bool = True,
        temperature: float = 0.7,
        params: Optional[Dict[str, Any]] = None
    ):
        """
        초기화
        
        Args:
            model (str, optional): 사용할 모델 이름 (None인 경우 선택 메뉴 표시)
            chat_log_dir (str): 대화 저장 디렉토리
            max_messages (int): 자동 요약 전 최대 메시지 수
            auto_summary (bool): 자동 요약 활성화 여부
            temperature (float): 모델 temperature 값
            params (Dict[str, Any], optional): 추가 모델 매개변수
        """
        # 메모리 관리자 초기화 (먼저 초기화하여 폴더 생성)
        self.memory = ChatMemory(
            chat_log_dir=chat_log_dir,
            max_messages=max_messages,
            auto_summary=auto_summary
        )
        
        # 모델 선택
        self.model = model if model else self._pick_model()
        
        # 모델 매개변수 초기화
        self.params = params or {
            "temperature": temperature,
            "top_p": 0.9,
            "top_k": 40,
        }
        
    def _pick_model(self) -> str:
        """
        설치된 모델 목록을 보여주고 사용자가 선택하게 함
        
        Returns:
            str: 선택된 모델 이름
        """
        try:
            # 설치된 모델 목록 가져오기
            models_resp = ollama.list()
            models = models_resp.models

            if not models:
                print("⚠️  로컬에 모델이 없습니다. 먼저 `ollama pull <model>` 로 가져오세요.")
                sys.exit(1)

            # 목록 출력
            print("=== 사용 가능한 모델 ===")
            for i, m in enumerate(models):
                name = m.model
                
                # size 처리 (버전에 따라 다를 수 있음)
                size_str = "알 수 없음"
                if hasattr(m, "size"):
                    if hasattr(m.size, "human_readable") and callable(m.size.human_readable):
                        size_str = m.size.human_readable()
                    elif isinstance(m.size, (int, float)):
                        size_str = f"{m.size / (1024**3):.1f} GB"
                    elif m.size:
                        size_str = str(m.size)
                
                # 수정 시간 처리
                mod_time = "알 수 없음"
                if hasattr(m, "modified_at") and m.modified_at:
                    if hasattr(m.modified_at, "strftime"):
                        mod_time = m.modified_at.strftime("%Y-%m-%d %H:%M")
                    else:
                        mod_time = str(m.modified_at)
                
                print(f"[{i}] {name:20}  {size_str:>8}  (수정일: {mod_time})")

            # 번호 입력
            while True:
                sel = input("\n번호를 선택하세요 ▶ ")
                try:
                    idx = int(sel)
                    if 0 <= idx < len(models):
                        return models[idx].model
                except ValueError:
                    pass
                print("잘못된 입력입니다. 다시 선택하세요.")
        
        except Exception as e:
            print(f"⚠️  모델 목록을 가져오는 중 오류가 발생했습니다: {e}")
            sys.exit(1)
    
    def update_parameters(self) -> None:
        """모델 매개변수 업데이트"""
        print("\n=== 현재 매개변수 ===")
        for key, value in self.params.items():
            print(f"{key}: {value}")
        
        print("\n변경할 매개변수를 'key=value' 형식으로 입력하세요.")
        print("예: temperature=0.8 top_p=0.9")
        print("그냥 Enter 키를 누르면 변경 없이 돌아갑니다.")
        
        user_input = input("\n입력 ▶ ")
        if not user_input.strip():
            return
        
        # 입력 파싱
        try:
            for pair in user_input.split():
                if "=" in pair:
                    key, value = pair.split("=", 1)
                    key = key.strip()
                    
                    # 값 타입 변환 시도
                    try:
                        if value.lower() == "true":
                            value = True
                        elif value.lower() == "false":
                            value = False
                        elif "." in value:
                            value = float(value)
                        else:
                            value = int(value)
                    except ValueError:
                        # 변환 실패시 문자열로 유지
                        pass
                    
                    self.params[key] = value
                    print(f"✅ {key} = {value} 설정됨")
        except Exception as e:
            print(f"⚠️  매개변수 업데이트 중 오류 발생: {e}")
    
    def process_command(self, command: str) -> bool:
        """
        명령어 처리
        
        Args:
            command (str): 명령어
            
        Returns:
            bool: 대화 계속 여부 (True: 계속, False: 종료)
        """
        cmd = command.lower().strip()
        
        if cmd == "/exit":
            print("👋 종료합니다.")
            return False
            
        elif cmd == "/help":
            self._show_help()
            
        elif cmd == "/save":
            if not self.memory.get_messages():
                print("⚠️ 저장할 대화 내용이 없습니다.")
                return True
                
            save_path = input("저장할 파일명 (기본: 자동 생성): ")
            try:
                filepath = self.memory.save_conversation(save_path if save_path else None)
                print(f"✅ 대화 내용이 저장되었습니다: {filepath}")
            except Exception as e:
                print(f"⚠️ 대화 저장 중 오류가 발생했습니다: {e}")
            
        elif cmd == "/params":
            self.update_parameters()
            
        elif cmd == "/summary":
            if not self.memory.get_messages():
                print("⚠️ 요약할 대화 내용이 없습니다.")
                return True
                
            # 현재 메시지 수 표시
            print(f"현재 메시지 수: {self.memory.count_messages()}개")
            keep_recent = 3  # 기본값
            
            try:
                keep_input = input("유지할 최근 메시지 수 (기본: 3): ")
                if keep_input.strip():
                    keep_recent = max(0, int(keep_input))
            except ValueError:
                print("잘못된 입력, 기본값 3을 사용합니다.")
            
            # 요약 실행
            success = self.memory.summarize_conversation(self.model, keep_recent, ollama.chat)
            
            # 메모리 업데이트 결과 출력
            if success:
                print(f"✅ 메모리가 업데이트되었습니다. 현재 메시지 수: {self.memory.count_messages()}개")
                messages = self.memory.get_messages()
                if messages and messages[0]["role"] == "system":
                    print(f"📝 요약: {messages[0]['content']}")
            
        elif cmd == "/show mem" or cmd == "/show_mem":
            self.memory.display_memory()
            
        elif cmd == "/load":
            # 저장된 대화 목록 표시 및 선택
            selected_file = self.memory.display_saved_chats()
            if selected_file:
                # 현재 대화 저장 여부 확인
                if self.memory.get_messages():
                    save_yn = input("현재 대화를 저장하시겠습니까? (y/n): ")
                    if save_yn.lower() in ["y", "yes", "예"]:
                        try:
                            filepath = self.memory.save_conversation()
                            print(f"✅ 현재 대화가 저장되었습니다: {filepath}")
                        except Exception as e:
                            print(f"⚠️ 대화 저장 중 오류가 발생했습니다: {e}")
                
                # 대화 불러오기
                success = self.memory.load_conversation(selected_file)
                if success:
                    print(f"✅ 대화를 불러왔습니다. 메시지 수: {self.memory.count_messages()}개")
                    # 불러온 대화 간략히 표시
                    self.memory.display_memory()
                else:
                    print("⚠️ 대화를 불러오지 못했습니다.")
        elif cmd.startswith("/prompt"):
            # 명령어 형식: /prompt [모드] 파일명
            # 모드: -a (추가), -r (교체), -u (업데이트)
            parts = cmd.split(maxsplit=2)
            
            mode = "append"  # 기본 모드
            filename = ""
            
            if len(parts) > 1:
                if parts[1].startswith("-"):
                    # 모드 지정됨
                    mode_flag = parts[1].lower()
                    if mode_flag == "-r":
                        mode = "replace"
                    elif mode_flag == "-u":
                        mode = "update"
                    elif mode_flag == "-a":
                        mode = "append"
                    else:
                        print(f"⚠️ 알 수 없는 모드: {mode_flag}")
                        print("사용 가능한 모드: -a (추가), -r (교체), -u (업데이트)")
                        print("기본 모드 '추가'로 진행합니다.")
                    
                    if len(parts) > 2:
                        filename = parts[2].strip()
                else:
                    # 모드 지정 없음, 두 번째 인자는 파일명
                    filename = parts[1].strip()
            
            if not filename:
                # 프롬프트 파일 입력 받기
                mode_desc = "추가" if mode == "append" else "교체" if mode == "replace" else "업데이트"
                filename = input(f"프롬프트 파일 경로 (모드: {mode_desc}): ")
            
            if filename.strip():
                self.memory.load_prompt_from_file(filename, mode=mode)
            else:
                print("⚠️ 파일 경로가 입력되지 않았습니다.")
                print("프롬프트 적용 모드:")
                print("  -a: 기존 메시지를 모두 유지하고 프롬프트 추가 (기본값)")
                print("  -r: 기존 시스템 메시지를 모두 제거하고 프롬프트로 교체") 
                print("  -u: 기존 시스템 메시지가 있으면 내용 업데이트, 없으면 추가")
        else:
            print(f"⚠️ 알 수 없는 명령어: {cmd}")
            print("명령어 목록을 보려면 /help를 입력하세요.")
            
        return True
        
    def _show_help(self) -> None:
        """도움말 표시"""
        print("\n=== 사용 가능한 명령어 ===")
        print("/help     - 이 도움말 표시")
        print("/exit     - 대화 종료")
        print("/save     - 대화 내용 저장")
        print("/load     - 저장된 대화 불러오기")
        print("/params   - 현재 모델 매개변수 확인/변경")
        print("/summary  - 지금까지의 대화 요약 및 메모리 정리")
        print("/show mem - 현재 메모리에 저장된 대화 내용 표시")
        print("==================\n")
    
    def chat_loop(self) -> None:
        """대화 루프 실행"""
        print(f"\n✅ '{self.model}' 모델로 대화를 시작합니다.")
        print(f"✅ 기본 temperature: {self.params.get('temperature', 0.7)}")
        if self.memory.auto_summary:
            print(f"✅ 자동 요약: 메시지 {self.memory.max_messages}개 초과시")
        else:
            print("❌ 자동 요약 비활성화됨")
        print("✅ 명령어 도움말은 /help 를 입력하세요.\n")
        
        try:
            while True:
                try:
                    if self.memory.count_messages() > 0:
                        # 이전 대화가 있는 경우 명령 프롬프트에 번호 표시
                        msg_count = self.memory.count_messages()
                        user_input = input(f"\033[1;32m[{msg_count}] You:\033[0m ")
                    else:
                        user_input = input("\033[1;32mYou:\033[0m ")
                except (EOFError, KeyboardInterrupt):
                    print("\n👋 종료합니다.")
                    break
                
                # 빈 입력이면 무시
                if not user_input.strip():
                    continue
                    
                # 특수 명령어 처리
                if user_input.startswith("/"):
                    if not self.process_command(user_input):
                        break
                    continue
                    
                # 대화 기록에 사용자 입력 추가
                self.memory.add_message("user", user_input)
                
                try:
                    # Ollama에 요청
                    response = chat(
                        model=self.model,
                        messages=self.memory.get_messages(),
                        options=self.params
                    )
                    
                    assistant_reply = response.message.content
                    print(f"\033[1;36mAI:\033[0m {assistant_reply}")
                    
                    # 대화 기록에 모델 응답 추가
                    self.memory.add_message("assistant", assistant_reply)
                    
                    # 자동 요약 체크
                    self.memory.check_auto_summary(self.model, keep_recent=5)
                    
                except Exception as e:
                    print(f"⚠️ 모델 응답 중 오류 발생: {e}")
                    # 오류 발생 시 마지막 사용자 메시지는 기록에서 제거
                    messages = self.memory.get_messages()
                    if messages and messages[-1]["role"] == "user":
                        messages.pop()
                        self.memory.set_messages(messages)
                        
        finally:
            # 종료 시 자동 저장 여부 확인
            if self.memory.count_messages() > 0:
                save_yn = input("\n대화 내용을 저장하시겠습니까? (y/n): ")
                if save_yn.lower() in ["y", "yes", "예"]:
                    save_path = input("저장할 파일명 (기본: 자동 생성): ")
                    try:
                        filepath = self.memory.save_conversation(save_path if save_path else None)
                        print(f"✅ 대화 내용이 저장되었습니다: {filepath}")
                    except Exception as e:
                        print(f"⚠️ 대화 저장 중 오류가 발생했습니다: {e}")