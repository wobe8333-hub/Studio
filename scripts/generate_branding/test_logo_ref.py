"""레퍼런스 이미지 기반 로고 스타일 테스트.

사용법:
    python scripts/generate_branding/test_logo_ref.py
"""
import sys
import os
sys.path.insert(0, str(__file__).split("scripts")[0])

from pathlib import Path
from dotenv import load_dotenv
load_dotenv()

from scripts.generate_branding.gemini_image_gen import (
    generate_best_of_n_with_reference,
    _make_client,
)

# Flash 모델로 테스트 (쿼터 제한 없음)
import scripts.generate_branding.gemini_image_gen as img_gen
img_gen.MODEL_MULTIMODAL = "gemini-3.1-flash-image-preview"

from scripts.generate_branding.gemini_image_gen import generate_best_of_n_multi_reference

# 4장 레퍼런스 경로
REF_IMAGES = [
    Path("assets/references/logo_ref_01.png"),
    Path("assets/references/logo_ref_02.png"),
    Path("assets/references/logo_ref_03.png"),
    Path("assets/references/logo_ref_04.png"),
]

# ─── 채널별 프롬프트 ───────────────────────────────────────────────────────────
_BASE = (
    "These reference images show a Korean YouTube channel logo style. "
    "Create a NEW logo variation following the SAME pattern: "
    "circular white badge, single large creative central doodle icon (unique concept), "
    "bold Korean '{kr}' text below, smaller '{en}' subtitle. "
    "Icon theme: {theme}. "
    "Be creative with a completely different icon concept each time. "
    "Do NOT copy any icon from the references."
)

CHANNEL_PROMPTS = {
    "CH1": _BASE.format(
        kr="머니그래픽", en="MoneyGraphic",
        theme="economics, money, finance — coins, charts, bills, investment",
    ),
    "CH2": _BASE.format(
        kr="가설낙서", en="HypothesisDoodle",
        theme="science — flask, atom, microscope, DNA, experiment, discovery",
    ),
    "CH3": _BASE.format(
        kr="홈팔레트", en="HomePalette",
        theme="real estate — house, key, city buildings, blueprint, neighborhood",
    ),
    "CH4": _BASE.format(
        kr="오묘한심리", en="MysticMind",
        theme="psychology — brain, thought bubbles, mirror, emotions, mind",
    ),
    "CH5": _BASE.format(
        kr="검은물음표", en="BlackQuestionMark",
        theme="mystery — magnifying glass, question mark, shadow, clue, enigma",
    ),
    "CH6": _BASE.format(
        kr="오래된두루마리", en="AncientScroll",
        theme="history — ancient scroll, artifacts, hourglass, timeline, ruins",
    ),
    "CH7": _BASE.format(
        kr="워메이징", en="WarMazing",
        theme="war history — strategy map, shield, sword, battle flag, compass",
    ),
}


def main():
    client = _make_client()

    for ch_id, prompt in CHANNEL_PROMPTS.items():
        output_dir = Path(f"assets/channels/{ch_id}/_candidates/logo_final")
        print(f"\n[{ch_id}] 로고 50장 생성 시작...")
        saved = generate_best_of_n_multi_reference(
            reference_image_paths=REF_IMAGES,
            prompt=prompt,
            output_dir=output_dir,
            n=50,
            client=client,
        )
        print(f"[{ch_id}] 완료: {len(saved)}/50장 저장")


if __name__ == "__main__":
    main()
