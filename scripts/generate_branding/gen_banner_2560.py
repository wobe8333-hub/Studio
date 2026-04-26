"""확정된 7채널 배너를 2560×1440으로 재생성.

각 채널의 확정 variant 번호에 해당하는 프롬프트로만 생성 후,
PIL로 정확히 2560×1440으로 파이널라이즈한다.

사용법:
    python scripts/generate_branding/gen_banner_2560.py
    python scripts/generate_branding/gen_banner_2560.py --channels CH1 CH3

저장 위치: assets/channels/CH{N}/banner/banner.png (기존 파일 교체)
"""
import sys
import io
import argparse
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from dotenv import load_dotenv
load_dotenv()

from PIL import Image
from loguru import logger

# ─── 유튜브 최소 허용 크기 (이 이하면 경고) ──────────────────────────────────
YOUTUBE_MIN_W, YOUTUBE_MIN_H = 2048, 1152

import scripts.generate_branding.gemini_image_gen as img_gen
img_gen.MODEL_MULTIMODAL = "gemini-3.1-flash-image-preview"

from scripts.generate_branding.gemini_image_gen import generate_with_multi_reference, _make_client
from google.genai import types

# ─── 유튜브 배너 안전 영역 ────────────────────────────────────────────────────
# 모든 디바이스에서 보이는 안전 영역 (가로 중앙 1235×338)
SAFE_ZONE_HINT = (
    "YOUTUBE SAFE ZONE: This banner displays at 2560×1440 on TV, "
    "cropped to 2560×423 on desktop, and only the center 1235×338 is visible on mobile. "
    "Place the channel name and key focal icon strictly within the center 1235×338 area. "
    "Keep outer edges (left/right beyond 660px from center, top/bottom beyond 169px from center) "
    "decorative only — no critical text or logos there."
)

# ─── 스타일 레퍼런스 ──────────────────────────────────────────────────────────
STYLE_REFS = [
    Path("assets/references/logo_ref_01.png"),
    Path("assets/references/logo_ref_02.png"),
    Path("assets/references/logo_ref_03.png"),
    Path("assets/references/logo_ref_04.png"),
]

# ─── 채널 테마 ────────────────────────────────────────────────────────────────
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

# ─── 확정된 variant 번호별 컴포지션 설명 (1-based 인덱스) ──────────────────────
ALL_VARIATIONS = [
    "centered symmetrical, elements spread evenly across the wide banner",           # 1
    "elements clustered on the right side, clean left area",                         # 2
    "elements clustered on the left side, clean right area",                         # 3
    "elements decorating the top edge, clean lower area",                            # 4
    "scattered doodle pattern filling the entire background lightly",                # 5
    "diagonal flow of elements from top-left to bottom-right",                       # 6
    "elements in all four corners, very clean center",                               # 7
    "large single hero icon centered smaller icons surrounding it",                  # 8
    "repeating pattern of small icons across the full banner width",                 # 9
    "elements layered with foreground and background depth",                         # 10
    "warm gradient background with doodle icons floating lightly",                   # 11
    "dark moody background with glowing doodle elements",                            # 12
    "pastel soft background with large playful doodle icons",                        # 13
    "grid pattern background with channel theme icons at intersections",             # 14
    "hand-drawn border frame with dense doodle icons inside",                        # 15
    "asymmetric balance — large icon left, small icons scattered right",             # 16
    "top banner strip of icons, clean white space below",                            # 17
    "circular arrangement of icons radiating from center",                           # 18
    "overlapping large transparent icons as background texture",                     # 19
    "vertical rhythm — three columns of stacked doodle icons",                       # 20
]

# ─── 채널별 확정 variant ──────────────────────────────────────────────────────
CONFIRMED_VARIANTS = {
    "CH1": 8,
    "CH2": 12,
    "CH3": 5,
    "CH4": 12,
    "CH5": 6,
    "CH6": 14,
    "CH7": 13,
}

