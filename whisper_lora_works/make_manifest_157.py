#file : whisper_lora_works/make_manifest_157.py
#author : gbox3d
# 이 주석은 수정하지 마세요.

import json
import re
import argparse
from pathlib import Path

def parse_args():
    parser = argparse.ArgumentParser(description="Whisper LoRA용 매니페스트 생성 스크립트 (TXT 기반)")
    # 기본 경로를 스크린샷의 'New_Sample' 기준으로 변경 가능하도록 설정
    parser.add_argument("--root", type=str, default="datasets/New_Sample", help="데이터셋 루트 경로")
    parser.add_argument("--output", type=str, default="manifest.jsonl", help="출력 파일명")
    return parser.parse_args()

def normalize_text(t: str) -> str:
    """
    제공된 txt 파일 포맷에 맞춰 정제 로직 수정
    예시: "자/ 누리 (소통방에서)/(소통망에서)..."
    """
    # 1. 패턴 제거    
    t = re.sub(r"/", "", t)

    # 2. (A)/(B) -> B 패턴 처리 (이전 로직 유지)
    # 괄호 안의 내용이 선택되며, 슬래시로 구분된 경우 뒤의 것을 선택
    t = re.sub(r"\(([^()]+?)\)/\(([^()]+?)\)", r"\2", t)

    # 3. 남은 괄호 제거
    t = t.replace("(", "").replace(")", "")

    # 4. 슬래시(/) 제거 (예: "자/ 누리" -> "자 누리" 또는 "자누리")
    # 문맥상 숨표나 노이즈 마킹일 수 있으므로 공백으로 치환하거나 삭제. 
    # 여기서는 단순 삭제 후 다중 공백 처리로 넘깁니다.
    t = t.replace("/", " ") 

    # 5. 공백 정리 (다중 공백 -> 단일 공백, 양옆 공백 제거)
    t = re.sub(r"\s+", " ", t).strip()
    
    return t

def main():
    args = parse_args()
    
    root = Path(args.root)
    out_path = root / args.output

    if not root.exists():
        print(f"❌ Error: 루트 폴더를 찾을 수 없습니다: {root}")
        return

    print(f"📂 Root: {root}")
    print(f"   Searching for .txt files recursively...")

    count = 0
    
    # 기존 모드(w) 대신, 안전하게 인코딩 지정하여 오픈
    with out_path.open("w", encoding="utf-8") as out:
        # root 하위의 모든 .txt 파일 탐색
        for txt_path in root.rglob("*.txt"):
            try:
                # 텍스트 읽기
                raw_text = txt_path.read_text(encoding="utf-8")
                
                # 텍스트가 비어있으면 스킵
                if not raw_text.strip():
                    continue

                text = normalize_text(raw_text)

                # 동일한 이름의 wav 파일 찾기 (확장자만 변경)
                wav_path = txt_path.with_suffix(".wav")
                
                if not wav_path.exists():
                    # wav가 없는 txt는 메타데이터 파일이거나 다른 용도일 수 있으므로 스킵
                    # print(f"⚠️ Missing audio for: {txt_path.name}")
                    continue

                # 절대 경로 대신 상대 경로를 사용할지, 절대 경로를 사용할지 결정
                # 학습 코드에서 로딩하기 편하게 절대 경로(혹은 실행 위치 기준)로 저장
                # 여기서는 스크립트 실행 위치 기준 상대 경로가 깔끔할 수 있습니다.
                # 하지만 확실한 로딩을 위해 str(wav_path)를 그대로 사용합니다.
                
                entry = {
                    "audio": str(wav_path.resolve()), # 절대 경로로 변환하여 저장 권장
                    "text": text
                }
                
                out.write(json.dumps(entry, ensure_ascii=False) + "\n")
                count += 1
                
            except Exception as e:
                print(f"Error processing {txt_path}: {e}")
                continue

    print("-" * 30)
    print(f"✅ Created: {out_path.resolve()}")
    print(f"📊 Total Rows: {count}")

if __name__ == "__main__":
    main()