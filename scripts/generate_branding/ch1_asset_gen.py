"""
ch1_asset_gen.py
────────────────
CH1 전용 Gemini Pro 기반 에셋 생성기.

모든 시각적 자산을 gemini-3-pro-image-preview로 생성한다.
PIL은 리사이즈·합성 등 후처리에만 사용한다.

Usage:
    python scripts/generate_branding/ch1_asset_gen.py
"""
from __future__ import annotations

import io
import os
import shutil
import sys
import time
from pathlib import Path
from typing import Optional

from loguru import logger
from PIL import Image

if hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

# ── 경로 ────────────────────────────────────────────────────────────────────
KAS_ROOT = Path(__file__).parent.parent.parent
CH1_DIR = KAS_ROOT / "assets" / "channels" / "CH1"
WONEE_SHEET_PATH = KAS_ROOT / "essential_branding" / "CH1_wonee_sheet.png"

# ── 헬퍼 임포트 ─────────────────────────────────────────────────────────────
sys.path.insert(0, str(Path(__file__).parent))
from nano_banana_helper import (  # noqa: E402
    BudgetExceededError,
    generate_best_of_n,
    generate_best_of_n_with_reference,
    generate_image,
    generate_with_reference,
)

# ── CH1 공통 스타일 프롬프트 ──────────────────────────────────────────────────
_DOODLE_BASE = (
    "Flat 2D hand-drawn doodle illustration style for Korean YouTube channel '머니그래픽' (economics). "
    "Thin black marker lines 2-3px, pure white background #FFFFFF. "
    "Wobbly hand-drawn lines, flat coloring, NO gradients, NO shadows, NO 3D effects. "
    "Color palette: gold #F4C420, dark charcoal #333333, green #16A34A, red #DC2626. "
    "Kawaii cute economics channel aesthetic. "
)

_WONEE_DESC = (
    "Character '원이': perfectly round white body with thin black outline 2px, "
    "small gold crown with three rounded bumps on top (NO ₩ symbol, NO letters in crown), "
    "small oval black dot eyes with white highlight, tiny curved smile, "
    "golden blush circles on cheeks, simple thin stick arms and legs. "
)


# ── PIL 후처리 유틸 ─────────────────────────────────────────────────────────

def _resize_to(path: Path, size: tuple[int, int]) -> None:
    """생성된 이미지를 정확한 크기로 리사이즈 (덮어쓰기)."""
    if not path.exists():
        return
    img = Image.open(path).convert("RGBA")
    img = img.resize(size, Image.LANCZOS)
    img.save(path, "PNG")
    logger.debug(f"  → 리사이즈 완료: {size[0]}×{size[1]}")


def _first_to_canonical(variants: list[Path], canonical_path: Path) -> bool:
    """Best-of-N variant 첫 번째를 canonical_path로 복사한다."""
    if not variants:
        logger.warning(f"variant 없음 — {canonical_path.name} 스킵")
        return False
    canonical_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(variants[0], canonical_path)
    logger.info(f"[OK] {canonical_path.name} ← {variants[0].name}")
    return True


# ── 로고 ────────────────────────────────────────────────────────────────────

def gen_logo(client) -> None:
    """CH1 채널 로고 배지 (512×512) — Best-of-3."""
    prompt = (
        _DOODLE_BASE + _WONEE_DESC
        + "Circular channel logo badge design. "
        + "원이 character centered inside a hand-drawn double circle border. "
        + "'머니그래픽' in bold hand-lettered Korean text below character inside circle. "
        + "Small gold 4-pointed sparkle stars at diagonal corners outside the circle. "
        + "Decorative gold curved arrows around the border. "
        + "Square 1:1 composition, pure white background."
    )
    out = CH1_DIR / "logo" / "logo.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    variants = generate_best_of_n(prompt, out, n=3, client=client)
    if _first_to_canonical(variants, out):
        _resize_to(out, (512, 512))


# ── 인트로 분해 요소 ─────────────────────────────────────────────────────────

