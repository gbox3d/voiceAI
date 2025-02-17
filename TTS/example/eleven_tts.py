#%%
import requests
import json
from dotenv import load_dotenv
import os

# 환경변수 파일(.env) 로드
load_dotenv('../.env')

print(f"ElevenLabs API 키: {os.getenv('ELEVENLABS_API_KEY')}")

#%%

API_KEY = os.getenv('ELEVENLABS_API_KEY')

# 사용할 보이스 아이디와 텍스트
voice_id = "uyVNoMrnUku1dZyVEXwD"
text = "안녕하세요"

# 음성 생성 API 엔드포인트 (보이스 아이디를 URL에 포함)
url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"

# 요청 헤더 (API 키와 JSON 콘텐츠 타입 지정)
headers = {
    "xi-api-key": API_KEY,
    "Content-Type": "application/json"
}

# 요청에 사용할 데이터 (모델 아이디와 출력 포맷은 필요에 따라 변경 가능)
payload = {
    "text": text,
    # 한국어와 다국어 지원을 위해 다국어 모델을 사용합니다.
    "model_id": "eleven_multilingual_v2",
    # 출력 포맷 (예: 44100Hz, 128kbps MP3)
    "output_format": "mp3_44100_128"
}

#%%
# POST 요청으로 텍스트를 음성으로 변환
response = requests.post(url, headers=headers, json=payload)

# 응답 상태 확인 및 파일 저장
if response.status_code == 200:
    output_filename = "output.mp3"
    with open(output_filename, "wb") as f:
        f.write(response.content)
    print(f"음성 파일이 성공적으로 생성되었습니다: {output_filename}")
else:
    print("음성 파일 생성 실패:", response.status_code, response.text)
