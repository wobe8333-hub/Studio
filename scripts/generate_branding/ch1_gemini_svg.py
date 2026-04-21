"""
ch1_gemini_svg.py
─────────────────
Gemini 2.5 Flash로 CH1 머니그래픽 브랜딩 SVG 9종을 생성하고
cairosvg/svglib로 PNG 래스터화.

Usage:
    python -m scripts.generate_branding.ch1_gemini_svg
"""
from __future__ import annotations

import io
import os
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

from dotenv import load_dotenv
from loguru import logger

load_dotenv()

# ── 경로 설정 ──────────────────────────────────────────────────────────────────
KAS_ROOT = Path(__file__).parent.parent.parent
CHANNELS_DIR = KAS_ROOT / "assets" / "channels" / "CH1"

# Gemini 모델
TEXT_MODEL = os.getenv("GEMINI_TEXT_MODEL", "gemini-2.5-flash")

# ── 공통 헬퍼 ─────────────────────────────────────────────────────────────────

def _extract_svg(text: str) -> str:
    """응답 텍스트에서 SVG 블록만 추출."""
    # 마크다운 코드 블록 제거
    text = re.sub(r"```(?:svg|xml)?\s*", "", text)
    text = re.sub(r"```", "", text)
    # <svg ... </svg> 추출
    match = re.search(r"<svg[\s\S]*?</svg>", text, re.IGNORECASE)
    if match:
        return match.group(0).strip()
    return text.strip()


def _validate_svg(svg_text: str) -> bool:
    """SVG XML 유효성 검증."""
    try:
        ET.fromstring(svg_text)
        return True
    except ET.ParseError as e:
        logger.warning(f"SVG XML 파싱 실패: {e}")
        return False


def _call_gemini_svg(client, prompt: str) -> str:
    """Gemini로 SVG 코드 생성, 최대 3회 재시도."""
    from google.genai import types

    for attempt in range(1, 4):
        logger.info(f"  Gemini 시도 {attempt}/3")
        response = client.models.generate_content(
            model=TEXT_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.1,       # 낮은 온도 → 결정론적 SVG 코드
                max_output_tokens=8192,
            ),
        )
        raw = response.text or ""
        svg_text = _extract_svg(raw)

        if not svg_text.startswith("<svg"):
            logger.warning("  SVG 태그 없음, 재시도")
            continue

        if not _validate_svg(svg_text):
            logger.warning("  SVG 유효성 실패, 재시도")
            continue

        return svg_text

    raise RuntimeError("SVG 생성 3회 모두 실패 — Gemini 응답을 확인하세요")


def _rasterize_svg(svg_path: Path, width: int, height: int) -> Path:
    """SVG를 PNG로 래스터화. cairosvg 우선, fallback: svglib."""
    png_path = svg_path.with_suffix(".png")
    try:
        import cairosvg
        cairosvg.svg2png(
            url=str(svg_path),
            write_to=str(png_path),
            output_width=width,
            output_height=height,
        )
        logger.info(f"  [cairosvg] PNG 저장: {png_path}")
    except ImportError:
        # fallback: svglib + reportlab
        try:
            from reportlab.graphics import renderPM
            from svglib.svglib import svg2rlg
            drawing = svg2rlg(str(svg_path))
            renderPM.drawToFile(drawing, str(png_path), fmt="PNG")
            logger.info(f"  [svglib] PNG 저장: {png_path}")
        except Exception as e:
            logger.warning(f"SVG 래스터화 실패: {svg_path} — {e}, PNG 생략")
            return svg_path
    return png_path


# ── 프롬프트 빌더 ─────────────────────────────────────────────────────────────

def _build_prompt_for_logo() -> str:
    return (
        "Create a complete, valid SVG file for a YouTube channel logo. "
        "Output ONLY raw SVG XML. No markdown. No explanation. No code blocks. "
        "Start directly with: <svg\n\n"
        "Requirements:\n"
        "- width=600 height=600 viewBox=\"0 0 600 600\" xmlns=\"http://www.w3.org/2000/svg\"\n"
        "- Background: <rect width=\"600\" height=\"600\" fill=\"#FFFDF5\"/>\n"
        "- Outer circle: cx=300 cy=300 r=260 stroke=\"#2C3E50\" stroke-width=\"7\" fill=\"none\"\n"
        "- Inner circle: cx=300 cy=300 r=248 stroke=\"#2ECC71\" stroke-width=\"3\" fill=\"none\"\n"
        "- Center rounded head: rect cx=300 cy=210 w=90 h=105 rx=30 ry=35 fill=\"#2C3E50\"\n"
        "- Gold W crown polygon above head: fill=\"#F1C40F\"\n"
        "- Channel name text: x=300 y=430 text-anchor=\"middle\" font-size=\"44\" fill=\"#2C3E50\" "
        "font-weight=\"bold\" content: MoneyGraphic\n"
        "- Four diamond polygon stars near circle edge at 90° intervals: fill=\"#F1C40F\"\n"
        "Return only valid SVG code starting with <svg."
    )