def gen_intro_frame(client) -> None:
    """인트로 장식 프레임 (512×512)."""
    prompt = (
        _DOODLE_BASE
        + "Decorative circular frame element only — empty center, no character inside. "
        + "Hand-drawn double circle border with gold 4-pointed star decorations "
        + "at 12/3/6/9 o'clock positions on the circle edge. "
        + "Gold and black strokes on pure white background. "
        + "Square 1:1 composition."
    )
    out = CH1_DIR / "intro" / "intro_frame.png"
    if generate_image(prompt, out, client=client):
        _resize_to(out, (512, 512))


def gen_intro_text(client) -> None:
    """인트로 채널명 배너 (620×156)."""
    prompt = (
        _DOODLE_BASE
        + "Horizontal text banner. "
        + "Dark charcoal #333333 rounded rectangle background. "
        + "Bold hand-lettered Korean text '머니그래픽' in gold color centered. "
        + "Thin green left accent stripe on the left edge of the banner. "
        + "Very wide horizontal banner (about 4:1 width-to-height ratio). "
        + "Doodle style hand-lettering, pure white outside the banner."
    )
    out = CH1_DIR / "intro" / "intro_text.png"
    if generate_image(prompt, out, client=client):
        _resize_to(out, (620, 156))


def gen_intro_sparkle(client) -> None:
    """인트로 스파클 장식 (256×256)."""
    prompt = (
        _DOODLE_BASE
        + "Gold sparkle starburst decoration icon. "
        + "4-pointed elongated star shape in gold #F4C420. "
        + "Short radiating lines extending from tips for glow effect. "
        + "White center highlight dot. "
        + "Isolated on pure white background, square 1:1 composition."
    )
    out = CH1_DIR / "intro" / "intro_sparkle.png"
    if generate_image(prompt, out, client=client):
        _resize_to(out, (256, 256))


def gen_intro_character(client) -> None:
    """인트로 캐릭터 (512×512) — character_explain 재사용 또는 Gemini 직접 생성."""
    out = CH1_DIR / "intro" / "intro_character.png"
    src = CH1_DIR / "characters" / "character_explain.png"
    if src.exists():
        shutil.copy2(src, out)
        _resize_to(out, (512, 512))
        logger.info("[OK] intro_character.png ← character_explain.png 재사용")
        return
    # character_explain.png 미생성 시 시트 참조 생성
    if WONEE_SHEET_PATH.exists():
        sys.path.insert(0, str(Path(__file__).parent))
        from config import CHANNELS
        prompt = CHANNELS["CH1"]["character_prompts"]["explain"]
        if generate_with_reference(WONEE_SHEET_PATH, prompt, out, client=client):
            _resize_to(out, (512, 512))
    else:
        logger.warning("character_explain.png · WONEE_SHEET 없음 — intro_character.png 스킵")


# ── 아웃트로 분해 요소 ───────────────────────────────────────────────────────

def gen_outro_background(client) -> None:
    """아웃트로 배경 (1280×720)."""
    prompt = (
        _DOODLE_BASE
        + "YouTube outro background screen, 16:9 landscape. "
        + "White background with soft green (#16A34A) gradient strip at the bottom 20%. "
        + "Faint ₩ currency symbols scattered as light watermark texture across the surface. "
        + "Light green concentric circle outlines around the center area. "
        + "Calm, professional, inviting economics channel aesthetic."
    )
    out = CH1_DIR / "outro" / "outro_background.png"
    if generate_image(prompt, out, client=client):
        _resize_to(out, (1280, 720))


def gen_outro_bill(client) -> None:
    """아웃트로 지폐 일러스트 (320×150) — Best-of-3."""
    prompt = (
        _DOODLE_BASE
        + "Simple cartoon Korean banknote prop illustration. "
        + "Green (#16A34A) colored horizontal rectangle bill with rounded corners and double inner border. "
        + "Large '₩' symbol on the left, '50,000' number in center-right. "
        + "Small gold 4-pointed star decorations at two corners. "
        + "Hand-drawn doodle style, pure white background, wide 2:1 horizontal proportions."
    )
    out = CH1_DIR / "outro" / "outro_bill.png"
    variants = generate_best_of_n(prompt, out, n=3, client=client)
    if _first_to_canonical(variants, out):
        _resize_to(out, (320, 150))


