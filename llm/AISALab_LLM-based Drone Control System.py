#!/usr/bin/env python
# coding: utf-8

# In[1]:


import os
import queue
import pyaudio
import torch
from google.cloud import speech
from torch import cuda, bfloat16
from transformers import pipeline, StoppingCriteria, StoppingCriteriaList
import transformers
from time import sleep, time as current_time
import time

from CodingDrone.drone import Drone
from CodingDrone.protocol import *

# Audio recording parameters
RATE = 16000
CHUNK = int(RATE / 10)  # 100ms

# Google Cloud credentials 설정
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "../STT/aisa-drone1-510cdea81a41.json"

# 모델 설정
model_id = 'meta-llama/Meta-Llama-3-8B'

# CUDA가 가능한지 확인하고, 없다면 CPU로 설정
if cuda.is_available():
    device = f'cuda:{cuda.current_device()}'
    print(f"CUDA 사용 가능: {device}에서 실행합니다.")
else:
    device = 'cpu'
    print("CUDA를 찾을 수 없습니다. CPU에서 실행합니다.")

# bitsandbytes 설정
bnb_config = transformers.BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_quant_type='nf4',
    bnb_4bit_use_double_quant=True,
    bnb_4bit_compute_dtype=bfloat16
)

# 모델 로드
model = transformers.AutoModelForCausalLM.from_pretrained(
    model_id,
    trust_remote_code=True,
    quantization_config=bnb_config,
    device_map='auto'
)
model.eval()
tokenizer = transformers.AutoTokenizer.from_pretrained(model_id)

# 정지 토큰 설정
stop_list = ['\nHuman:', '\n']
stop_token_ids = [tokenizer(x)['input_ids'] for x in stop_list]
stop_token_ids = [torch.LongTensor(x).to(device) for x in stop_token_ids]

# 사용자 정의 정지 조건 객체
class StopOnTokens(StoppingCriteria):
    def __call__(self, input_ids: torch.LongTensor, scores: torch.FloatTensor, **kwargs) -> bool:
        for stop_ids in stop_token_ids:
            if torch.eq(input_ids.to(device)[0][-len(stop_ids):], stop_ids).all():
                return True
        return False

stopping_criteria = StoppingCriteriaList([StopOnTokens()])

# 텍스트 생성 파이프라인 설정
generate_text = pipeline(
    model=model,
    tokenizer=tokenizer,
    return_full_text=False,
    task='text-generation',
    temperature=0.1,
    max_new_tokens=50,
    repetition_penalty=1.1
)

# 새로운 드론 제어 함수
def takeoff(drone):
    print("Drone Takeoff")
    drone.sendTakeOff()
def landing(drone):
    print("Drone Landing")
    drone.sendLanding()
def move_up(drone):
    print("Moving up")
    drone.sendControlPosition(0, 0, 0.5, 1, 0, 0)
def move_down(drone):
    print("Moving down")
    drone.sendControlPosition(0, 0, -0.5, 1, 0, 0)
def move_left(drone):
    print("Moving left")
    drone.sendControlPosition(0, -1.0, 0, 0.5, 0, 0)
def move_right(drone):
    print("Moving right")
    drone.sendControlPosition(0, 1.0, 0, 0.5, 0, 0)
def move_forward(drone):
    print("Moving forward")
    drone.sendControlPosition(1.0, 0, 0, 0.5, 0, 0)
def move_backward(drone):
    print("Moving backward")
    drone.sendControlPosition(-1.0, 0, 0, 0.5, 0, 0)
def hover(drone):
    print("Hovering")
    drone.sendControlWhile(0, 0, 0, 0, 1000)

