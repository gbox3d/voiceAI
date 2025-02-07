# Facebook's Massively Multilingual Speech Synthesis (MMS-TTS) 모델을 사용하여 텍스트를 음성으로 변환하는 예제입니다.
#%%
from transformers import VitsModel, AutoTokenizer
import torch
import scipy

from pydub import AudioSegment
import numpy as np
import torch

#%% hgf 에서 모델과 토크나이저 불러오기
model = VitsModel.from_pretrained("facebook/mms-tts-kor")
tokenizer = AutoTokenizer.from_pretrained("facebook/mms-tts-kor")

# 로컬 디렉토리에 저장 (예: "./mms_tts_kor_local")
model.save_pretrained("./weights/mms_tts_kor_local")
tokenizer.save_pretrained("./weights/mms_tts_kor_local")

#%% 저장된 파일에서 모델과 토크나이저 불러오기
model = VitsModel.from_pretrained("./weights/mms_tts_kor_local")
tokenizer = AutoTokenizer.from_pretrained("./weights/mms_tts_kor_local")

print(f'ok loading model and tokenizer')

#%%

text = "안녕하세요, 미라클 에이지 아이 입니다."
inputs = tokenizer(text, return_tensors="pt")

# %%
with torch.no_grad():
    output = model(**inputs).waveform
# %%
# 출력 텐서를 NumPy 배열로 변환
output_np = output.squeeze().detach().cpu().numpy()

#%% mp3로 저장하기
# 정규화 및 int16 변환
waveform_norm = output_np / np.abs(output_np).max()
waveform_int16 = (waveform_norm * 32767).astype(np.int16)

# AudioSegment 생성
audio_segment = AudioSegment(
    waveform_int16.tobytes(),
    frame_rate=model.config.sampling_rate,
    sample_width=waveform_int16.dtype.itemsize,
    channels=1
)

# MP3 파일로 저장 (높은 비트레이트 지정)
audio_segment.export("output.mp3", format="mp3", bitrate="192k")


# %% wav로 저장하기

scipy.io.wavfile.write("output.wav", rate=model.config.sampling_rate, data=output_np)


# %%
