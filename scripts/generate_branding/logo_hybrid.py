"""
logo_hybrid.py
──────────────
Gemini 텍스트 모델로 머니그래픽 CH1 로고 SVG 코드를 직접 생성.

LoRA/GPU 없이도 최고 퀄리티 SVG를 생성할 수 있는 네이티브 접근법.
Potrace 의존성 없음 — SVG 코드 자체를 LLM이 설계.

Usage:
    python -m scripts.generate_branding.logo_hybrid
"""
from __future__ import annotations

import os
import sys
import io
import re
import xml.etree.ElementTree as ET
from pathlib import Path

from dotenv import load_dotenv
from loguru import logger

load_dotenv()

# ── 경로 설정 ─────────────────────────────────────────────────────────────────
KAS_ROOT = Path(__file__).parent.parent.parent
OUTPUT_PATH = KAS_ROOT / "assets" / "channels" / "CH1" / "logo" / "logo.svg"

# Gemini 모델
TEXT_MODEL = os.getenv("GEMINI_TEXT_MODEL", "gemini-2.5-flash")

# ── SVG 생성 프롬프트 ─────────────────────────────────────────────────────────
SVG_PROMPT = """Create a complete, valid SVG file for a YouTube channel logo.
Output ONLY raw SVG XML. No markdown. No explanation. No code blocks.
Start directly with: <svg

Requirements:
- width=600 height=600 viewBox="0 0 600 600" xmlns="http://www.w3.org/2000/svg"
- White background rect fill #FFFFFF
- Outer circle cx=300 cy=300 r=220 stroke #2C3E50 fill none stroke-width 6
- Inner circle cx=300 cy=300 r=210 stroke #2ECC71 fill none stroke-width 3
- Character head: filled circle cx=300 cy=210 r=55 fill #2C3E50
- Left eye: cx=285 cy=200 r=8 fill white
- Right eye: cx=315 cy=200 r=8 fill white
- Smile: path arc from (275,230) to (325,230) curving downward
- Crown: polygon W-shape above head fill #F1C40F (points around y=145-165)
- Channel name text: x=300 y=420 font-size=44 text-anchor=middle fill=#2C3E50 font-weight=bold content: MoneyGraphic
- Four diamond stars near circle edge at top/bottom/left/right positions fill #F1C40F

End with: </svg>"""

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


def generate_ch1_logo() -> Path:
    """Gemini 텍스트 모델로 CH1 머니그래픽 로고 SVG를 생성·저장.

    Returns:
        저장된 SVG 파일 경로.
    """
    from google import genai
    from google.genai import types

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY 환경변수 미설정")

    client = genai.Client(api_key=api_key)

    logger.info(f"[Logo] Gemini({TEXT_MODEL})로 SVG 생성 시작")

    # 최대 3회 재시도 (SVG 유효성 실패 대비)
    for attempt in range(1, 4):
        logger.info(f"  시도 {attempt}/3")
        response = client.models.generate_content(
            model=TEXT_MODEL,
            contents=SVG_PROMPT,
            config=types.GenerateContentConfig(
                temperature=0.1,   # 낮은 온도 → 더 결정론적인 SVG 코드
                max_output_tokens=8192,  # 충분한 토큰 확보 (4096은 잘릴 수 있음)
            ),
        )
        raw = response.text or ""
        svg_text = _extract_svg(raw)

        if not svg_text.startswith("<svg"):
            logger.warning(f"  SVG 태그 없음, 재시도")
            continue

        if not _validate_svg(svg_text):
            logger.warning(f"  SVG 유효성 실패, 재시도")
            continue

        # 성공 — 저장
        OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
        OUTPUT_PATH.write_text(svg_text, encoding="utf-8")
        logger.info(f"[Logo] 완료: {OUTPUT_PATH} ({len(svg_text):,} bytes)")
        return OUTPUT_PATH

    raise RuntimeError("SVG 생성 3회 모두 실패 — Gemini 응답을 확인하세요")


if __name__ == "__main__":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    generate_ch1_logo()
