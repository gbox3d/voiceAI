# Ollama Chat

Ollama API를 활용한 간단한 터미널 기반 채팅 인터페이스입니다. 이 도구를 사용하면 로컬에서 Ollama를 통해 다양한 대형 언어 모델과 대화할 수 있습니다.

## 필수 요구 사항

- Python 3.8 이상
- [Ollama](https://ollama.ai/) 설치 및 실행 중

## 설치 방법

1. 이 저장소를 클론하거나 다운로드합니다:
   ```bash
   git clone [repository-url]
   cd [repository-directory]
   ```

2. 필요한 패키지를 설치합니다:
   ```bash
   pip install requests
   ```

## 사용 방법

### 기본 실행

```bash
python main.py
```

이 명령은 기본 설정으로 대화를 시작합니다. 기본적으로 `llama3` 모델을 사용합니다.

### 명령줄 옵션

다양한 옵션을 통해 동작을 사용자 정의할 수 있습니다:

```bash
python main.py --model llama3 --temperature 0.8 --chat-log-dir my_logs
```

#### 사용 가능한 옵션:

| 옵션 | 설명 | 기본값 |
| ---- | ---- | ------ |
| `--model` | 사용할 Ollama 모델 이름 | `llama3` |
| `--temperature` | 생성 시 온도 설정 (높을수록 더 창의적) | `0.7` |
| `--max-messages` | 메모리에 저장할 최대 메시지 수 | `100` |
| `--chat-log-dir` | 대화 로그를 저장할 디렉토리 | `chat_logs` |
| `--no-summary` | 자동 요약 기능 비활성화 | 비활성화되지 않음 |
| `--save` | 대화를 저장할 파일 이름 | - |
| `--load` | 불러올 대화 파일 이름 | - |

### 대화 저장 및 불러오기

대화를 저장하려면:
```bash
python main.py --save my_conversation
```

저장된 대화를 불러오려면:
```bash
python main.py --load my_conversation
```

파일 이름에 확장자를 지정하지 않으면 자동으로 `.json` 확장자가 추가됩니다.

## 대화 중 명령어

대화 중에는 다음 명령어를 사용할 수 있습니다:

- `exit`, `quit`, `q`, `종료`: 대화 종료
- `Ctrl+C`: 대화 종료

## 파일 구조

- `main.py` - 메인 실행 스크립트
- `ollama_chat.py` - OllamaChat 및 ChatMemory 클래스 구현

## 주요 기능

- 다양한 Ollama 모델과의 대화
- 대화 내용 저장 및 불러오기
- 메시지 수 제한 관리 (자동 요약)
- 사용자 정의 가능한 온도 및 기타 생성 매개변수

## 예제

### 특정 모델 및 온도로 실행

```bash
python main.py --model mistral --temperature 0.9
```

### 대화 저장 후 나중에 계속하기

세션 1:
```bash
python main.py --save monday_chat
```

세션 2 (나중에):
```bash
python main.py --load monday_chat
```

### 자동 요약 비활성화 및 최대 메시지 수 늘리기

```bash
python main.py --no-summary --max-messages 200
```

## 문제 해결

1. "API 오류" 메시지가 표시되는 경우:
   - Ollama가 실행 중인지 확인하세요
   - `http://localhost:11434`에 접속할 수 있는지 확인하세요

2. 특정 모델을 찾을 수 없는 경우:
   - `ollama list`로 사용 가능한 모델을 확인하세요
   - 필요한 경우 `ollama pull [model]`로 모델을 다운로드하세요