def _build_prompt_for_intro_frame() -> str:
    return (
        "Create a complete, valid SVG file for a YouTube intro frame decoration. "
        "Output ONLY raw SVG XML. No markdown. No explanation. No code blocks. "
        "Start directly with: <svg\n\n"
        "Requirements:\n"
        "- width=512 height=512 viewBox=\"0 0 512 512\" xmlns=\"http://www.w3.org/2000/svg\"\n"
        "- Background: <rect width=\"512\" height=\"512\" fill=\"#FFFDF5\"/>\n"
        "- Outer concentric circle: cx=256 cy=256 r=240 stroke=\"#2C3E50\" stroke-width=\"5\" fill=\"none\"\n"
        "- Inner concentric circle: cx=256 cy=256 r=228 stroke=\"#2ECC71\" stroke-width=\"3\" fill=\"none\"\n"
        "- 8 gold star points at 45° intervals on r=120 from center (256,256): "
        "small 4-point diamond polygons fill=\"#F1C40F\"\n"
        "Return only valid SVG code starting with <svg."
    )


def _build_prompt_for_intro_text() -> str:
    return (
        "Create a complete, valid SVG file for a YouTube channel intro text banner. "
        "Output ONLY raw SVG XML. No markdown. No explanation. No code blocks. "
        "Start directly with: <svg\n\n"
        "Requirements:\n"
        "- width=620 height=156 viewBox=\"0 0 620 156\" xmlns=\"http://www.w3.org/2000/svg\"\n"
        "- Background: <rect width=\"620\" height=\"156\" fill=\"#FFFDF5\" rx=\"12\"/>\n"
        "- Left accent bar: x=\"0\" y=\"0\" width=\"8\" height=\"156\" fill=\"#2ECC71\"\n"
        "- Main text: <text x=\"320\" y=\"110\" text-anchor=\"middle\" "
        "font-size=\"72\" fill=\"#2ECC71\" font-weight=\"bold\">머니그래픽</text>\n"
        "Return only valid SVG code starting with <svg."
    )


def _build_prompt_for_intro_sparkle() -> str:
    return (
        "Create a complete, valid SVG file for a YouTube intro sparkle decoration. "
        "Output ONLY raw SVG XML. No markdown. No explanation. No code blocks. "
        "Start directly with: <svg\n\n"
        "Requirements:\n"
        "- width=256 height=256 viewBox=\"0 0 256 256\" xmlns=\"http://www.w3.org/2000/svg\"\n"
        "- Background: <rect width=\"256\" height=\"256\" fill=\"#FFFDF5\"/>\n"
        "- Central 4-point gold star polygon spanning r=100 from center (128,128): fill=\"#F1C40F\"\n"
        "- Same 4-point star rotated 45°: fill=\"#F1C40F\" opacity=\"0.7\"\n"
        "- Small white circle: cx=128 cy=128 r=8 fill=\"white\"\n"
        "Return only valid SVG code starting with <svg."
    )


def _build_prompt_for_outro_bill() -> str:
    return (
        "Create a complete, valid SVG file for a YouTube outro animated bill element. "
        "Output ONLY raw SVG XML. No markdown. No explanation. No code blocks. "
        "Start directly with: <svg\n\n"
        "Requirements:\n"
        "- width=320 height=150 viewBox=\"0 0 320 150\" xmlns=\"http://www.w3.org/2000/svg\"\n"
        "- Transparent background (no background rect)\n"
        "- Main bill: rounded rect x=0 y=0 width=320 height=150 fill=\"#2ECC71\" rx=10\n"
        "- Inner white frame: rect x=8 y=8 width=304 height=134 fill=\"none\" "
        "stroke=\"white\" stroke-width=\"2\" rx=7\n"
        "- Large won sign: <text x=\"22\" y=\"95\" fill=\"white\" font-size=\"80\" "
        "font-weight=\"bold\">₩</text>\n"
        "- Amount text: <text x=\"122\" y=\"60\" fill=\"white\" font-size=\"32\" "
        "font-weight=\"bold\">50,000</text>\n"
        "- 2 gold diamond stars at top-right and bottom-right corners: fill=\"#F1C40F\"\n"
        "Return only valid SVG code starting with <svg."
    )


