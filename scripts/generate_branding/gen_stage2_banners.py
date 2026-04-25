"""2단계: 배너 10장 × 7채널 Gemini 생성.

사용법:
    python scripts/generate_branding/gen_stage2_banners.py
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

# ─── 채널별 배너 프롬프트 ─────────────────────────────────────────────────────

BANNER_PROMPTS = {
    "CH1": (
        "Create a YouTube channel art banner for a Korean economics channel. "
        "Wide 16:9 landscape format. "
        "Theme: economics, money, finance — coins, currency symbols ($, ¥, €, ₩), "
        "stock charts, bar graphs, scales of justice. "
        "Color palette: rich golden yellow (#FFD700), deep navy blue, white. "
        "Style: modern clean doodle illustration, hand-drawn feel, flat design. "
        "Doodle icons scattered as background decoration. "
        "Central area should be relatively clean for overlaying text. "
        "No text in the image."
    ),
    "CH2": (
        "Create a YouTube channel art banner for a Korean science channel. "
        "Wide 16:9 landscape format. "
        "Theme: science, experiments — flasks, atoms, DNA helix, microscope, telescope, equations. "
        "Color palette: neon cyan (#00E5FF), dark navy background (#1A1A2E), white. "
        "Style: clean doodle illustration, glowing neon line art on dark background. "
        "Science doodle icons as background elements. "
        "Central area clean for text. No text in the image."
    ),
    "CH3": (
        "Create a YouTube channel art banner for a Korean real estate channel. "
        "Wide 16:9 landscape format. "
        "Theme: real estate, housing — houses, buildings, keys, location pins, blueprints, city skyline. "
        "Color palette: warm orange (#E67E22), sky blue, white, sage green. "
        "Style: cheerful doodle illustration, hand-drawn flat design. "
        "House and city doodle icons as background decoration. "
        "Central area clean for text. No text in the image."
    ),
    "CH4": (
        "Create a YouTube channel art banner for a Korean psychology channel. "
        "Wide 16:9 landscape format. "
        "Theme: psychology, mind — brain illustrations, thought bubbles, eyes, mirrors, spirals, emotions. "
        "Color palette: purple (#9B59B6), lavender, soft violet, white. "
        "Style: dreamy mystical doodle illustration, soft flat design. "
        "Psychology doodle icons as background elements. "
        "Central area clean for text. No text in the image."
    ),
    "CH5": (
        "Create a YouTube channel art banner for a Korean mystery channel. "
        "Wide 16:9 landscape format. "
        "Theme: mystery, enigma — question marks, magnifying glass, keyholes, shadows, eyes, clues. "
        "Color palette: dark navy (#1C2833), charcoal, soft gray, white accents. "
        "Style: moody atmospheric doodle illustration, dark minimal design. "
        "Mystery doodle icons as background decoration. "
        "Central area clean for text. No text in the image."
    ),
    "CH6": (
        "Create a YouTube channel art banner for a Korean history channel. "
        "Wide 16:9 landscape format. "
        "Theme: history, ancient — scrolls, hourglasses, maps, castles, ancient artifacts, timelines. "
        "Color palette: warm brown (#A0522D), parchment beige (#F5F0E0), gold accent. "
        "Style: aged parchment doodle illustration, vintage hand-drawn feel. "
        "Historical doodle icons as background elements. "
        "Central area clean for text. No text in the image."
    ),
    "CH7": (
        "Create a YouTube channel art banner for a Korean war history channel. "
        "Wide 16:9 landscape format. "
        "Theme: war, military strategy — swords, shields, battle maps, flags, compasses, medals. "
        "Color palette: deep crimson red (#C0392B), dark charcoal, khaki, gold. "
        "Style: bold dramatic doodle illustration, strong line art. "
        "Military and war doodle icons as background decoration. "
        "Central area clean for text. No text in the image."
    ),
}

# 10장 다양성을 위한 변형 키워드
VARIATIONS = [
    "centered composition, symmetrical layout",
    "left-weighted composition, elements clustered on left side",
    "right-weighted composition, elements clustered on right side",
    "top-heavy composition, elements concentrated at top",
    "sparse minimal design, few large iconic elements",
    "dense pattern, many small icons repeating across the background",
    "diagonal composition, elements flowing from top-left to bottom-right",
    "corner-focused design, icons in all four corners, clean center",
    "abstract geometric shapes combined with thematic icons",
    "layered depth composition, foreground and background elements",
]


def main():
    client = _make_client()

    print("=== 2단계: 배너 생성 시작 ===\n")

    for ch_id, base_prompt in BANNER_PROMPTS.items():
        logo_path = Path(f"assets/channels/{ch_id}/logo/logo.png")
        output_dir = Path(f"assets/channels/{ch_id}/_candidates/banner")
        output_dir.mkdir(parents=True, exist_ok=True)

        refs = [logo_path] if logo_path.exists() else []
        if not refs:
            print(f"[{ch_id}] 로고 없음 — 스킵")
            continue

        print(f"[{ch_id}] 배너 10장 생성 중...")
        saved_count = 0

        for i, variation in enumerate(VARIATIONS, 1):
            prompt = base_prompt + f" Composition style: {variation}"
            output_path = output_dir / f"variant_{i}.png"
            ok = generate_best_of_n_multi_reference.__wrapped__ if hasattr(generate_best_of_n_multi_reference, '__wrapped__') else None

            from scripts.generate_branding.gemini_image_gen import generate_with_multi_reference
            success = generate_with_multi_reference(refs, prompt, output_path, client=client)
            if success:
                saved_count += 1
                print(f"  [{ch_id}] variant_{i} [OK]")
            else:
                print(f"  [{ch_id}] variant_{i} [FAIL]")

        print(f"[{ch_id}] 완료: {saved_count}/10장\n")

    print("=== 2단계 완료 ===")
    print("저장 위치: assets/channels/CH{N}/_candidates/banner/")


if __name__ == "__main__":
    main()
