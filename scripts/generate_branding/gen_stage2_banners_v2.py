"""2단계 v2: 배너 배경 Gemini 생성 + 로고 Pillow 합성 (10장×7채널).

사용법:
    python scripts/generate_branding/gen_stage2_banners_v2.py
"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.path.insert(0, str(__file__).split("scripts")[0])

from pathlib import Path
from dotenv import load_dotenv
load_dotenv()

from PIL import Image

import scripts.generate_branding.gemini_image_gen as img_gen
img_gen.MODEL_MULTIMODAL = "gemini-3.1-flash-image-preview"

from scripts.generate_branding.gemini_image_gen import generate_with_multi_reference, _make_client

# ─── 배너 규격 ─────────────────────────────────────────────────────────────────
BANNER_W, BANNER_H = 2560, 1440
LOGO_H = 320  # 로고 높이 (px)

# ─── 로고 10가지 배치 위치 ────────────────────────────────────────────────────
# YouTube safe zone: 1546×423 (가로 중앙, 세로 중앙)
# safe_x = (2560 - 1546) // 2 = 507, safe_y = (1440 - 423) // 2 = 508
LOGO_POSITIONS = [
    "center",           # 1: 정중앙
    "top-center",       # 2: 상단 중앙
    "center-left",      # 3: 좌측 중앙
    "center-right",     # 4: 우측 중앙
    "bottom-center",    # 5: 하단 중앙
    "top-left",         # 6: 좌상단
    "top-right",        # 7: 우상단
    "bottom-left",      # 8: 좌하단
    "bottom-right",     # 9: 우하단
    "center",           # 10: 정중앙 (배경 다름)
]

# ─── 채널별 배경 프롬프트 ─────────────────────────────────────────────────────
BANNER_PROMPTS = {
    "CH1": (
        "Wide landscape banner background for a Korean economics YouTube channel. "
        "Theme: money, finance — coins, currency symbols ($,€,¥,₩), stock charts, bills. "
        "Color palette: rich golden yellow, deep navy blue, white. "
        "Style: modern doodle illustration, flat design. "
        "Leave a clean open area in the {zone} for logo placement. "
        "No text, no logo in the image — background decoration only."
    ),
    "CH2": (
        "Wide landscape banner background for a Korean science YouTube channel. "
        "Theme: science — flasks, atoms, DNA helix, microscope, equations. "
        "Color palette: neon cyan (#00E5FF), dark navy (#1A1A2E), white. "
        "Style: glowing neon doodle on dark background. "
        "Leave a clean open area in the {zone} for logo placement. "
        "No text, no logo in the image — background decoration only."
    ),
    "CH3": (
        "Wide landscape banner background for a Korean real estate YouTube channel. "
        "Theme: housing — houses, buildings, keys, city skyline, blueprints. "
        "Color palette: warm orange, sky blue, white, sage green. "
        "Style: cheerful doodle illustration, flat design. "
        "Leave a clean open area in the {zone} for logo placement. "
        "No text, no logo in the image — background decoration only."
    ),
    "CH4": (
        "Wide landscape banner background for a Korean psychology YouTube channel. "
        "Theme: mind — brain, thought bubbles, eyes, mirrors, spirals, emotions. "
        "Color palette: purple (#9B59B6), lavender, soft violet, white. "
        "Style: dreamy mystical doodle illustration. "
        "Leave a clean open area in the {zone} for logo placement. "
        "No text, no logo in the image — background decoration only."
    ),
    "CH5": (
        "Wide landscape banner background for a Korean mystery YouTube channel. "
        "Theme: enigma — question marks, magnifying glass, keyholes, shadows. "
        "Color palette: dark navy, charcoal, soft gray, white accents. "
        "Style: moody atmospheric doodle. "
        "Leave a clean open area in the {zone} for logo placement. "
        "No text, no logo in the image — background decoration only."
    ),
    "CH6": (
        "Wide landscape banner background for a Korean history YouTube channel. "
        "Theme: ancient history — scrolls, hourglasses, maps, artifacts, castles. "
        "Color palette: warm brown, parchment beige, gold accent. "
        "Style: aged parchment vintage doodle illustration. "
        "Leave a clean open area in the {zone} for logo placement. "
        "No text, no logo in the image — background decoration only."
    ),
    "CH7": (
        "Wide landscape banner background for a Korean war history YouTube channel. "
        "Theme: military — swords, shields, battle maps, flags, medals, compass. "
        "Color palette: deep crimson red, dark charcoal, khaki, gold. "
        "Style: bold dramatic doodle illustration. "
        "Leave a clean open area in the {zone} for logo placement. "
        "No text, no logo in the image — background decoration only."
    ),
}

ZONE_HINTS = [
    "center",
    "top center",
    "left side",
    "right side",
    "bottom center",
    "top left corner",
    "top right corner",
    "bottom left",
    "bottom right",
    "center",
]

VARIATIONS = [
    "centered symmetrical layout",
    "dense top, sparse bottom",
    "elements clustered on right side",
    "elements clustered on left side",
    "scattered pattern across entire background",
    "diagonal flow top-left to bottom-right",
    "corner-focused, clean center",
    "layered depth, large background + small foreground icons",
    "minimal sparse design, few large elements",
    "abstract geometric shapes with thematic icons",
]


def calc_logo_pos(position: str, logo_w: int, logo_h: int) -> tuple[int, int]:
    pad = 100
    cx = (BANNER_W - logo_w) // 2
    cy = (BANNER_H - logo_h) // 2
    positions = {
        "center":        (cx, cy),
        "top-center":    (cx, pad),
        "center-left":   (pad, cy),
        "center-right":  (BANNER_W - logo_w - pad, cy),
        "bottom-center": (cx, BANNER_H - logo_h - pad),
        "top-left":      (pad, pad),
        "top-right":     (BANNER_W - logo_w - pad, pad),
        "bottom-left":   (pad, BANNER_H - logo_h - pad),
        "bottom-right":  (BANNER_W - logo_w - pad, BANNER_H - logo_h - pad),
    }
    return positions.get(position, (cx, cy))


def composite_logo(bg_path: Path, logo_path: Path, position: str) -> Image.Image:
    bg = Image.open(bg_path).convert("RGBA").resize((BANNER_W, BANNER_H), Image.LANCZOS)
    logo = Image.open(logo_path).convert("RGBA")

    # 로고 높이 기준 비율 유지 리사이즈
    ratio = LOGO_H / logo.height
    logo_w = int(logo.width * ratio)
    logo = logo.resize((logo_w, LOGO_H), Image.LANCZOS)

    x, y = calc_logo_pos(position, logo_w, LOGO_H)
    bg.paste(logo, (x, y), logo)
    return bg.convert("RGB")


def main():
    client = _make_client()
    tmp_dir = Path("assets/_tmp_banner_bg")
    tmp_dir.mkdir(parents=True, exist_ok=True)

    print("=== 2단계 v2: 배너 + 로고 합성 생성 시작 ===\n")

    for ch_id, base_prompt in BANNER_PROMPTS.items():
        logo_path = Path(f"assets/channels/{ch_id}/logo/logo.png")
        output_dir = Path(f"assets/channels/{ch_id}/_candidates/banner_v2")
        output_dir.mkdir(parents=True, exist_ok=True)

        if not logo_path.exists():
            print(f"[{ch_id}] 로고 없음 — 스킵")
            continue

        print(f"[{ch_id}] 배너 10장 생성 중...")
        saved_count = 0

        for i in range(1, 11):
            zone = ZONE_HINTS[i - 1]
            variation = VARIATIONS[i - 1]
            prompt = base_prompt.format(zone=zone) + f" Layout: {variation}."
            position = LOGO_POSITIONS[i - 1]

            # 배경 임시 저장
            tmp_bg = tmp_dir / f"{ch_id}_bg_{i}.png"
            ok = generate_with_multi_reference([logo_path], prompt, tmp_bg, client=client)

            if ok and tmp_bg.exists():
                # 로고 합성
                final = composite_logo(tmp_bg, logo_path, position)
                out_path = output_dir / f"variant_{i}.png"
                final.save(out_path, "PNG")
                tmp_bg.unlink()
                saved_count += 1
                print(f"  [{ch_id}] variant_{i} [OK] (로고 위치: {position})")
            else:
                print(f"  [{ch_id}] variant_{i} [FAIL]")

        print(f"[{ch_id}] 완료: {saved_count}/10장\n")

    # 임시 폴더 정리
    if tmp_dir.exists():
        import shutil
        shutil.rmtree(tmp_dir, ignore_errors=True)

    print("=== 2단계 v2 완료 ===")
    print("저장 위치: assets/channels/CH{N}/_candidates/banner_v2/")


if __name__ == "__main__":
    main()
