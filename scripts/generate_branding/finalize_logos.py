"""선택된 로고만 남기고 텍스트 색상 개선 재생성.

사용법:
    python scripts/generate_branding/finalize_logos.py
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

# ─── 4장 스타일 레퍼런스 ──────────────────────────────────────────────────────
STYLE_REFS = [
    Path("assets/references/logo_ref_01.png"),
    Path("assets/references/logo_ref_02.png"),
    Path("assets/references/logo_ref_03.png"),
    Path("assets/references/logo_ref_04.png"),
]

# ─── 채널별 선택 번호 + 텍스트 색상 ─────────────────────────────────────────
SELECTED = {
    "CH1": {
        "nums": [8, 11, 24, 43],
        "kr": "머니그래픽", "en": "MoneyGraphic",
        "text_color": "deep navy blue",
        "theme": "economics, money, finance — coins, charts, bills, investment",
    },
    "CH2": {
        "nums": [1, 11, 27],
        "kr": "가설낙서", "en": "HypothesisDoodle",
        "text_color": "dark teal #006064",
        "theme": "science — flask, atom, microscope, DNA, experiment, discovery",
    },
    "CH3": {
        "nums": [4, 6, 14, 15],
        "kr": "홈팔레트", "en": "HomePalette",
        "text_color": "dark forest green",
        "theme": "real estate — house, key, city buildings, blueprint, neighborhood",
    },
    "CH4": {
        "nums": [1, 5, 7, 29],
        "kr": "오묘한심리", "en": "MysticMind",
        "text_color": "deep purple",
        "theme": "psychology — brain, thought bubbles, mirror, emotions, mind",
    },
    "CH5": {
        "nums": [6, 9],
        "kr": "검은물음표", "en": "BlackQuestionMark",
        "text_color": "near black dark navy",
        "theme": "mystery — magnifying glass, question mark, shadow, clue, enigma",
    },
    "CH6": {
        "nums": [1, 6, 45],
        "kr": "오래된두루마리", "en": "AncientScroll",
        "text_color": "dark warm brown",
        "theme": "history — ancient scroll, artifacts, hourglass, timeline, ruins",
    },
    "CH7": {
        "nums": [4, 8],
        "kr": "워메이징", "en": "WarMazing",
        "text_color": "dark burgundy red",
        "theme": "war history — strategy map, shield, sword, battle flag, compass",
    },
}


def delete_unselected(ch_id: str, selected_nums: list[int]):
    """선택되지 않은 파일 삭제."""
    folder = Path(f"assets/channels/{ch_id}/_candidates/logo_final")
    deleted = 0
    for f in folder.glob("variant_*.png"):
        num = int(f.stem.split("_")[1])
        if num not in selected_nums:
            f.unlink()
            deleted += 1
    print(f"  [{ch_id}] {deleted}장 삭제 완료, {len(selected_nums)}장 유지")


def regenerate_with_color(ch_id: str, info: dict, client):
    """선택 이미지를 레퍼런스로 텍스트 색상 개선 재생성."""
    folder = Path(f"assets/channels/{ch_id}/_candidates/logo_final")
    output_dir = Path(f"assets/channels/{ch_id}/_candidates/logo_color")
    output_dir.mkdir(parents=True, exist_ok=True)

    for num in info["nums"]:
        selected_img = folder / f"variant_{num}.png"
        if not selected_img.exists():
            print(f"  [{ch_id}] variant_{num}.png 없음 — 스킵")
            continue

        # 스타일 레퍼런스 4장 + 선택 이미지 1장
        refs = STYLE_REFS + [selected_img]

        prompt = (
            f"Recreate a logo very similar to the LAST reference image (same icon concept and circular badge style). "
            f"IMPORTANT TEXT STYLING: bold Korean '{info['kr']}' text below the icon, "
            f"smaller '{info['en']}' subtitle beneath it. "
            f"Text color MUST match the dominant colors of the icon in the last reference image "
            f"(e.g. if icon is gold, use dark gold or navy; if icon is teal, use dark teal). "
            f"Keep the circular white badge format and same icon theme: {info['theme']}. "
            f"Do NOT copy text from other reference images."
        )

        output_path = output_dir / f"variant_{num}.png"
        print(f"  [{ch_id}] variant_{num} 재생성 중...")
        ok = generate_with_multi_reference(refs, prompt, output_path, client=client)
        if ok:
            print(f"  [{ch_id}] variant_{num} [OK] 저장")
        else:
            print(f"  [{ch_id}] variant_{num} [FAIL] 실패")


def main():
    client = _make_client()

    print("=== Step 2: 텍스트 색상 개선 재생성 ===")
    for ch_id, info in SELECTED.items():
        print(f"\n[{ch_id}] {len(info['nums'])}장 재생성...")
        regenerate_with_color(ch_id, info, client)

    print("\n=== 완료 ===")
    print("저장 위치: assets/channels/CH{N}/_candidates/logo_color/")


if __name__ == "__main__":
    main()
