"""최종 로고 선택 + 수정사항 반영 재생성.

사용법:
    python scripts/generate_branding/finalize_logos_v2.py
"""
import sys
import io
import shutil
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.path.insert(0, str(__file__).split("scripts")[0])

from pathlib import Path
from dotenv import load_dotenv
load_dotenv()

import scripts.generate_branding.gemini_image_gen as img_gen
img_gen.MODEL_MULTIMODAL = "gemini-3.1-flash-image-preview"

from scripts.generate_branding.gemini_image_gen import (
    generate_with_multi_reference,
    _make_client,
)

# ─── 스타일 레퍼런스 ──────────────────────────────────────────────────────────
STYLE_REFS = [
    Path("assets/references/logo_ref_01.png"),
    Path("assets/references/logo_ref_02.png"),
    Path("assets/references/logo_ref_03.png"),
    Path("assets/references/logo_ref_04.png"),
]

COLOR_DIR = Path("assets/channels/{ch}/_candidates/logo_color")
OUTPUT_DIR = Path("assets/channels/{ch}/logo")


def get_color_path(ch: str, num: int) -> Path:
    return Path(f"assets/channels/{ch}/_candidates/logo_color/variant_{num}.png")


def save_final(ch: str, img_bytes: bytes) -> Path:
    out_dir = Path(f"assets/channels/{ch}/logo")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "logo.png"
    out_path.write_bytes(img_bytes)
    return out_path


def ch1_hybrid(client):
    """CH1: 11+24 하이브리드, 머니그래픽/MoneyGraphic 텍스트 황금색."""
    refs = STYLE_REFS + [
        get_color_path("CH1", 11),
        get_color_path("CH1", 24),
    ]
    prompt = (
        "Blend the TWO LAST reference images into ONE new logo. "
        "Take icon elements and composition inspiration from BOTH of the last two images "
        "to create a creative hybrid design. "
        "Keep the circular white badge format with a single central doodle icon. "
        "Economics/money/finance theme: coins, charts, bills, investment symbols. "
        "TEXT STYLING: bold Korean text '머니그래픽' in RICH GOLDEN color (#FFD700 / #DAA520), "
        "smaller 'MoneyGraphic' subtitle also in GOLDEN color. "
        "Gold metallic text effect. White badge background."
    )
    out_dir = Path("assets/channels/CH1/logo")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "logo.png"
    print("[CH1] 11+24 하이브리드 황금색 텍스트 생성 중...")
    ok = generate_with_multi_reference(refs, prompt, out_path, client=client)
    if ok:
        print(f"[CH1] [OK] {out_path}")
    else:
        print("[CH1] [FAIL]")


def ch2_no_en(client):
    """CH2: 27번, 영어 채널명 삭제."""
    refs = STYLE_REFS + [get_color_path("CH2", 27)]
    prompt = (
        "Recreate this logo very similar to the LAST reference image. "
        "Keep the circular white badge and the central science doodle icon (flask, atom, DNA, microscope theme). "
        "TEXT: bold Korean '가설낙서' text below the icon. "
        "DO NOT include any English text — remove the English subtitle completely. "
        "Only Korean text '가설낙서' is shown. "
        "Maintain the dark teal text color from the reference. Science/experiment theme."
    )
    out_dir = Path("assets/channels/CH2/logo")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "logo.png"
    print("[CH2] 27번 영어 제거 생성 중...")
    ok = generate_with_multi_reference(refs, prompt, out_path, client=client)
    if ok:
        print(f"[CH2] [OK] {out_path}")
    else:
        print("[CH2] [FAIL]")


def ch3_paint_text(client):
    """CH3: 15번, 글씨 전체 물감 형태/색깔."""
    refs = STYLE_REFS + [get_color_path("CH3", 15)]
    prompt = (
        "Recreate this logo very similar to the LAST reference image. "
        "Keep the circular white badge and central real estate doodle icon (house, key, building). "
        "TEXT STYLING: bold Korean '홈팔레트' text and 'HomePalette' subtitle below the icon "
        "must look like they were PAINTED WITH COLORFUL PAINT — "
        "brushstroke-style lettering with vivid paint colors (mix of red, blue, yellow, green, orange "
        "like a painter's palette). Each letter can have a different paint color. "
        "Give the text a hand-painted, artistic brushstroke appearance. "
        "Real estate / house / neighborhood theme."
    )
    out_dir = Path("assets/channels/CH3/logo")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "logo.png"
    print("[CH3] 15번 물감 텍스트 생성 중...")
    ok = generate_with_multi_reference(refs, prompt, out_path, client=client)
    if ok:
        print(f"[CH3] [OK] {out_path}")
    else:
        print("[CH3] [FAIL]")