# 프롬프트 업데이트
prompt = """
너는 고급 언어 모델인 LLAMA3이며, 드론 제어 명령을 해석하고 응답해야 합니다. 주어진 명령에 따라 정확하고 구체적인 응답을 제공하여 드론을 제어할 수 있도록 해야 합니다. 명령을 해석할 때 아래의 규칙을 따라야 합니다:

### 규칙:

1. **이륙 명령:**
   - 드론을 이륙시키라는 모든 명령은 "takeoff"로 응답하세요.
   - 관련된 키워드: "이륙", "출발", "날아올라", "뜨다", "오르다".
   - 예시: "드론을 이륙시켜 주세요."

2. **착륙 명령:**
   - 드론을 착륙시키라는 모든 명령은 "landing"로 응답하세요.
   - 관련된 키워드: "착륙", "내려", "착지", "도착".
   - 예시: "드론을 착륙시켜 주세요."

3. **상승 명령:**
   - 드론을 위로 이동시키라는 모든 명령은 "move up"으로 응답하세요.
   - 관련된 키워드: "올라", "위로", "상승", "높이", "올리다".
   - 예시: "드론을 더 높이 올려 주세요."

4. **하강 명령:**
   - 드론을 아래로 이동시키라는 모든 명령은 "move down"으로 응답하세요.
   - 관련된 키워드: "내려", "아래로", "하강", "낮춰", "떨어지다".
   - 예시: "드론을 아래로 내려 주세요."

5. **왼쪽 이동 명령:**
   - 드론을 왼쪽으로 이동시키라는 모든 명령은 "move left"로 응답하세요.
   - 관련된 키워드: "왼쪽", "좌측", "왼편", "왼쪽으로".
   - 예시: "드론을 왼쪽으로 이동시켜 주세요."

6. **오른쪽 이동 명령:**
   - 드론을 오른쪽으로 이동시키라는 모든 명령은 "move right"로 응답하세요.
   - 관련된 키워드: "오른쪽", "우측", "오른편", "오른쪽으로".
   - 예시: "드론을 오른쪽으로 이동시켜 주세요."

7. **앞으로 이동 명령:**
   - 드론을 앞으로 이동시키라는 모든 명령은 "move forward"로 응답하세요.
   - 관련된 키워드: "앞으로", "전방", "전진", "앞쪽".
   - 예시: "드론을 앞으로 이동시켜 주세요."

8. **뒤로 이동 명령:**
   - 드론을 뒤로 이동시키라는 모든 명령은 "move backward"로 응답하세요.
   - 관련된 키워드: "뒤로", "후방", "후진", "뒤쪽".
   - 예시: "드론을 뒤로 이동시켜 주세요."

9. **호버링 명령:**
   - 드론을 제자리에서 호버링 시키라는 모든 명령은 "hovering"으로 응답하세요.
   - 관련된 키워드: "호버링", "제자리", "유지", "고정", "가만히".
   - 예시: "드론을 제자리에서 호버링 시켜 주세요."

10. **비상 정지 명령:**
    - 드론을 즉시 멈추라는 모든 명령은 "stop"으로 응답하세요.
    - 관련된 키워드: "정지", "멈춰", "비상 정지", "즉시 멈춤".
    - 예시: "드론을 즉시 멈춰 주세요."

11. **제어 명령:**
    - 드론의 롤, 피치, 요, 스로틀을 구체적으로 제어하라는 명령은 다음 형식으로 응답하세요:
      control <roll> <pitch> <yaw> <throttle>
    - 예시 입력: "롤 0, 피치 30, 요 0, 스로틀 5000"
    - 예시 출력: control 0 30 0 5000

12. **위치 명령:**
    - 드론의 특정 위치를 지정하여 이동시키라는 명령은 다음 형식으로 응답하세요:
      position <x> <y> <z> <yaw> <pitch>
    - 예시 입력: "x 5, y 0, z 2, 요 90, 피치 45"
    - 예시 출력: position 5 0 2 90 45

13. **방향 명령:**
    - 드론의 방향을 설정하라는 명령은 다음 형식으로 응답하세요:
      heading <yaw> <pitch>
    - 예시 입력: "요 90, 피치 45"
    - 예시 출력: heading 90 45

14. **이해하지 못한 명령:**
    - 명령을 이해하지 못한 경우 "hovering"으로 응답하세요.
    - 명령에 모순이 있는 경우 "hovering"으로 응답하세요.
    - 명령에 여러 단계가 있는 경우 "hovering"으로 응답하세요.
    
### 예시 쿼리와 응답:

- 쿼리: "드론이 지금 이륙할 수 있나요?"
  - 응답: takeoff

- 쿼리: "드론을 즉시 착륙시켜야 합니다."
  - 응답: landing

- 쿼리: "드론을 더 높이 올려 주세요."
  - 응답: move up

- 쿼리: "드론을 아래로 내려 주세요."
  - 응답: move down

- 쿼리: "드론을 왼쪽으로 이동시켜 주세요."
  - 응답: move left

- 쿼리: "드론을 오른쪽으로 이동시켜 주세요."
  - 응답: move right

- 쿼리: "드론을 앞으로 이동시켜 주세요."
  - 응답: move forward

- 쿼리: "드론을 뒤로 이동시켜 주세요."
  - 응답: move backward

- 쿼리: "드론을 제자리에서 호버링 시켜 주세요."
  - 응답: hovering

- 쿼리: "드론을 즉시 멈춰 주세요."
  - 응답: stop

- 쿼리: "롤 0, 피치 30, 요 0, 스로틀 5000으로 드론을 조정해 주세요."
  - 응답: control 0 30 0 5000

- 쿼리: "x 5, y 0, z 2 위치로 드론을 이동시키고, 요 90, 피치 45로 설정해 주세요."
  - 응답: position 5 0 2 90 45

- 쿼리: "방향을 요 90, 피치 45로 변경해 주세요."
  - 응답: heading 90 45

다음은 사용자 쿼리입니다:
"""