def gen_outro_character(client) -> None:
    """아웃트로 캐릭터 (512×512) — character_victory 재사용 또는 Gemini 직접 생성."""
    out = CH1_DIR / "outro" / "outro_character.png"
    src = CH1_DIR / "characters" / "character_victory.png"
    if src.exists():
        shutil.copy2(src, out)
        _resize_to(out, (512, 512))
        logger.info("[OK] outro_character.png ← character_victory.png 재사용")
        return
    if WONEE_SHEET_PATH.exists():
        sys.path.insert(0, str(Path(__file__).parent))
        from config import CHANNELS
        prompt = CHANNELS["CH1"]["character_prompts"]["victory"]
        if generate_with_reference(WONEE_SHEET_PATH, prompt, out, client=client):
            _resize_to(out, (512, 512))
    else:
        logger.warning("character_victory.png · WONEE_SHEET 없음 — outro_character.png 스킵")


def gen_outro_cta(client) -> None:
    """아웃트로 CTA 버튼 (600×120)."""
    prompt = (
        _DOODLE_BASE
        + "YouTube subscribe and like CTA button pair, side by side horizontal layout. "
        + "Left: rounded red (#DC2626) pill button with bold white Korean text '구독'. "
        + "Right: rounded green (#16A34A) pill button with bold white Korean text '좋아요'. "
        + "Hand-drawn doodle style edges. "
        + "White background, very wide horizontal proportions (5:1 ratio)."
    )
    out = CH1_DIR / "outro" / "outro_cta.png"
    if generate_image(prompt, out, client=client):
        _resize_to(out, (600, 120))


# ── 자막바 3종 ───────────────────────────────────────────────────────────────

def gen_subtitle_bar_key(client) -> None:
    """KEY 자막바 (1280×120)."""
    prompt = (
        _DOODLE_BASE
        + "Video subtitle overlay bar — 'KEY' keyword style. "
        + "Dark charcoal #333333 semi-transparent rounded horizontal bar. "
        + "Green rounded badge label 'KEY' on the far left. "
        + "White text placeholder area in the center. "
        + "Gold 4-pointed star on the far right. "
        + "Very wide horizontal proportions, about 11:1 width-to-height."
    )
    out = CH1_DIR / "templates" / "subtitle_bar_key.png"
    if generate_image(prompt, out, client=client):
        _resize_to(out, (1280, 120))


def gen_subtitle_bar_dialog(client) -> None:
    """DIALOG 자막바 (1280×120)."""
    prompt = (
        _DOODLE_BASE
        + "Video subtitle overlay bar for narration/dialogue. "
        + "Dark semi-transparent rounded horizontal bar. "
        + "Thin green (#16A34A) accent line at the bottom edge. "
        + "Light white text placeholder area. "
        + "Very wide horizontal proportions, about 11:1 width-to-height."
    )
    out = CH1_DIR / "templates" / "subtitle_bar_dialog.png"
    if generate_image(prompt, out, client=client):
        _resize_to(out, (1280, 120))


def gen_subtitle_bar_info(client) -> None:
    """INFO 자막바 (1280×120)."""
    prompt = (
        _DOODLE_BASE
        + "Video info highlight subtitle bar. "
        + "Green (#16A34A) rounded horizontal bar background. "
        + "Dark circular badge with bold italic 'i' on left side. "
        + "Dark charcoal placeholder text area. "
        + "Very wide horizontal proportions, about 11:1 width-to-height."
    )
    out = CH1_DIR / "templates" / "subtitle_bar_info.png"
    if generate_image(prompt, out, client=client):
        _resize_to(out, (1280, 120))


# ── 썸네일 3종 ───────────────────────────────────────────────────────────────

def _gen_thumbnail(
    client,
    idx: int,
    title: str,
    pose_desc: str,
    color_hint: str,
) -> None:
    """썸네일 1장 — Best-of-3, 1920×1080."""
    prompt = (
        _DOODLE_BASE + _WONEE_DESC
        + f"YouTube thumbnail for economics channel '머니그래픽', 16:9 landscape. "
        + f"Large bold Korean text '{title}' prominently on the LEFT half. "
        + f"원이 character ({pose_desc}) on the RIGHT side, full body visible. "
        + f"{color_hint} "
        + "Small '머니그래픽' channel name text at top left corner. "
        + "High CTR YouTube thumbnail composition, doodle style, eye-catching."
    )
    out = CH1_DIR / "templates" / f"thumbnail_sample_{idx}.png"
    variants = generate_best_of_n(prompt, out, n=3, client=client)
    if _first_to_canonical(variants, out):
        _resize_to(out, (1920, 1080))