def _build_prompt_for_outro_cta() -> str:
    return (
        "Create a complete, valid SVG file for a YouTube outro call-to-action buttons. "
        "Output ONLY raw SVG XML. No markdown. No explanation. No code blocks. "
        "Start directly with: <svg\n\n"
        "Requirements:\n"
        "- width=600 height=120 viewBox=\"0 0 600 120\" xmlns=\"http://www.w3.org/2000/svg\"\n"
        "- Transparent background (no background rect)\n"
        "- Left subscribe button: rect x=0 y=0 width=280 height=120 fill=\"#E74C3C\" rx=12, "
        "text \"구독\" centered x=140 y=72 fill=\"white\" font-size=\"44\" font-weight=\"bold\"\n"
        "- Right like button: rect x=320 y=0 width=280 height=120 fill=\"#2ECC71\" rx=12, "
        "text \"좋아요\" centered x=460 y=72 fill=\"white\" font-size=\"44\" font-weight=\"bold\"\n"
        "Return only valid SVG code starting with <svg."
    )


def _build_prompt_for_subtitle_bar_key() -> str:
    return (
        "Create a complete, valid SVG file for a YouTube subtitle/lower-third KEY term bar. "
        "Output ONLY raw SVG XML. No markdown. No explanation. No code blocks. "
        "Start directly with: <svg\n\n"
        "Requirements:\n"
        "- width=1280 height=120 viewBox=\"0 0 1280 120\" xmlns=\"http://www.w3.org/2000/svg\"\n"
        "- Background: <rect width=\"1280\" height=\"120\" fill=\"#FFFDF5\"/>\n"
        "- Dark rounded bar: rect x=20 y=10 width=1240 height=100 fill=\"#2C3E50\" rx=8 opacity=0.92\n"
        "- Mint KEY badge: rect x=30 y=20 width=80 height=80 fill=\"#2ECC71\" rx=6, "
        "text \"KEY\" x=70 y=68 text-anchor=\"middle\" fill=\"white\" font-size=\"24\" font-weight=\"bold\"\n"
        "- Content text area: <text x=\"140\" y=\"70\" fill=\"white\" font-size=\"32\">핵심 용어 텍스트 영역</text>\n"
        "- 2 gold diamond stars at right edge (x~1220-1250 y~60): fill=\"#F1C40F\"\n"
        "Return only valid SVG code starting with <svg."
    )


def _build_prompt_for_subtitle_bar_dialog() -> str:
    return (
        "Create a complete, valid SVG file for a YouTube subtitle/lower-third narration bar. "
        "Output ONLY raw SVG XML. No markdown. No explanation. No code blocks. "
        "Start directly with: <svg\n\n"
        "Requirements:\n"
        "- width=1280 height=120 viewBox=\"0 0 1280 120\" xmlns=\"http://www.w3.org/2000/svg\"\n"
        "- Background: <rect width=\"1280\" height=\"120\" fill=\"#FFFDF5\"/>\n"
        "- Dark rounded bar: rect x=20 y=10 width=1240 height=100 fill=\"#2C3E50\" rx=8 opacity=0.80\n"
        "- Mint underline: rect x=20 y=108 width=1240 height=4 fill=\"#2ECC71\"\n"
        "- Narration text: <text x=\"60\" y=\"70\" fill=\"#FFFDF5\" font-size=\"30\">나레이션 텍스트 영역</text>\n"
        "Return only valid SVG code starting with <svg."
    )