def ch4_mystic_color(client):
    """CH4: 1번, 그림+글씨 오묘한 색깔로."""
    refs = STYLE_REFS + [get_color_path("CH4", 1)]
    prompt = (
        "Recreate this logo similar to the LAST reference image. "
        "Change ALL COLORS — both the central icon and text — to mysterious, mystical, enigmatic tones: "
        "deep purple, violet, indigo, soft lavender, cosmic iridescent colors, aurora-like hues. "
        "The icon should have a dreamy, otherworldly color palette (purple/violet/indigo gradient). "
        "TEXT: bold Korean '오묘한심리' in deep violet/purple, smaller 'MysticMind' in soft lavender. "
        "Keep the circular white badge format. Psychology / mind / brain / emotions theme "
        "with a mystical, enigmatic atmosphere."
    )
    out_dir = Path("assets/channels/CH4/logo")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "logo.png"
    print("[CH4] 1번 오묘한 색상 생성 중...")
    ok = generate_with_multi_reference(refs, prompt, out_path, client=client)
    if ok:
        print(f"[CH4] [OK] {out_path}")
    else:
        print("[CH4] [FAIL]")


def ch5_no_en_white_bg(client):
    """CH5: 9번, 영어 삭제 + 흰 배경."""
    refs = STYLE_REFS + [get_color_path("CH5", 9)]
    prompt = (
        "Recreate this logo very similar to the LAST reference image. "
        "Keep the circular badge with PURE WHITE background (no gray, no off-white — pure white). "
        "Keep the central mystery doodle icon (question mark, magnifying glass, shadow, keyhole). "
        "TEXT: bold Korean '검은물음표' text only below the icon. "
        "DO NOT include any English text — remove the English subtitle completely. "
        "Only Korean text '검은물음표' is shown. "
        "Dark/near-black text color. Pure white badge background. Mystery/enigma theme."
    )
    out_dir = Path("assets/channels/CH5/logo")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "logo.png"
    print("[CH5] 9번 영어 제거 + 흰 배경 생성 중...")
    ok = generate_with_multi_reference(refs, prompt, out_path, client=client)
    if ok:
        print(f"[CH5] [OK] {out_path}")
    else:
        print("[CH5] [FAIL]")


def ch6_copy():
    """CH6: 6번 수정 없이 복사."""
    src = get_color_path("CH6", 6)
    out_dir = Path("assets/channels/CH6/logo")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "logo.png"
    shutil.copy2(src, out_path)
    print(f"[CH6] [OK] 복사 완료 {out_path}")


def ch7_military_text(client):
    """CH7: 4번, 글씨 전체 군대 색깔로."""
    refs = STYLE_REFS + [get_color_path("CH7", 4)]
    prompt = (
        "Recreate this logo very similar to the LAST reference image. "
        "Keep the circular white badge and the central war history doodle icon "
        "(strategy map, shield, sword, battle flag, compass). "
        "TEXT STYLING: bold Korean '워메이징' text and 'WarMazing' subtitle "
        "must be in MILITARY / ARMY COLORS — olive drab (#4B5320), khaki (#C3B091), "
        "dark military green (#2D3A1E), camouflage tones. "
        "Give both Korean and English text a rugged military feel. "
        "War history / battle strategy theme."
    )
    out_dir = Path("assets/channels/CH7/logo")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "logo.png"
    print("[CH7] 4번 군대 색상 텍스트 생성 중...")
    ok = generate_with_multi_reference(refs, prompt, out_path, client=client)
    if ok:
        print(f"[CH7] [OK] {out_path}")
    else:
        print("[CH7] [FAIL]")


def main():
    client = _make_client()

    print("=== 최종 로고 생성 (수정사항 반영) ===\n")

    # CH6는 API 불필요 — 먼저 처리
    ch6_copy()

    # 나머지 6채널 순서대로 생성
    ch1_hybrid(client)
    ch2_no_en(client)
    ch3_paint_text(client)
    ch4_mystic_color(client)
    ch5_no_en_white_bg(client)
    ch7_military_text(client)

    print("\n=== 완료 ===")
    print("저장 위치: assets/channels/CH{N}/logo/logo.png")


if __name__ == "__main__":
    main()
