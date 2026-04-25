"""배너 10장×7채널 — 스타일 레퍼런스 4장 + 로고 레퍼런스.

사용법:
    python scripts/generate_branding/gen_assets_banner.py
"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.path.insert(0, str(__file__).split("scripts")[0])

from pathlib import Path
from dotenv import load_dotenv
load_dotenv()

import scripts.generate_branding.gemini_image_gen as img_gen
img_gen.MODEL_MULTIMODAL = "gemini-3.1-flash-image-preview"
from scripts.generate_branding.gemini_image_gen import generate_with_multi_reference, _make_client

STYLE_REFS = [
    Path("assets/references/logo_ref_01.png"),
    Path("assets/references/logo_ref_02.png"),
    Path("assets/references/logo_ref_03.png"),
    Path("assets/references/logo_ref_04.png"),
]

CHANNEL_THEMES = {
    "CH1": "economics, money, finance — coins, currency symbols ($,€,¥,₩), stock charts, balance scales, bills",
    "CH2": "science — flasks, atoms, DNA helix, microscope, test tubes, equations, planets",
    "CH3": "real estate — houses, buildings, keys, location pins, blueprints, city skyline",
    "CH4": "psychology — brain, thought bubbles, eyes, mirrors, spirals, emotions, mind",
    "CH5": "mystery — question marks, magnifying glass, keyholes, shadows, clues, fog",
    "CH6": "history — ancient scrolls, hourglasses, maps, castles, artifacts, quill pens",
    "CH7": "war history — swords, shields, battle maps, flags, medals, compass, helmets",
}

VARIATIONS = [
    "centered symmetrical, elements spread evenly across the wide banner",
    "elements clustered on the right side, clean left area",
    "elements clustered on the left side, clean right area",
    "elements decorating the top edge, clean lower area",
    "scattered doodle pattern filling the entire background lightly",
    "diagonal flow of elements from top-left to bottom-right",
    "elements in all four corners, very clean center",
    "large single hero icon centered, smaller icons surrounding it",
    "repeating pattern of small icons across the full banner width",
    "elements layered with foreground and background depth",
]

BASE_PROMPT = (
    "The first four reference images show a Korean YouTube channel logo style: "
    "flat 2D doodle illustration, simple 2px black outline, clean flat colors, hand-drawn kawaii feel. "
    "The LAST reference is the actual channel logo — use its exact color palette and icon themes. "
    "Create a WIDE YouTube channel art BANNER in the EXACT SAME flat doodle style as the first four references. "
    "Channel theme: {theme}. "
    "CRITICAL: Match the flat doodle style exactly — simple outlines, flat colors, no realistic shading, no gradients, no photographic elements. "
    "Wide landscape 16:9 format, doodle icons spread as background decoration. "
    "Clean open area in the {zone} for text overlay. "
    "No text, no channel name in the image. "
    "Composition: {variation}."
)

ZONES = ["center", "left third", "right third", "center", "lower center",
         "left side", "right side", "center", "top center", "center"]


def main():
    client = _make_client()
    print("=== 배너 생성 시작 ===\n")

    for ch_id, theme in CHANNEL_THEMES.items():
        logo_path = Path(f"assets/channels/{ch_id}/logo/logo.png")
        output_dir = Path(f"assets/channels/{ch_id}/_candidates/banner")
        output_dir.mkdir(parents=True, exist_ok=True)
        refs = STYLE_REFS + [logo_path]

        print(f"[{ch_id}] 배너 10장 생성 중...")
        saved = 0
        for i, (variation, zone) in enumerate(zip(VARIATIONS, ZONES), 1):
            prompt = BASE_PROMPT.format(theme=theme, zone=zone, variation=variation)
            ok = generate_with_multi_reference(refs, prompt, output_dir / f"variant_{i}.png", client=client)
            if ok:
                saved += 1
                print(f"  [{ch_id}] variant_{i} [OK]")
            else:
                print(f"  [{ch_id}] variant_{i} [FAIL]")
        print(f"[{ch_id}] 완료: {saved}/10장\n")

    print("=== 배너 생성 완료 ===")
    print("저장 위치: assets/channels/CH{N}/_candidates/banner/")


if __name__ == "__main__":
    main()
