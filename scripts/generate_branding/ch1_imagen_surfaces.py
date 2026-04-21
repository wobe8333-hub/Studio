# scripts/generate_branding/ch1_imagen_surfaces.py
"""CH1 Imagen 4.0 2K 일러스트 표면 7종 Best-of-3 생성

생성 에셋:
  - outro/outro_background.png    (1920×1080, 16:9)
  - templates/_tmp/thumb1_bg.png  (썸네일 배경 #1)
  - templates/_tmp/thumb2_bg.png  (썸네일 배경 #2)
  - templates/_tmp/thumb3_bg.png  (썸네일 배경 #3)
  - templates/transition_paper.png (1920×1080)
  - templates/transition_ink.png   (1920×1080)
  - templates/transition_zoom.png  (1920×1080)

각 에셋: Best-of-3 variant (_candidates/) → Claude Vision 채점 → canonical 복사
"""
from __future__ import annotations

import io
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from loguru import logger
from PIL import Image

load_dotenv()

sys.path.insert(0, str(Path(__file__).parent))
from google import genai
from imagen_2k_helper import BudgetExceededError, generate_best_of_n

from config import CHANNELS_DIR

# ─────────────────────────────────────────────
# 프롬프트 정의
# ─────────────────────────────────────────────
_CREAM_SUFFIX = (
    "Solid flat warm cream #FFFDF5 background with no gradient and no texture on the background itself. "
    "Hand-drawn Korean YouTube doodle reference style."
)


def _prompt_outro_bg() -> str:
    return (
        "hand-drawn doodle illustration of a cozy Korean study desk scene from above: "
        "open ledger notebook, small piggy bank, neat stack of Korean 50000-won banknotes, "
        "abacus, potted plant, coffee mug. "
        "Mint #2ECC71 and gold #F1C40F accents only. "
        "No text, no characters. Flat 2D doodle. "
        + _CREAM_SUFFIX
    )


def _prompt_thumb1_bg() -> str:
    return (
        "hand-drawn doodle illustration: rising bitcoin coin and candlestick chart "
        "with mint #2ECC71 rising line on right half. "
        "Left half completely empty clean cream space reserved for Korean title text overlay. "
        "No text. Flat 2D. Korean YouTube thumbnail style. "
        + _CREAM_SUFFIX
    )


def _prompt_thumb2_bg() -> str:
    return (
        "hand-drawn doodle illustration: brown wallet with a rising interest-rate arrow, "
        "gold coins falling out, mint #2ECC71 and gold #F1C40F accents on right half. "
        "Left half completely empty for Korean title. "
        "No text. Flat 2D. "
        + _CREAM_SUFFIX
    )


def _prompt_thumb3_bg() -> str:
    return (
        "hand-drawn doodle illustration: open beginner stock-investing book "
        "with rising candlestick chart floating above it, mint and gold accents on right half. "
        "Left half completely empty for Korean title. "
        "No text. Flat 2D. "
        + _CREAM_SUFFIX
    )


def _prompt_transition_paper() -> str:
    return (
        "hand-drawn doodle illustration of a turning book page: "
        "top-right corner curling upward revealing page below, "
        "both pages warm cream #FFFDF5 tone with subtle paper texture. "
        "Soft fold shadow. Mint #2ECC71 and gold #F1C40F small decorative marks in corners. "
        "No text. Flat 2D. "
        + _CREAM_SUFFIX
    )


def _prompt_transition_ink() -> str:
    return (
        "hand-drawn watercolour ink bloom spreading outward from center on warm cream #FFFDF5 paper. "
        "Ink colour is deep mint #1E8449 fading to translucent edges. "
        "Organic feather edges, no sharp geometry. "
        "No text. "
        + _CREAM_SUFFIX
    )


def _prompt_transition_zoom() -> str:
    return (
        "hand-drawn doodle speed-lines radiating outward from a central mint #2ECC71 "
        "circular badge containing a gold W crown. "
        "16 black radial speed-lines, 3 concentric circles around badge. "
        "Korean anime-style zoom transition. Flat 2D. "
        "No text. "
        + _CREAM_SUFFIX
    )


