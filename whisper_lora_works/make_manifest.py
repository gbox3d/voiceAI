# make_manifest.py
import json, re
from pathlib import Path

root = Path("datasets/Sample")
wav_root = root / "01.원천데이터"
lab_root = root / "02.라벨링데이터"

def normalize_text(t: str) -> str:
    # (A)/(B) -> B
    t = re.sub(r"\(([^()]+?)\)/\(([^()]+?)\)", r"\2", t)
    # 남은 괄호 제거 (필요시)
    t = t.replace("(", "").replace(")", "")
    # 공백 정리
    t = re.sub(r"\s+", " ", t).strip()
    return t

out = Path(root/"manifest.jsonl").open("w", encoding="utf-8")

count = 0
for jp in lab_root.rglob("*.json"):
    obj = json.loads(jp.read_text(encoding="utf-8"))
    text = normalize_text(obj["script"]["text"])

    # 라벨 경로와 동일한 상대구조로 wav 찾기
    rel = jp.relative_to(lab_root).with_suffix(".wav")
    wav_path = wav_root / rel
    if not wav_path.exists():
        continue

    out.write(json.dumps({"audio": str(wav_path), "text": text}, ensure_ascii=False) + "\n")
    count += 1

out.close()
print("rows:", count)