def _build_prompt_for_subtitle_bar_info() -> str:
    return (
        "Create a complete, valid SVG file for a YouTube subtitle/lower-third info emphasis bar. "
        "Output ONLY raw SVG XML. No markdown. No explanation. No code blocks. "
        "Start directly with: <svg\n\n"
        "Requirements:\n"
        "- width=1280 height=120 viewBox=\"0 0 1280 120\" xmlns=\"http://www.w3.org/2000/svg\"\n"
        "- Background: <rect width=\"1280\" height=\"120\" fill=\"#2ECC71\"/>\n"
        "- Dark info circle: cx=50 cy=60 r=35 fill=\"#2C3E50\"\n"
        "- Info i text in circle: <text x=\"50\" y=\"76\" text-anchor=\"middle\" fill=\"white\" "
        "font-size=\"36\" font-weight=\"bold\">i</text>\n"
        "- Info text: <text x=\"110\" y=\"72\" fill=\"#2C3E50\" font-size=\"32\">정보 강조 텍스트 영역</text>\n"
        "Return only valid SVG code starting with <svg."
    )


# ── SVG 생성 함수 9종 ─────────────────────────────────────────────────────────

def gen_logo_svg(client, output_dir: Path) -> Path:
    """로고 SVG/PNG 생성 — 600×600."""
    logger.info("[SVG] logo 생성 중...")
    prompt = _build_prompt_for_logo()
    svg_content = _call_gemini_svg(client, prompt)

    svg_path = output_dir / "logo" / "logo.svg"
    svg_path.parent.mkdir(parents=True, exist_ok=True)
    svg_path.write_text(svg_content, encoding="utf-8")
    logger.info(f"  SVG 저장: {svg_path}")

    png_path = _rasterize_svg(svg_path, width=600, height=600)
    return png_path


def gen_intro_frame_svg(client, output_dir: Path) -> Path:
    """인트로 프레임 장식 SVG/PNG 생성 — 512×512."""
    logger.info("[SVG] intro_frame 생성 중...")
    prompt = _build_prompt_for_intro_frame()
    svg_content = _call_gemini_svg(client, prompt)

    svg_path = output_dir / "intro" / "intro_frame.svg"
    svg_path.parent.mkdir(parents=True, exist_ok=True)
    svg_path.write_text(svg_content, encoding="utf-8")
    logger.info(f"  SVG 저장: {svg_path}")

    png_path = _rasterize_svg(svg_path, width=512, height=512)
    return png_path


def gen_intro_text_svg(client, output_dir: Path) -> Path:
    """인트로 텍스트 배너 SVG/PNG 생성 — 620×156."""
    logger.info("[SVG] intro_text 생성 중...")
    prompt = _build_prompt_for_intro_text()
    svg_content = _call_gemini_svg(client, prompt)

    svg_path = output_dir / "intro" / "intro_text.svg"
    svg_path.parent.mkdir(parents=True, exist_ok=True)
    svg_path.write_text(svg_content, encoding="utf-8")
    logger.info(f"  SVG 저장: {svg_path}")

    png_path = _rasterize_svg(svg_path, width=620, height=156)
    return png_path


def gen_intro_sparkle_svg(client, output_dir: Path) -> Path:
    """인트로 스파클 장식 SVG/PNG 생성 — 256×256."""
    logger.info("[SVG] intro_sparkle 생성 중...")
    prompt = _build_prompt_for_intro_sparkle()
    svg_content = _call_gemini_svg(client, prompt)

    svg_path = output_dir / "intro" / "intro_sparkle.svg"
    svg_path.parent.mkdir(parents=True, exist_ok=True)
    svg_path.write_text(svg_content, encoding="utf-8")
    logger.info(f"  SVG 저장: {svg_path}")

    png_path = _rasterize_svg(svg_path, width=256, height=256)
    return png_path


def gen_outro_bill_svg(client, output_dir: Path) -> Path:
    """아웃트로 지폐 요소 SVG/PNG 생성 — 320×150."""
    logger.info("[SVG] outro_bill 생성 중...")
    prompt = _build_prompt_for_outro_bill()
    svg_content = _call_gemini_svg(client, prompt)

    svg_path = output_dir / "outro" / "outro_bill.svg"
    svg_path.parent.mkdir(parents=True, exist_ok=True)
    svg_path.write_text(svg_content, encoding="utf-8")
    logger.info(f"  SVG 저장: {svg_path}")

    png_path = _rasterize_svg(svg_path, width=320, height=150)
    return png_path