# 드론 제어 명령을 해석하여 응답하는 함수
def interpret_drone_command(command):
    full_prompt = prompt + "Human: " + command + "\nLLM:"
    result = generate_text(full_prompt, max_new_tokens=50, stopping_criteria=stopping_criteria)
    response = result[0]['generated_text'].split('Human:')[0].strip().split('\n')[0]
    return response

# 드론 동작을 제어하는 함수
def execute_drone_command(drone, response):
    if response == "takeoff":
        takeoff(drone)
    elif response == "landing":
        landing(drone)
    elif response == "move up":
        move_up(drone)
    elif response == "move down":
        move_down(drone)
    elif response == "move left":
        move_left(drone)
    elif response == "move right":
        move_right(drone)
    elif response == "move forward":
        move_forward(drone)
    elif response == "move backward":
        move_backward(drone)
    elif response == "hovering":
        hover(drone)
    elif response == "stop":
        print("Emergency Stop")
        drone.sendStop()
    elif response.startswith("control"):
        _, roll, pitch, yaw, throttle = response.split()
        print(f"Control: Roll={roll}, Pitch={pitch}, Yaw={yaw}, Throttle={throttle}")
        drone.sendControl(int(roll), int(pitch), int(yaw), int(throttle), 1000)
    elif response.startswith("position"):
        _, x, y, z, yaw, pitch = response.split()
        print(f"Position: X={x}, Y={y}, Z={z}, Yaw={yaw}, Pitch={pitch}")
        drone.sendControlPosition(float(x), float(y), float(z), float(yaw), float(pitch), 0)
    elif response.startswith("heading"):
        _, yaw, pitch = response.split()
        print(f"Heading: Yaw={yaw}, Pitch={pitch}")
        # Assuming heading involves adjusting yaw and pitch
        drone.sendControlPosition(0, 0, 0, float(yaw), float(pitch), 0)
    else:
        print("Command not recognized, hovering")
        drone.sendControlWhile(0, 0, 0, 0, 1000)

# MicrophoneStream 클래스 정의
class MicrophoneStream:
    def __init__(self, rate, chunk):
        self._rate = rate
        self._chunk = chunk
        self._buff = queue.Queue()
        self.closed = True

    def __enter__(self):
        self._audio_interface = pyaudio.PyAudio()
        self._audio_stream = self._audio_interface.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=self._rate,
            input=True,
            frames_per_buffer=self._chunk,
            stream_callback=self._fill_buffer,
        )
        self.closed = False
        return self

    def __exit__(self, type, value, traceback):
        self._audio_stream.stop_stream()
        self._audio_stream.close()
        self.closed = True
        self._buff.put(None)
        self._audio_interface.terminate()

    def _fill_buffer(self, in_data, frame_count, time_info, status_flags):
        self._buff.put(in_data)
        return None, pyaudio.paContinue

    def generator(self):
        while not self.closed:
            chunk = self._buff.get()
            if chunk is None:
                return
            data = [chunk]

            while True:
                try:
                    chunk = self._buff.get(block=False)
                    if chunk is None:
                        return
                    data.append(chunk)
                except queue.Empty:
                    break

            yield b"".join(data)

