#%%

from melo.api import TTS   # 레퍼런스 WAV 없이 한국어 기본 화자 TTS

#%%
text = "안녕하세요! 미라클 A G I 입니다. 반갑습니다."
device = "cuda"            # GPU 없으면 "cpu"

tts = TTS(language="KR", device=device)
spk_id = tts.hps.data.spk2id["KR"]   # 기본 여성 화자
tts.tts_to_file(text, spk_id, "output.wav")

print("✅ output.wav 생성 완료")

# %%