BASE_PROMPT = (
    "The first four reference images show a Korean YouTube channel logo style: "
    "flat 2D doodle illustration, simple 2px black outline, clean flat colors, hand-drawn kawaii feel. "
    "The LAST reference is the actual channel logo — use its exact color palette and icon themes. "
    "Create a WIDE YouTube channel art BANNER in the EXACT SAME flat doodle style as the first four references. "
    "Channel theme: {theme}. "
    "CRITICAL: Match the flat doodle style exactly — simple outlines, flat colors, no realistic shading, no gradients, no photographic elements. "
    "Wide landscape 16:9 format, doodle icons spread as background decoration. "
    "CHANNEL NAME: Place the Korean text '{name}' in large stylized doodle lettering at the CENTER of the banner. "
    "Text style: {text_colors}. The text should look hand-drawn and match the flat doodle illustration style. "
    "Make the channel name the visual focal point — large, clear, and prominent. "
    "Composition: {variation}. "
    "{safe_zone}"
)


def check_dimensions(img_path: Path) -> tuple[int, int]:
    """생성된 이미지 실제 해상도를 반환하고 YouTube 최소 규격을 검증한다."""
    img = Image.open(img_path)
    w, h = img.size
    if w < YOUTUBE_MIN_W or h < YOUTUBE_MIN_H:
        logger.warning(f"  [주의] {w}×{h} — YouTube 최소 크기({YOUTUBE_MIN_W}×{YOUTUBE_MIN_H}) 미달")
    else:
        logger.info(f"  실제 해상도: {w}×{h} ✓")
    return w, h


def main(channels: list[str] | None = None) -> None:
    client = _make_client()
    target_channels = channels or list(CONFIRMED_VARIANTS.keys())

    # 2K 이미지 설정 — Gemini가 최대한 고해상도로 생성
    img_cfg = types.ImageConfig(
        aspect_ratio="16:9",
        image_size="2K",
    )

    print(f"=== 확정 배너 2560×1440 재생성 ({len(target_channels)}채널) ===\n")

    for ch_id in target_channels:
        if ch_id not in CONFIRMED_VARIANTS:
            logger.warning(f"[{ch_id}] 확정 variant 없음 — 건너뜀")
            continue

        info = CHANNEL_THEMES[ch_id]
        variant_no = CONFIRMED_VARIANTS[ch_id]
        variation_desc = ALL_VARIATIONS[variant_no - 1]

        logo_path = Path(f"assets/channels/{ch_id}/logo/logo.png")
        output_path = Path(f"assets/channels/{ch_id}/banner/banner.png")
        output_path.parent.mkdir(parents=True, exist_ok=True)

        refs = STYLE_REFS + [logo_path]

        prompt = BASE_PROMPT.format(
            theme=info["theme"],
            name=info["name"],
            text_colors=info["text_colors"],
            variation=variation_desc,
            safe_zone=SAFE_ZONE_HINT,
        )

        print(f"[{ch_id}] '{info['name']}' variant_{variant_no} 생성 중 (16:9 2K)...")

        ok = generate_with_multi_reference(
            refs,
            prompt,
            output_path,
            client=client,
            image_config=img_cfg,
        )

        if ok:
            w, h = check_dimensions(output_path)
            print(f"  [OK] {output_path} ({w}×{h})")
        else:
            logger.error(f"  [FAIL] {ch_id} 배너 생성 실패")

    print("\n=== 완료 ===")
    print("저장 위치: assets/channels/CH{N}/banner/banner.png")
    print("YouTube Studio → 채널 맞춤설정 → 브랜딩 → 배너 이미지로 업로드하세요.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="확정 배너 2560×1440 재생성")
    parser.add_argument(
        "--channels",
        nargs="+",
        choices=list(CONFIRMED_VARIANTS.keys()),
        help="특정 채널만 생성 (기본: 전체 7채널)",
    )
    args = parser.parse_args()
    main(args.channels)
