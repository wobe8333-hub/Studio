# scripts/test_nano_banana_poc_v2.py
"""POC v2: gemini-3.1-flash-image-preview로 동일 캐릭터 생성 — 모델 품질 비교용

사용법:
    cd C:\\Users\\조찬우\\Desktop\\ai_stuidio_claude
    python scripts/test_nano_banana_poc_v2.py
"""
import io
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.path.insert(0, str(Path(__file__).parent / "generate_branding"))

from dotenv import load_dotenv
load_dotenv()

import os
from google import genai
from google.genai import types
from config import CHANNELS, KAS_ROOT

REFERENCE = KAS_ROOT / "essential_branding" / "CH1.png"
OUT_V2 = KAS_ROOT / "assets" / "channels" / "CH1" / "characters" / "character_explain_poc_v2.png"

MODEL_V2 = "gemini-3.1-flash-image-preview"

client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
ch1 = CHANNELS["CH1"]
prompt = ch1["character_prompts"]["explain"]

ref_bytes = REFERENCE.read_bytes()
ref_part = types.Part.from_bytes(data=ref_bytes, mime_type="image/png")

full_prompt = (
    "Replicate EXACTLY the flat 2D hand-drawn doodle illustration style shown "
    "in the reference image. Same line weight (2-3px thin black marker), "
    "same cream paper background (#FFFDF5), same wobbly hand-drawn lines, "
    "same flat coloring with NO gradients or shadows, NO shading, NO 3D effects. "
    f"Now generate: {prompt}. "
    "Output ONLY the character on cream background, NO text, NO labels, NO hex codes."
)

print(f"모델: {MODEL_V2}")
print(f"레퍼런스: {REFERENCE}")
print(f"출력: {OUT_V2}")
print("생성 중...\n")

try:
    response = client.models.generate_content(
        model=MODEL_V2,
        contents=[ref_part, full_prompt],
        config=types.GenerateContentConfig(
            response_modalities=["IMAGE"],
        ),
    )
    for part in response.candidates[0].content.parts:
        if part.inline_data and part.inline_data.mime_type.startswith("image/"):
            OUT_V2.parent.mkdir(parents=True, exist_ok=True)
            OUT_V2.write_bytes(part.inline_data.data)
            print(f"[성공] {OUT_V2.name} ({len(part.inline_data.data):,} bytes)")
            print(f"\n비교 이미지 열기: start {OUT_V2}")
            break
    else:
        print("[실패] 이미지 응답 없음")
except Exception as e:
    print(f"[오류] {e}")
