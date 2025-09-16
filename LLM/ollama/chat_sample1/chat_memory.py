#!/usr/bin/env python3
"""
Ollama 채팅 메모리 관리 모듈
대화 내용의 저장, 불러오기, 요약 및 메모리 관리를 담당합니다.
"""
import os
import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple


class ChatMemory:
    """대화 메모리 관리 클래스"""
    
    def __init__(self, chat_log_dir: str = "chat_log", max_messages: int = 20, auto_summary: bool = True):
        """
        초기화
        
        Args:
            chat_log_dir (str): 대화 저장 디렉토리
            max_messages (int): 자동 요약 전 최대 메시지 수
            auto_summary (bool): 자동 요약 활성화 여부
        """
        self.chat_log_dir = Path(chat_log_dir)
        self.max_messages = max_messages
        self.auto_summary = auto_summary
        self.messages: List[Dict[str, str]] = []
        
        # 저장 디렉토리 생성
        self.chat_log_dir.mkdir(exist_ok=True)
    
    # 기본 메시지 관리 메서드
    def add_message(self, role: str, content: str) -> None:
        """
        메시지 추가
        
        Args:
            role (str): 메시지 역할 ('user', 'assistant', 'system')
            content (str): 메시지 내용
        """
        self.messages.append({"role": role, "content": content})
    
    def get_messages(self) -> List[Dict[str, str]]:
        """현재 메시지 목록 반환"""
        return self.messages
    
    def set_messages(self, messages: List[Dict[str, str]]) -> None:
        """메시지 목록 설정"""
        self.messages = messages
    
    def clear_messages(self) -> None:
        """메시지 목록 초기화"""
        self.messages = []
    
    def count_messages(self) -> int:
        """메시지 수 반환"""
        return len(self.messages)
    
    # 메모리 표시 메서드
    def display_memory(self) -> None:
        """현재 메모리에 저장된 대화 내용 표시"""
        if not self.messages:
            print("⚠️ 메모리에 저장된 대화 내용이 없습니다.")
            return
        
        print("\n=== 현재 메모리 내용 (전체 메시지 수: {}) ===".format(len(self.messages)))
        
        for i, msg in enumerate(self.messages):
            role = msg["role"]
            
            # 역할에 따라 다른 색상과 표시
            if role == "system":
                role_display = "\033[1;33m시스템\033[0m"  # 노란색
                # 요약 내용은 너무 길면 축약
                content = msg["content"]
                if len(content) > 100:
                    content = content[:97] + "..."
            elif role == "user":
                role_display = "\033[1;32m사용자\033[0m"  # 녹색
            elif role == "assistant":
                role_display = "\033[1;36mAI    \033[0m"  # 청록색
            else:
                role_display = "\033[1;37m{}    \033[0m".format(role)  # 기본 회색
            
            # 메시지 내용 (너무 길면 축약)
            content = msg["content"]
            if len(content) > 60 and role != "system":  # 시스템 메시지는 이미 처리됨
                content = content[:57] + "..."
            
            # 메시지 번호와 함께 출력
            print(f"[{i:2d}] {role_display}: {content}")
        
        print("=" * 50)
        
    # 요약 관련 메서드
    def check_auto_summary(self, model_name: str, keep_recent: int = 5) -> bool:
        """
        자동 요약 조건 확인 및 요약 수행
        
        Args:
            model_name (str): 요약에 사용할 모델 이름
            keep_recent (int): 유지할 최근 메시지 수
            
        Returns:
            bool: 요약 수행 여부
        """
        if not self.auto_summary:
            return False
            
        if len(self.messages) > self.max_messages:
            print(f"\n🔄 메시지가 {self.max_messages}개를 초과했습니다. 자동 요약을 진행합니다...")
            self.summarize_conversation(model_name, keep_recent)
            return True
        
        return False
    
    def summarize_conversation(self, model_name: str, keep_recent: int = 5, ollama_chat_func=None) -> bool:
        """
        대화 내용을 요약하고 메모리를 정리
        
        Args:
            model_name (str): 요약에 사용할 모델 이름
            keep_recent (int): 유지할 최근 메시지 수
            ollama_chat_func: Ollama chat 함수 (함수 의존성 주입)
            
        Returns:
            bool: 요약 성공 여부
        """
        if len(self.messages) <= keep_recent + 1:  # 요약할 만큼 메시지가 없으면 그대로 반환
            return False

        # 요약할 메시지들 (최근 keep_recent 개는 제외)
        messages_to_summarize = self.messages[:-keep_recent] if keep_recent > 0 else self.messages
        
        # 요약 내용 구성
        conversation_text = ""
        for msg in messages_to_summarize:
            role = "사용자" if msg["role"] == "user" else "AI"
            conversation_text += f"{role}: {msg['content']}\n\n"
        
        # 요약 프롬프트 작성
        summary_prompt = f"""다음은 사용자와 AI 사이의 대화입니다. 
이 대화의 핵심 내용을 3-5문장으로 요약해주세요. 
중요한 정보, 결정사항, 질문과 답변을 포함해주세요.

=== 대화 내용 ===
{conversation_text}

=== 요약 ==="""
        
        try:
            print("\n🔄 대화 내용을 요약하는 중...")
            
            # 요약 요청
            import ollama
            if ollama_chat_func:
                # 주입된 함수 사용
                response = ollama_chat_func(
                    model=model_name,
                    messages=[{"role": "user", "content": summary_prompt}],
                    options={"temperature": 0.3}  # 요약은 낮은 temperature로
                )
            else:
                # 기본 ollama 사용
                response = ollama.chat(
                    model=model_name,
                    messages=[{"role": "user", "content": summary_prompt}],
                    options={"temperature": 0.3}
                )
            
            summary = response.message.content
            print(f"✅ 요약 완료: {len(messages_to_summarize)}개 메시지 → 요약")
            
            # 새 메시지 목록 구성: 시스템 메시지 + 최근 메시지들
            new_messages = [
                {"role": "system", "content": f"이전 대화 요약: {summary}"}
            ]
            
            # 최근 메시지 추가
            if keep_recent > 0:
                new_messages.extend(self.messages[-keep_recent:])
            
            # 메시지 업데이트
            self.messages = new_messages
            
            return True
            
        except Exception as e:
            print(f"⚠️ 대화 요약 중 오류 발생: {e}")
            print("⚠️ 요약을 건너뛰고 원래 메시지를 유지합니다.")
            return False
    
    def apply_prompt(self, prompt_text: str, mode: str = "append") -> None:
        """
        프롬프트를 시스템 메시지로 적용
        
        Args:
            prompt_text (str): 적용할 프롬프트 텍스트
            mode (str): 적용 모드 
                - "append": 기존 메시지 유지하고 맨 앞에 추가 (기본값)
                - "replace": 기존 시스템 메시지 교체
                - "update": 기존 시스템 메시지 있으면 내용 업데이트, 없으면 추가
        """
        if mode == "replace":
            # 기존 시스템 메시지 제거 후 새로 추가
            self.messages = [msg for msg in self.messages if msg["role"] != "system"]
            self.messages.insert(0, {"role": "system", "content": prompt_text})
            print(f"\n✅ 프롬프트로 시스템 메시지가 교체되었습니다. (길이: {len(prompt_text)} 글자)")
        
        elif mode == "update":
            # 기존 시스템 메시지 있으면 업데이트, 없으면 추가
            system_msg_exists = False
            for msg in self.messages:
                if msg["role"] == "system":
                    msg["content"] = prompt_text
                    system_msg_exists = True
                    break
                    
            if not system_msg_exists:
                self.messages.insert(0, {"role": "system", "content": prompt_text})
                
            print(f"\n✅ 시스템 메시지가 업데이트되었습니다. (길이: {len(prompt_text)} 글자)")
        
        else:  # mode == "append"
            # 맨 앞에 새 시스템 메시지 추가 (기존 메시지 모두 유지)
            self.messages.insert(0, {"role": "system", "content": prompt_text})
            print(f"\n✅ 프롬프트가 시스템 메시지로 추가되었습니다. (길이: {len(prompt_text)} 글자)")
        
    def load_prompt_from_file(self, filepath: str, mode: str = "append") -> bool:
        """
        파일에서 프롬프트 불러와 적용
        
        Args:
            filepath (str): 프롬프트 파일 경로
            mode (str): 적용 모드
                - "append": 기존 메시지 유지하고 맨 앞에 추가 (기본값) 
                - "replace": 기존 시스템 메시지 교체
                - "update": 기존 시스템 메시지 있으면 내용 업데이트, 없으면 추가
                
        Returns:
            bool: 성공 여부
        """
        try:
            path = Path(filepath)
            
            # 파일이 없으면 prompt 폴더에서 찾아봄
            if not path.exists():
                prompt_dir = Path("prompt")
                if prompt_dir.exists():
                    alt_path = prompt_dir / path
                    if alt_path.exists():
                        path = alt_path
                    else:
                        # .txt 확장자 추가 시도
                        txt_path = prompt_dir / (str(path) + ".txt")
                        if txt_path.exists():
                            path = txt_path
            
            # 여전히 파일이 없으면 오류
            if not path.exists():
                print(f"⚠️ 프롬프트 파일을 찾을 수 없습니다: {filepath}")
                return False
                
            # 파일 읽기
            with open(path, "r", encoding="utf-8") as f:
                prompt_text = f.read()
                
            if not prompt_text.strip():
                print("⚠️ 프롬프트 파일이 비어 있습니다.")
                return False
                
            # 프롬프트 적용
            self.apply_prompt(prompt_text, mode=mode)
            return True
            
        except Exception as e:
            print(f"⚠️ 프롬프트 파일을 불러오는 중 오류가 발생했습니다: {e}")
            return False
    
    # 대화 저장 및 불러오기 메서드
    def save_conversation(self, filepath: Optional[str] = None) -> str:
        """
        대화 내용을 파일로 저장
        
        Args:
            filepath (str, optional): 저장할 파일 경로
            
        Returns:
            str: 저장된 파일 경로
        """
        if not self.messages:
            raise ValueError("저장할 대화 내용이 없습니다.")
            
        if not filepath:
            # 타임스탬프로 파일명 생성
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            filepath = self.chat_log_dir / f"chat_{timestamp}.json"
        else:
            # 사용자가 지정한 경로에 확장자가 없으면 .json 추가
            path = Path(filepath)
            if not path.suffix:
                path = Path(str(path) + ".json")
            
            # 상대 경로인 경우 chat_log 폴더 내에 저장
            if not path.is_absolute():
                path = self.chat_log_dir / path
                
            filepath = path
        
        # 저장할 데이터 준비
        data = {
            "title": "Ollama 채팅 기록",
            "created_at": datetime.datetime.now().isoformat(),
            "message_count": len(self.messages),
            "messages": self.messages
        }
        
        # JSON 형식으로 저장
        import json
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        return str(filepath)
    
    def list_saved_chats(self) -> List[Path]:
        """
        저장된 대화 목록 반환
        
        Returns:
            List[Path]: 저장된 채팅 파일 경로 목록
        """
        if not self.chat_log_dir.exists() or not self.chat_log_dir.is_dir():
            return []
        
        # .json 파일만 반환, 최근 수정일 기준 정렬
        return sorted(
            self.chat_log_dir.glob("*.json"), 
            key=lambda p: p.stat().st_mtime, 
            reverse=True
        )
    
    def display_saved_chats(self) -> Optional[Path]:
        """
        저장된 대화 목록을 표시하고 선택된 파일 경로 반환
        
        Returns:
            Optional[Path]: 선택된 파일 경로 또는 None
        """
        saved_chats = self.list_saved_chats()
        
        if not saved_chats:
            print("⚠️ 저장된 대화가 없습니다.")
            return None
        
        print("\n=== 저장된 대화 목록 ===")
        for i, chat_file in enumerate(saved_chats):
            # 파일 정보 가져오기
            mtime = datetime.datetime.fromtimestamp(chat_file.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
            size_kb = chat_file.stat().st_size / 1024
            
            # JSON 파일에서 제목 추출
            title = chat_file.name
            try:
                import json
                with open(chat_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if "title" in data:
                        title = data["title"]
                    
                    # 추가 정보 (메시지 수)
                    msg_count = data.get("message_count", len(data.get("messages", [])))
                    title = f"{title} (메시지 {msg_count}개)"
            except:
                pass
            
            print(f"[{i}] {title} ({chat_file.name}) - {mtime}, {size_kb:.1f}KB")
        
        # 사용자 선택
        while True:
            try:
                sel = input("\n불러올 대화 번호 선택 (취소: q): ")
                if sel.lower() in ["q", "취소", "cancel"]:
                    return None
                
                idx = int(sel)
                if 0 <= idx < len(saved_chats):
                    return saved_chats[idx]
            except ValueError:
                pass
            
            print("잘못된 입력입니다. 다시 선택하세요.")
    
    def load_conversation(self, filepath: Path) -> bool:
        """
        저장된 대화 파일에서 메시지 불러오기
        
        Args:
            filepath (Path): 불러올 파일 경로
            
        Returns:
            bool: 불러오기 성공 여부
        """
        if not filepath.exists():
            print(f"⚠️ 파일을 찾을 수 없습니다: {filepath}")
            return False
        
        # JSON 파일 불러오기
        try:
            import json
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            # 메시지 배열 가져오기
            if "messages" in data and isinstance(data["messages"], list):
                loaded_messages = data["messages"]
                
                # 메시지 형식 검증
                valid_messages = []
                for msg in loaded_messages:
                    if isinstance(msg, dict) and "role" in msg and "content" in msg:
                        # 역할 검증
                        role = msg["role"]
                        if role not in ["user", "assistant", "system"]:
                            # 잘못된 역할은 기본값으로 대체
                            if role == "사용자":
                                role = "user"
                            elif role in ["AI", "ai"]:
                                role = "assistant"
                            elif role in ["시스템", "System"]:
                                role = "system"
                            else:
                                # 알 수 없는 역할은 사용자로 처리
                                role = "user"
                        
                        valid_messages.append({
                            "role": role,
                            "content": msg["content"]
                        })
                
                if valid_messages:
                    self.messages = valid_messages
                    return True
                else:
                    print("⚠️ 유효한 메시지를 찾을 수 없습니다.")
                    return False
            else:
                print("⚠️ 파일에서 메시지 데이터를 찾을 수 없습니다.")
                return False
                
        except json.JSONDecodeError:
            print("⚠️ JSON 형식이 아니거나 잘못된 형식입니다.")
            return False
        except Exception as e:
            print(f"⚠️ 파일을 불러오는 중 오류가 발생했습니다: {e}")
            return False