"""CH1 마스코트 테스트 생성 (5장).

사용법:
    python scripts/generate_branding/test_mascot_ch1.py
"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.path.insert(0, str(__file__).split("scripts")[0])

from pathlib import Path
from dotenv import load_dotenv
load_dotenv()

import scripts.generate_branding.gemini_image_gen as img_gen
img_gen.MODEL_MULTIMODAL = "gemini-3.1-flash-image-preview"

from scripts.generate_branding.gemini_image_gen import (
    generate_best_of_n_multi_reference,
    _make_client,
)

# ─── 레퍼런스 ─────────────────────────────────────────────────────────────────
BASE_PLAIN = Path("assets/shared/base_plain.png")
CH1_LOGO   = Path("assets/channels/CH1/logo/logo.png")

# ─── 출력 경로 ────────────────────────────────────────────────────────────────
OUTPUT_DIR = Path("assets/channels/CH1/_candidates/mascot")

# ─── 프롬프트 ─────────────────────────────────────────────────────────────────
PROMPT = (
    "Create a cute chibi mascot character based on these TWO reference images. "

    "From the FIRST reference (character): "
    "inherit the exact body proportions (3.5-head chibi ratio), "
    "bald round head, chubby round face with rosy cheeks, "
    "simple 2px black doodle outline style, flat colors, "
    "front-facing friendly pose. "

    "From the SECOND reference (logo): "
    "inherit the golden yellow (#FFD700) and teal/green color palette, "
    "economics and money theme (balance scales, coins, currency symbols, charts). "

    "Costume design: smart business suit or vest in golden/navy tones, "
    "holding a small gold coin or mini chart in one hand. "
    "Optional: tiny $ or W symbol accessory. "

    "Style rules: white background, full body visible, "
    "same kawaii doodle illustration style as the first reference, "
    "no text, no logo, character only."
)


def main():
    client = _make_client()

    print("[CH1] 마스코트 5장 테스트 생성 중...")
    saved = generate_best_of_n_multi_reference(
        reference_image_paths=[BASE_PLAIN, CH1_LOGO],
        prompt=PROMPT,
        output_dir=OUTPUT_DIR,
        n=5,
        client=client,
    )
    print(f"[CH1] 완료: {len(saved)}/5장 저장")
    print(f"저장 위치: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
