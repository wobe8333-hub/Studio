"""배너 20장×7채널 — 중앙에 한글 채널명 포함, 색상은 배너 팔레트와 조화.

사용법:
    python scripts/generate_branding/gen_assets_banner_named.py
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
    "CH1": {
        "theme": "economics, money, finance — coins, currency symbols ($,€,¥,₩), stock charts, balance scales, bills",
        "name": "머니그래픽",
        "main_color": "#F4C420",
        "text_colors": "golden yellow (#F4C420) outline with dark navy (#333333) shadow — bold and prominent",
    },
    "CH2": {
        "theme": "science — flasks, atoms, DNA helix, microscope, test tubes, equations, planets",
        "name": "가설낙서",
        "main_color": "#00E5FF",
        "text_colors": "bright cyan (#00E5FF) with dark navy (#1A1A2E) shadow — glowing effect",
    },
    "CH3": {
        "theme": "real estate — houses, buildings, keys, location pins, blueprints, city skyline",
        "name": "홈팔레트",
        "main_color": "#E67E22",
        "text_colors": "warm orange (#E67E22) with white shadow — cheerful and bold",
    },
    "CH4": {
        "theme": "psychology — brain, thought bubbles, eyes, mirrors, spirals, emotions, mind",
        "name": "오묘한심리",
        "main_color": "#9B59B6",
        "text_colors": "purple (#9B59B6) with lavender shadow — mystical and dreamy",
    },
    "CH5": {
        "theme": "mystery — question marks, magnifying glass, keyholes, shadows, clues, fog",
        "name": "검은물음표",
        "main_color": "#F0F0F0",
        "text_colors": "soft white (#F0F0F0) with dark charcoal (#1C2833) shadow — moody and dramatic",
    },
    "CH6": {
        "theme": "history — ancient scrolls, hourglasses, maps, castles, artifacts, quill pens",
        "name": "오래된두루마리",
        "main_color": "#A0522D",
        "text_colors": "warm brown (#A0522D) with parchment beige (#F5F0E0) shadow — vintage and aged",
    },
    "CH7": {
        "theme": "war history — swords, shields, battle maps, flags, medals, compass, helmets",
        "name": "워메이징",
        "main_color": "#C0392B",
        "text_colors": "deep crimson (#C0392B) with khaki (#8B7355) shadow — bold military style",
    },
}

VARIATIONS_1_10 = [
    "centered symmetrical, elements spread evenly across the wide banner",
    "elements clustered on the right side, clean left area",
    "elements clustered on the left side, clean right area",
    "elements decorating the top edge, clean lower area",
    "scattered doodle pattern filling the entire background lightly",
    "diagonal flow of elements from top-left to bottom-right",
    "elements in all four corners, very clean center",
    "large single hero icon centered smaller icons surrounding it",
    "repeating pattern of small icons across the full banner width",
    "elements layered with foreground and background depth",
]

VARIATIONS_11_20 = [
    "warm gradient background with doodle icons floating lightly",
    "dark moody background with glowing doodle elements",
    "pastel soft background with large playful doodle icons",
    "grid pattern background with channel theme icons at intersections",
    "hand-drawn border frame with dense doodle icons inside",
    "asymmetric balance — large icon left, small icons scattered right",
    "top banner strip of icons, clean white space below",
    "circular arrangement of icons radiating from center",
    "overlapping large transparent icons as background texture",
    "vertical rhythm — three columns of stacked doodle icons",
]

BASE_PROMPT = (
    "The first four reference images show a Korean YouTube channel logo style: "
    "flat 2D doodle illustration, simple 2px black outline, clean flat colors, hand-drawn kawaii feel. "
    "The LAST reference is the actual channel logo — use its exact color palette and icon themes. "
    "Create a YouTube channel art banner (2560×1440, 16:9) "
    "in the EXACT SAME flat doodle style as the first four references. "
    "CRITICAL: Match the flat doodle style exactly — simple outlines, flat colors, no realistic shading, no gradients, no photographic elements. "
    "Channel theme: {theme}. "
    "YOUTUBE SAFE ZONE — this banner is displayed differently per device: "
    "mobile users see ONLY the center horizontal strip (center 48% width × center 24% height), "
    "desktop users see full width but only the center 423px height, "
    "TV users see the full 2560×1440. "
    "CHANNEL NAME: Place the Korean text '{name}' in large stylized doodle lettering "
    "at the CENTER of the banner so it is visible on ALL devices including mobile. "
    "Text style: {text_colors}. The text should look hand-drawn and match the flat doodle illustration style. "
    "Make the channel name the visual focal point — large, clear, prominent, and unobstructed. "
    "Spread doodle icons across the full banner as background decoration, "
    "keeping the center text area clean and uncluttered. "
    "Composition: {variation}."
)


def main():
    client = _make_client()
    print("=== 배너 생성 (채널명 포함, variant_1~20) ===\n")

    all_variations = VARIATIONS_1_10 + VARIATIONS_11_20

    for ch_id, info in CHANNEL_THEMES.items():
        logo_path = Path(f"assets/channels/{ch_id}/logo/logo.png")
        output_dir = Path(f"assets/channels/{ch_id}/_candidates/banner_named")
        output_dir.mkdir(parents=True, exist_ok=True)
        refs = STYLE_REFS + [logo_path]

        print(f"[{ch_id}] '{info['name']}' 배너 20장 생성 중...")
        saved = 0

        for i, variation in enumerate(all_variations, 1):
            out_path = output_dir / f"variant_{i}.png"
            if out_path.exists():
                print(f"  [{ch_id}] variant_{i} [SKIP]")
                saved += 1
                continue

            prompt = BASE_PROMPT.format(
                theme=info["theme"],
                name=info["name"],
                text_colors=info["text_colors"],
                variation=variation,
            )
            ok = generate_with_multi_reference(refs, prompt, out_path, client=client)
            if ok:
                saved += 1
                print(f"  [{ch_id}] variant_{i} [OK]")
            else:
                print(f"  [{ch_id}] variant_{i} [FAIL]")

        print(f"[{ch_id}] 완료: {saved}/20장\n")

    print("=== 배너 생성 완료 ===")
    print("저장 위치: assets/channels/CH{N}/_candidates/banner_named/")


if __name__ == "__main__":
    main()
