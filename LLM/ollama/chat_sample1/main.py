#!/usr/bin/env python3
"""
Ollama 채팅 스크립트 (객체지향 개선 버전)
시작할 때 로컬 모델 목록을 보여주고
번호를 선택하면 그 모델로 대화를 시작한다.

추가 기능:
- 대화 중 명령어 지원 (/help, /exit, /save, /params, /summary, /show mem, /load)
- 대화 내용 파일로 저장 및 불러오기
- 모델 매개변수 조절 가능
- 긴 대화 자동 요약 및 메모리 관리
"""
import argparse
from pathlib import Path

from ollama_chat import OllamaChat


def parse_arguments():
    """명령줄 인수 처리"""
    parser = argparse.ArgumentParser(description="Ollama 모델과 대화하는 스크립트")
    parser.add_argument("-m", "--model", help="사용할 모델 이름")
    parser.add_argument("-t", "--temperature", type=float, default=0.7,
                        help="모델 temperature 값 (기본값: 0.7)")
    parser.add_argument("-s", "--save", help="대화 내용을 저장할 파일 경로")
    parser.add_argument("-l", "--load", help="불러올 대화 파일 경로")
    parser.add_argument("-p", "--prompt", help="적용할 프롬프트 파일 경로")
    parser.add_argument("--prompt-mode", choices=["append", "replace", "update"],
                        default="append", help="프롬프트 적용 모드 (기본값: append)")
    parser.add_argument("--max-messages", type=int, default=20,
                        help="자동 요약 전 최대 메시지 수 (기본값: 20)")
    parser.add_argument("--no-summary", action="store_true",
                        help="자동 요약 기능 비활성화")
    parser.add_argument("--chat-log-dir", default="chat_log",
                        help="대화 로그 저장 디렉토리 (기본값: chat_log)")
    
    return parser.parse_args()


def main():
    """메인 함수"""
    args = parse_arguments()
    
    # 기본 매개변수 설정
    params = {
        "temperature": args.temperature,
        "top_p": 0.9,
        "top_k": 40,
    }
    
    # 채팅 객체 생성
    chat = OllamaChat(
        model=args.model,
        chat_log_dir=args.chat_log_dir,
        max_messages=args.max_messages,
        auto_summary=not args.no_summary,
        temperature=args.temperature,
        params=params
    )
    
    # 프롬프트 파일 적용 (가장 먼저 적용)
    if args.prompt:
        chat.memory.load_prompt_from_file(args.prompt, mode=args.prompt_mode)
    
    # 저장된 대화 불러오기 (명령줄 인수로 지정된 경우)
    if args.load:
        load_path = Path(args.load)
        if not load_path.is_absolute():
            # 상대 경로인 경우 chat_log 폴더 내에서 찾음
            load_path = Path(args.chat_log_dir) / load_path
            
        # 확장자가 없으면 .json 추가
        if not load_path.suffix:
            load_path = Path(str(load_path) + ".json")
            
        if load_path.exists():
            success = chat.memory.load_conversation(load_path)
            if success:
                print(f"✅ 대화를 불러왔습니다: {load_path}")
                print(f"✅ 불러온 메시지 수: {chat.memory.count_messages()}개")
            else:
                print(f"⚠️ 대화를 불러오지 못했습니다: {load_path}")
        else:
            print(f"⚠️ 파일을 찾을 수 없습니다: {load_path}")
    
    # 대화 루프 실행
    chat.chat_loop()
    
    # 명령줄 인수로 저장 옵션이 지정된 경우
    if args.save and chat.memory.count_messages() > 0:
        try:
            filepath = chat.memory.save_conversation(args.save)
            print(f"✅ 대화 내용이 저장되었습니다: {filepath}")
        except Exception as e:
            print(f"⚠️ 대화 저장 중 오류가 발생했습니다: {e}")


if __name__ == "__main__":
    main()