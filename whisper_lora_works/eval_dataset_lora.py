import argparse
import json
import os
import re
import numpy as np
import torch
import pandas as pd
from tqdm import tqdm
from pathlib import Path

# 오디오 처리 라이브러리
import soundfile as sf
from transformers import WhisperProcessor, WhisperForConditionalGeneration
from peft import PeftModel

# ==========================================
# 1. 유틸리티 함수
# ==========================================

def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--manifest", type=str, default="datasets/Sample/manifest.jsonl", help="평가할 데이터셋 경로")
    p.add_argument("--base_model", type=str, default="openai/whisper-small", help="베이스 모델")
    p.add_argument("--lora_dir", type=str, default="outputs/small_lora", help="학습된 LoRA 경로")
    p.add_argument("--output_csv", type=str, default="comparison_results.csv", help="결과 저장 파일명")
    p.add_argument("--language", default="ko")
    p.add_argument("--task", default="transcribe")
    return p.parse_args()

def load_audio_16k(wav_path: str):
    """오디오를 로드하고 16kHz Mono로 변환"""
    if not os.path.exists(wav_path):
        if os.path.exists(os.path.join(os.getcwd(), wav_path)):
            wav_path = os.path.join(os.getcwd(), wav_path)
        else:
            return None

    try:
        audio, sr = sf.read(wav_path)
        if isinstance(audio, np.ndarray) and audio.ndim == 2:
            audio = audio.mean(axis=1) # stereo to mono
        
        if sr != 16000:
            from scipy.signal import resample_poly
            import math
            g = math.gcd(sr, 16000)
            audio = resample_poly(audio, 16000 // g, sr // g)
            
        return audio.astype(np.float32)
    except Exception as e:
        print(f"Error loading {wav_path}: {e}")
        return None

def normalize_text_ko(s: str) -> str:
    """한국어 텍스트 정규화"""
    s = str(s).strip()
    s = re.sub(r'\([^)]*\)', '', s) # 괄호 제거
    s = re.sub(r"[^0-9A-Za-z가-힣\s]", "", s) # 특수문자 제거
    s = re.sub(r"\s+", " ", s).strip()
    return s

def levenshtein(a, b):
    n, m = len(a), len(b)
    if n == 0: return m
    if m == 0: return n
    dp = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(n + 1): dp[i][0] = i
    for j in range(m + 1): dp[0][j] = j
    
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            cost = 0 if a[i-1] == b[j-1] else 1
            dp[i][j] = min(dp[i-1][j] + 1, dp[i][j-1] + 1, dp[i-1][j-1] + cost)
    return dp[n][m]

def calc_cer(ref, hyp):
    ref = ref.replace(" ", "")
    hyp = hyp.replace(" ", "")
    if len(ref) == 0: return 1.0 if len(hyp) > 0 else 0.0
    dist = levenshtein(ref, hyp)
    return dist / len(ref)

# ==========================================
# 2. 메인 평가 로직
# ==========================================

def main():
    args = parse_args()
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"🚀 Evaluation Start on {device.upper()}")
    print(f"📂 Manifest: {args.manifest}")

    # 1. 모델 로딩
    print("⏳ Loading Models...")
    
    processor = WhisperProcessor.from_pretrained(args.base_model, language=args.language, task=args.task)
    
    # Base Model
    base_model = WhisperForConditionalGeneration.from_pretrained(args.base_model).to(device)
    # 경고 방지를 위해 config 직접 설정 대신 generate 시 kwargs로 전달 예정
    base_model.eval()

    # LoRA Model
    _base_for_lora = WhisperForConditionalGeneration.from_pretrained(args.base_model)
    lora_model = PeftModel.from_pretrained(_base_for_lora, args.lora_dir).to(device)
    lora_model.eval()
    
    print("✅ Models Loaded Successfully.")

    # 2. 데이터 로딩
    dataset = []
    with open(args.manifest, 'r', encoding='utf-8') as f:
        for line in f:
            dataset.append(json.loads(line))
    
    results = []
    total_cer_base = 0
    total_cer_lora = 0
    count = 0

    print(f"📊 Processing {len(dataset)} samples...")
    
    # 3. 추론 루프
    for item in tqdm(dataset):
        audio_path = item['audio']
        ref_text = item['text']
        
        audio = load_audio_16k(audio_path)
        if audio is None: continue

        inputs = processor(audio, sampling_rate=16000, return_tensors="pt").input_features.to(device)

        with torch.no_grad():
            # ✅ [수정] positional argument 에러 방지를 위해 'input_features=' 명시
            # 또한 언어/태스크 설정을 generate 함수에 직접 전달하여 경고 제거
            
            # Base 추론
            gen_base = base_model.generate(
                input_features=inputs, 
                max_new_tokens=128,
                language=args.language,
                task=args.task
            )
            text_base = processor.batch_decode(gen_base, skip_special_tokens=True)[0]

            # LoRA 추론
            gen_lora = lora_model.generate(
                input_features=inputs, 
                max_new_tokens=128,
                language=args.language,
                task=args.task
            )
            text_lora = processor.batch_decode(gen_lora, skip_special_tokens=True)[0]

        # 정규화 및 CER 계산
        norm_ref = normalize_text_ko(ref_text)
        norm_base = normalize_text_ko(text_base)
        norm_lora = normalize_text_ko(text_lora)

        cer_base = calc_cer(norm_ref, norm_base)
        cer_lora = calc_cer(norm_ref, norm_lora)

        total_cer_base += cer_base
        total_cer_lora += cer_lora
        count += 1

        results.append({
            "audio": audio_path,
            "Reference": norm_ref,
            "Base_Pred": norm_base,
            "LoRA_Pred": norm_lora,
            "Base_CER": round(cer_base, 4),
            "LoRA_CER": round(cer_lora, 4),
            "Improved": cer_lora < cer_base
        })

    # 4. 결과 요약
    if count > 0:
        avg_base = total_cer_base / count
        avg_lora = total_cer_lora / count
        improvement = avg_base - avg_lora

        print("\n" + "="*40)
        print(" 📢 FINAL EVALUATION REPORT")
        print("="*40)
        print(f" Samples Evaluated : {count}")
        print(f" Average CER (Base): {avg_base:.4f} ({avg_base*100:.2f}%)")
        print(f" Average CER (LoRA): {avg_lora:.4f} ({avg_lora*100:.2f}%)")
        print(f" 📈 Improvement    : {improvement:+.4f} ({(improvement/avg_base)*100:+.2f}%p improvement)")
        print("="*40)

        df = pd.DataFrame(results)
        df.to_csv(args.output_csv, index=False, encoding='utf-8-sig')
        print(f"💾 Detailed results saved to: {args.output_csv}")

        print("\n[Sample Improvements]")
        better_df = df[df['Improved'] == True].head(3)
        if not better_df.empty:
            for _, row in better_df.iterrows():
                print(f"Ref : {row['Reference']}")
                print(f"Base: {row['Base_Pred']}")
                print(f"LoRA: {row['LoRA_Pred']}")
                print("-" * 30)
    else:
        print("No valid samples processed.")

if __name__ == "__main__":
    main()