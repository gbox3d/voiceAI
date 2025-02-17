#%%
import torch
from transformers import AutoModelForSpeechSeq2Seq, AutoProcessor, pipeline

# 디바이스 설정: GPU가 있으면 GPU를, 없으면 CPU 사용
device = "cuda:0" if torch.cuda.is_available() else "cpu"
torch_dtype = torch.float16 if torch.cuda.is_available() else torch.float32

#%%
# 모델 및 프로세서 불러오기 (Whisper large-v3-turbo)
model_id = "openai/whisper-large-v3-turbo"
model = AutoModelForSpeechSeq2Seq.from_pretrained(
    model_id,
    torch_dtype=torch_dtype,
    low_cpu_mem_usage=True,
    use_safetensors=True
)
model.to(device)
processor = AutoProcessor.from_pretrained(model_id)

print("모델 및 프로세서 불러오기 완료")

#%%
# 파이프라인 생성: 자동 음성 인식(ASR)
asr_pipe = pipeline(
    "automatic-speech-recognition",
    model=model,
    tokenizer=processor.tokenizer,
    feature_extractor=processor.feature_extractor,
    torch_dtype=torch_dtype,
    device=device
)

print(" 자동 음성 인식(ASR)  파이프라인 생성 완료")

#%%
# mp3 파일 경로 (예: "input.mp3")
audio_file = "test2.mp3"

# 한국어로 전사하도록 language 파라미터 설정
result = asr_pipe(audio_file, generate_kwargs={"language": "korean"})

print("전사 결과:", result["text"])

# %%
