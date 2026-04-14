# scripts/generate_branding/template_gen.py
"""영상 템플릿 SVG 생성 — 자막바·썸네일·장면전환·로워서드"""
import sys
import io

from pathlib import Path
from loguru import logger

sys.path.insert(0, str(Path(__file__).parent))
from config import CHANNELS, CHANNELS_DIR
from svg_helpers import svg_open, svg_close, doodle_rect, doodle_line, doodle_text, doodle_path


def subtitle_bar(ch_id: str) -> str:
    cfg = CHANNELS[ch_id]
    mc = cfg["main_color"]
    bg_fill = "#1A1A1A" if cfg["bg_color"] == "#FFFFFF" else cfg["bg_color"]
    return (
        svg_open(1280, 120, bg_fill)
        + doodle_rect(0, 8, 1280, 104, mc, sw=3, rx=8)
        + f'<text x="640" y="78" font-size="52" fill="{mc}" '
        + f'font-family="Gmarket Sans Bold,sans-serif" text-anchor="middle" font-weight="900">자막 텍스트 영역</text>'
        + svg_close()
    )


def thumbnail_template(ch_id: str) -> str:
    cfg = CHANNELS[ch_id]
    mc = cfg["main_color"]
    bg = cfg["bg_color"]
    return (
        svg_open(1280, 720, bg)
        + doodle_rect(12, 12, 1256, 696, mc, sw=6, rx=16)
        + doodle_rect(32, 32, 760, 656, mc, sw=3, rx=8)
        + doodle_rect(820, 32, 428, 310, mc, sw=3, rx=8)
        + doodle_rect(820, 378, 428, 310, mc, sw=3, rx=8)
        + f'<text x="412" y="380" font-size="64" fill="{mc}" '
        + f'font-family="Gmarket Sans Bold,sans-serif" text-anchor="middle" font-weight="900">제목 영역</text>'
        + f'<text x="1034" y="200" font-size="36" fill="{mc}" '
        + f'font-family="Gmarket Sans Bold,sans-serif" text-anchor="middle">{cfg["name"]}</text>'
        + svg_close()
    )


def transition_wipe(ch_id: str) -> str:
    cfg = CHANNELS[ch_id]
    mc = cfg["main_color"]
    return (
        svg_open(1920, 1080)
        + f'<defs><linearGradient id="wipe" x1="0%" y1="0%" x2="100%" y2="0%">'
        + f'<stop offset="0%" style="stop-color:{mc};stop-opacity:1"/>'
        + f'<stop offset="100%" style="stop-color:{mc};stop-opacity:0"/></linearGradient></defs>'
        + f'<rect width="1920" height="1080" fill="url(#wipe)"/>'
        + svg_close()
    )


def lower_third(ch_id: str) -> str:
    cfg = CHANNELS[ch_id]
    mc = cfg["main_color"]
    bg = "#1A1A1A" if cfg["bg_color"] == "#FFFFFF" else cfg["bg_color"]
    return (
        svg_open(1920, 200, bg)
        + f'<rect x="40" y="20" width="8" height="160" fill="{mc}" rx="4"/>'
        + f'<text x="72" y="90" font-size="52" fill="#FFFFFF" '
        + f'font-family="Gmarket Sans Bold,sans-serif" font-weight="900">이름 / 출처</text>'
        + f'<text x="72" y="148" font-size="34" fill="{mc}" '
        + f'font-family="Gmarket Sans,sans-serif">{cfg["name"]} · {cfg["domain"]}</text>'
        + svg_close()
    )


TEMPLATES: dict = {
    "subtitle_bar.svg": subtitle_bar,
    "thumbnail_template.svg": thumbnail_template,
    "transition_wipe.svg": transition_wipe,
    "lower_third.svg": lower_third,
}


def generate_templates(ch_id: str) -> None:
    out_dir = CHANNELS_DIR / ch_id / "templates"
    out_dir.mkdir(parents=True, exist_ok=True)
    for fname, fn in TEMPLATES.items():
        (out_dir / fname).write_text(fn(ch_id), encoding="utf-8")
    logger.info(f"[OK] {ch_id} 템플릿 4종 생성")


if __name__ == "__main__":
    if hasattr(sys.stdout, "buffer"):
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    for ch_id in CHANNELS:
        generate_templates(ch_id)
    logger.info("7채널 템플릿 SVG 생성 완료")
