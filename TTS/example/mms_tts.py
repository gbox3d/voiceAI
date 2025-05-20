# Facebook's Massively Multilingual Speech Synthesis (MMS-TTS) 모델을 사용하여 텍스트를 음성으로 변환하는 예제입니다.
#%%
# from transformers import VitsModel, AutoTokenizer
from transformers import VitsTokenizer, VitsModel, set_seed

import torch
import scipy

from pydub import AudioSegment
import numpy as np
import torch

#%% hgf 에서 모델과 토크나이저 불러오기
# model = VitsModel.from_pretrained("facebook/mms-tts-kor")
# tokenizer = AutoTokenizer.from_pretrained("facebook/mms-tts-kor")

tokenizer = VitsTokenizer.from_pretrained("facebook/mms-tts-kor")
model     = VitsModel.from_pretrained("facebook/mms-tts-kor")

text = "안녕하세요, 저는 안덕수 입니다. 반갑습니다."
# uroman 설치 후라면 아래 warning 없이 자동 로마자화
inputs = tokenizer(text, return_tensors="pt")

# 정수형 강제
inputs["input_ids"]     = inputs["input_ids"].long()
inputs["attention_mask"] = inputs.get("attention_mask", None)
if inputs["attention_mask"] is not None:
    inputs["attention_mask"] = inputs["attention_mask"].long()

set_seed(42)
with torch.no_grad():
    outputs = model(**inputs)  # 이제 waveform이 정상 생성됩니다.

#%%
# outputs.waveform[0] → waveform
waveform = outputs.waveform[0]

# NumPy 배열로 변환
waveform_np = waveform.detach().cpu().numpy()

# 샘플레이트
sr = model.config.sampling_rate  # 예: 16000

# 1) scipy로 WAV 저장
import scipy.io.wavfile
scipy.io.wavfile.write("output.wav", rate=sr, data=waveform_np)

# 2) (선택) pydub 사용 시, normalized int16 WAV 저장
from pydub import AudioSegment
import numpy as np

# 정규화 및 int16 변환
wave_norm = waveform_np / np.abs(waveform_np).max()
wave_int16 = (wave_norm * 32767).astype(np.int16)

audio_seg = AudioSegment(
    wave_int16.tobytes(),
    frame_rate=sr,
    sample_width=wave_int16.dtype.itemsize,
    channels=1
)
audio_seg.export("output_pydub.wav", format="wav")


# %%