# ─────────────────────────────────────────────
# 사후 처리: 1920×1080 LANCZOS 리사이즈
# ─────────────────────────────────────────────
def _resize_to_1920x1080(src: Path, dst: Path) -> None:
    """PNG를 1920×1080으로 LANCZOS 리사이즈 후 dst에 저장."""
    with Image.open(src) as img:
        resized = img.resize((1920, 1080), Image.LANCZOS)
        resized.save(dst, "PNG", optimize=True)


# ─────────────────────────────────────────────
# 개별 에셋 생성 함수
# ─────────────────────────────────────────────
def _gen_surface(
    client: genai.Client,
    prompt: str,
    canonical_path: Path,
    aspect: str = "16:9",
    resize_to_1920: bool = True,
) -> list[Path]:
    """Best-of-3 variant 생성 → canonical_path 근처 _candidates/ 저장 → variant 목록 반환."""
    canonical_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        candidates = generate_best_of_n(
            client=client,
            prompt=prompt,
            canonical_path=canonical_path,
            n=3,
            aspect=aspect,
        )
        if resize_to_1920 and candidates:
            # variant 전부 1920×1080으로 후처리 (Claude Vision 채점 전)
            resized_candidates = []
            for v in candidates:
                if v.exists() and v.suffix == ".png":
                    _resize_to_1920x1080(v, v)
                resized_candidates.append(v)
            return resized_candidates
        return candidates
    except BudgetExceededError:
        logger.error(f"[BUDGET] {canonical_path.name}: 예산 초과. 중단.")
        raise
    except Exception as e:
        logger.error(f"[ERR] {canonical_path.name}: {e}")
        return []


# ─────────────────────────────────────────────
# 메인 오케스트레이터
# ─────────────────────────────────────────────
def generate_ch1_imagen_surfaces(channels_dir: Path | None = None) -> dict[str, list[Path]]:
    """CH1 Imagen 일러스트 표면 7종을 Best-of-3으로 생성한다.

    Returns:
        {asset_key: [variant_path, ...]} — Claude Vision 채점 대기
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        logger.error("GEMINI_API_KEY 환경변수가 없습니다.")
        sys.exit(1)

    base = (channels_dir or CHANNELS_DIR) / "CH1"
    client = genai.Client(api_key=api_key)
    logger.info("Gemini Imagen 4.0 준비 완료 — CH1 표면 7종 Best-of-3 시작")

    results: dict[str, list[Path]] = {}

    surfaces = [
        ("outro_background", _prompt_outro_bg(), base / "outro" / "outro_background.png", "16:9"),
        ("thumb1_bg", _prompt_thumb1_bg(), base / "templates" / "_tmp" / "thumb1_bg.png", "16:9"),
        ("thumb2_bg", _prompt_thumb2_bg(), base / "templates" / "_tmp" / "thumb2_bg.png", "16:9"),
        ("thumb3_bg", _prompt_thumb3_bg(), base / "templates" / "_tmp" / "thumb3_bg.png", "16:9"),
        (
            "transition_paper",
            _prompt_transition_paper(),
            base / "templates" / "transition_paper.png",
            "16:9",
        ),
        (
            "transition_ink",
            _prompt_transition_ink(),
            base / "templates" / "transition_ink.png",
            "16:9",
        ),
        (
            "transition_zoom",
            _prompt_transition_zoom(),
            base / "templates" / "transition_zoom.png",
            "16:9",
        ),
    ]

    for asset_key, prompt, canonical_path, aspect in surfaces:
        logger.info(f"[{asset_key}] Best-of-3 variant 생성 중...")
        try:
            candidates = _gen_surface(client, prompt, canonical_path, aspect=aspect)
            results[asset_key] = candidates
            logger.info(f"[{asset_key}] {len(candidates)}개 variant 완료")
        except BudgetExceededError:
            logger.error("예산 초과로 이후 에셋 생성 중단.")
            break

    logger.info(
        f"\n[완료] CH1 표면 {len(results)}/7종 생성 완료 — Claude Vision 채점 대기"
    )
    return results


if __name__ == "__main__":
    if hasattr(sys.stdout, "buffer"):
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    generate_ch1_imagen_surfaces()