def gen_outro_cta_svg(client, output_dir: Path) -> Path:
    """아웃트로 CTA 버튼 SVG/PNG 생성 — 600×120."""
    logger.info("[SVG] outro_cta 생성 중...")
    prompt = _build_prompt_for_outro_cta()
    svg_content = _call_gemini_svg(client, prompt)

    svg_path = output_dir / "outro" / "outro_cta.svg"
    svg_path.parent.mkdir(parents=True, exist_ok=True)
    svg_path.write_text(svg_content, encoding="utf-8")
    logger.info(f"  SVG 저장: {svg_path}")

    png_path = _rasterize_svg(svg_path, width=600, height=120)
    return png_path


def gen_subtitle_bar_key_svg(client, output_dir: Path) -> Path:
    """자막바 KEY 용어 템플릿 SVG/PNG 생성 — 1280×120."""
    logger.info("[SVG] subtitle_bar_key 생성 중...")
    prompt = _build_prompt_for_subtitle_bar_key()
    svg_content = _call_gemini_svg(client, prompt)

    svg_path = output_dir / "templates" / "subtitle_bar_key.svg"
    svg_path.parent.mkdir(parents=True, exist_ok=True)
    svg_path.write_text(svg_content, encoding="utf-8")
    logger.info(f"  SVG 저장: {svg_path}")

    png_path = _rasterize_svg(svg_path, width=1280, height=120)
    return png_path


def gen_subtitle_bar_dialog_svg(client, output_dir: Path) -> Path:
    """자막바 나레이션 대화 템플릿 SVG/PNG 생성 — 1280×120."""
    logger.info("[SVG] subtitle_bar_dialog 생성 중...")
    prompt = _build_prompt_for_subtitle_bar_dialog()
    svg_content = _call_gemini_svg(client, prompt)

    svg_path = output_dir / "templates" / "subtitle_bar_dialog.svg"
    svg_path.parent.mkdir(parents=True, exist_ok=True)
    svg_path.write_text(svg_content, encoding="utf-8")
    logger.info(f"  SVG 저장: {svg_path}")

    png_path = _rasterize_svg(svg_path, width=1280, height=120)
    return png_path


def gen_subtitle_bar_info_svg(client, output_dir: Path) -> Path:
    """자막바 정보 강조 템플릿 SVG/PNG 생성 — 1280×120."""
    logger.info("[SVG] subtitle_bar_info 생성 중...")
    prompt = _build_prompt_for_subtitle_bar_info()
    svg_content = _call_gemini_svg(client, prompt)

    svg_path = output_dir / "templates" / "subtitle_bar_info.svg"
    svg_path.parent.mkdir(parents=True, exist_ok=True)
    svg_path.write_text(svg_content, encoding="utf-8")
    logger.info(f"  SVG 저장: {svg_path}")

    png_path = _rasterize_svg(svg_path, width=1280, height=120)
    return png_path


# ── 엔트리포인트 ──────────────────────────────────────────────────────────────

def generate_ch1_gemini_svg(channels_dir: Path | None = None) -> None:
    """CH1 Gemini SVG 9종 생성.

    Args:
        channels_dir: CH1 채널 에셋 루트 경로.
                      None이면 KAS_ROOT/assets/channels/CH1 사용.
    """
    from google import genai

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY 환경변수 미설정")

    client = genai.Client(api_key=api_key)

    output_dir = channels_dir if channels_dir is not None else CHANNELS_DIR
    output_dir.mkdir(parents=True, exist_ok=True)

    logger.info(f"[CH1 Gemini SVG] 9종 생성 시작 → {output_dir}")

    generators = [
        gen_logo_svg,
        gen_intro_frame_svg,
        gen_intro_text_svg,
        gen_intro_sparkle_svg,
        gen_outro_bill_svg,
        gen_outro_cta_svg,
        gen_subtitle_bar_key_svg,
        gen_subtitle_bar_dialog_svg,
        gen_subtitle_bar_info_svg,
    ]

    results: list[Path] = []
    for gen_fn in generators:
        try:
            result_path = gen_fn(client, output_dir)
            results.append(result_path)
            logger.info(f"  완료: {result_path}")
        except Exception as e:
            logger.error(f"  실패 [{gen_fn.__name__}]: {e}")

    logger.info(f"[CH1 Gemini SVG] 완료 {len(results)}/{len(generators)}종")
    for p in results:
        logger.info(f"  - {p}")


if __name__ == "__main__":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    generate_ch1_gemini_svg()