def gen_thumbnails(client) -> None:
    """CH1 썸네일 3종 — Best-of-3 each."""
    configs = [
        (1, "코인 차트의 마법!", "pointing arm explain pose", "Cream/white background, gold #F4C420 accent."),
        (2, "금리 인상, 내 지갑은?", "thumbs-up victory pose", "White background, gold #F4C420 accent."),
        (3, "주식 초보, 이것만 알아!", "jumping V-arms happy pose", "White background, green #16A34A accent."),
    ]
    for idx, title, pose_desc, color_hint in configs:
        _gen_thumbnail(client, idx, title, pose_desc, color_hint)
        if idx < 3:
            time.sleep(1.0)  # rate limit 방지


# ── 전환 3종 ─────────────────────────────────────────────────────────────────

def gen_transition_paper(client) -> None:
    """전환 paper 효과 (1920×1080)."""
    prompt = (
        _DOODLE_BASE
        + "Video scene transition frame: paper fold effect. "
        + "Left half cream/white, right half dark charcoal, "
        + "vertical fold crease in center with light shadow. "
        + "Small circular doodle logo motif with gold star at the fold center. "
        + "Wide 16:9 landscape composition."
    )
    out = CH1_DIR / "templates" / "transition_paper.png"
    if generate_image(prompt, out, client=client):
        _resize_to(out, (1920, 1080))


def gen_transition_ink(client) -> None:
    """전환 ink 잉크 번짐 효과 (1920×1080)."""
    prompt = (
        _DOODLE_BASE
        + "Video scene transition: dramatic ink splash explosion. "
        + "Black ink blob bursting from center of white background, "
        + "irregular splatters and ink droplets radiating outward in all directions. "
        + "Doodle/comic style ink splat, high contrast black on white. "
        + "Wide 16:9 landscape composition."
    )
    out = CH1_DIR / "templates" / "transition_ink.png"
    if generate_image(prompt, out, client=client):
        _resize_to(out, (1920, 1080))


def gen_transition_zoom(client) -> None:
    """전환 zoom 동심원 효과 (1920×1080)."""
    prompt = (
        _DOODLE_BASE
        + "Video scene transition: concentric zoom rings effect. "
        + "Dark charcoal background with concentric circle rings "
        + "alternating gold #F4C420 and green #16A34A, radiating outward from center. "
        + "Gold 4-pointed star at the very center. "
        + "Thin radiating lines between rings. "
        + "Wide 16:9 landscape composition."
    )
    out = CH1_DIR / "templates" / "transition_zoom.png"
    if generate_image(prompt, out, client=client):
        _resize_to(out, (1920, 1080))


# ── 메인 ─────────────────────────────────────────────────────────────────────

def generate_ch1_assets(client=None) -> None:
    """CH1 Gemini Pro 에셋 전체 생성.

    Args:
        client: google.genai.Client 인스턴스. None이면 GEMINI_API_KEY로 자동 생성.
    """
    if client is None:
        from google import genai as _genai
        client = _genai.Client(api_key=os.environ["GEMINI_API_KEY"])

    logger.info("=" * 60)
    logger.info("CH1 Gemini Pro 에셋 생성 시작 (17종)")
    logger.info("=" * 60)

    try:
        gen_logo(client)

        gen_intro_frame(client)
        gen_intro_text(client)
        gen_intro_sparkle(client)
        gen_intro_character(client)

        gen_outro_background(client)
        gen_outro_bill(client)
        gen_outro_character(client)
        gen_outro_cta(client)

        gen_subtitle_bar_key(client)
        gen_subtitle_bar_dialog(client)
        gen_subtitle_bar_info(client)

        gen_thumbnails(client)

        gen_transition_paper(client)
        gen_transition_ink(client)
        gen_transition_zoom(client)

    except BudgetExceededError as e:
        logger.error(f"예산 초과 — 생성 중단: {e}")

    logger.info("=" * 60)
    logger.info("[완료] CH1 Gemini Pro 에셋 생성 완료")
    logger.info("=" * 60)


if __name__ == "__main__":
    generate_ch1_assets()