def recognize_audio():
    language_code = "ko-KR"  # Korean language code

    client = speech.SpeechClient()
    config = speech.RecognitionConfig(
        encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
        sample_rate_hertz=RATE,
        language_code=language_code,
    )

    streaming_config = speech.StreamingRecognitionConfig(
        config=config,
        interim_results=False,  # Complete results only
    )

    with MicrophoneStream(RATE, CHUNK) as stream:
        audio_generator = stream.generator()
        requests = (speech.StreamingRecognizeRequest(audio_content=content) for content in audio_generator)

        responses = client.streaming_recognize(config=streaming_config, requests=requests)

        # 결과에서 첫 번째 응답만 반환
        for response in responses:
            if not response.results:
                continue
            result = response.results[0]
            if not result.alternatives:
                continue
            transcript = result.alternatives[0].transcript
            return transcript
            

def main():
    print("╔══════════════════════════════════════════════════════════╗")
    print("║           GNU_AISALab X 항공우주전문가협동조합           ║")
    print("╠══════════════════════════════════════════════════════════╣")
    print("║         드론 제어 시스템에 오신 것을 환영합니다!         ║")
    print("╠══════════════════════════════════════════════════════════╣")
    print("║     시스템을 시작하고 있습니다. 잠시만 기다려 주세요...  ║")
    print("╚══════════════════════════════════════════════════════════╝\n")

    # 포트 번호를 입력받음
    while True:
        print("╔══════════════════════════════════════════════════════════╗")
        port_number = input("║   포트 번호를 숫자만 입력하세요 (예: 6): ")
        print("╚══════════════════════════════════════════════════════════╝")
        port = f'COM{port_number}'  # 숫자를 COM 포맷으로 변환
        if not port_number:  # 포트 번호가 입력되지 않았을 때
            print("╔══════════════════════════════════════════════════════════╗")
            print("║  ⚠️  포트 번호를 입력해 주세요.                          ║")
            print("╚══════════════════════════════════════════════════════════╝")
            continue
        try:
            drone = Drone()
            drone.open(port)  # 입력된 포트 번호로 드론 연결
            print("╔══════════════════════════════════════════════════════════╗")
            print(f"║  ✅ {port} 포트에 성공적으로 연결되었습니다.               ║")
            print("╚══════════════════════════════════════════════════════════╝")
            break
                
        except Exception as e:
            print("╔══════════════════════════════════════════════════════════╗")
            print(f"║  ❌ 연결 실패: {e}")
            print("╚══════════════════════════════════════════════════════════╝")
            continue

    try:
        while True:
            print('\n╔══════════════════════════════════════════════════════════╗')
            input("║  명령을 시작하려면 엔터 키를 누르세요...                 ║")
            print("╠══════════════════════════════════════════════════════════╣")
            # 음성 인식 시작
            print("║  🎤 명령 인식 중...                                      ║")
            transcript = recognize_audio()
            print(f"║  🎧 명령 인식 결과: {transcript}")                     
            print("╠══════════════════════════════════════════════════════════╣")
            print("║  명령 처리 중...                                         ║")
            # 인식 결과 확인
            drone_response = interpret_drone_command(transcript)
            print("║  명령을 실행합니다...                                    ║")
            execute_drone_command(drone, drone_response)  # 드론 명령 실행
            print("║  ✅ 명령이 실행되었습니다.                               ║")
            print("╚══════════════════════════════════════════════════════════╝\n")

    finally:
        print("╔══════════════════════════════════════════════════════════╗")
        drone.close()  # 드론 연결 종료
        print("║  🛑 드론 연결이 종료되었습니다.                          ║")
        input("║  프로그램을 종료하시려면 엔터 키를 누르세요.             ║")
        print("╚══════════════════════════════════════════════════════════╝")

if __name__ == "__main__":
    main()




# In[ ]:





# In[ ]:




