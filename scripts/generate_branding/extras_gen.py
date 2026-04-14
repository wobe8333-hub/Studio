# scripts/generate_branding/extras_gen.py
"""채널 아트(2560×1440) + 프로필 배너(800×800) SVG 생성"""
import sys
import io

from pathlib import Path
from loguru import logger

sys.path.insert(0, str(Path(__file__).parent))
from config import CHANNELS, CHANNELS_DIR
from svg_helpers import svg_open, svg_close, doodle_circle, doodle_line


def channel_art(ch_id: str) -> str:
    cfg = CHANNELS[ch_id]
    mc = cfg["main_color"]
    bg = cfg["bg_color"]
    sc = cfg["sub_colors"][0]
    name = cfg["name"]
    domain = cfg["domain"]
    W, H = 2560, 1440
    CX, CY = W // 2, H // 2
    return (
        svg_open(W, H, bg)
        + doodle_circle(CX, CY, 580, mc, sw=3)
        + doodle_circle(CX, CY, 520, mc, sw=1)
        + doodle_circle(200, 200, 120, sc, sw=2)
        + doodle_circle(W - 200, H - 200, 100, sc, sw=2)
        + doodle_circle(200, H - 200, 80, mc, sw=2)
        + doodle_circle(W - 200, 200, 90, mc, sw=2)
        + f'<text x="{CX}" y="{CY - 40}" font-size="180" fill="{mc}" '
        + f'font-family="Gmarket Sans Bold,sans-serif" text-anchor="middle" font-weight="900">{name}</text>'
        + f'<text x="{CX}" y="{CY + 100}" font-size="80" fill="{sc}" '
        + f'font-family="Gmarket Sans,sans-serif" text-anchor="middle">{domain} 채널</text>'
        + doodle_line(CX - 400, CY + 180, CX + 400, CY + 180, mc, sw=4)
        + svg_close()
    )


def profile_banner(ch_id: str) -> str:
    cfg = CHANNELS[ch_id]
    mc = cfg["main_color"]
    bg = cfg["bg_color"]
    name = cfg["name"]
    W = H = 800
    CX = CY = 400
    return (
        svg_open(W, H, bg)
        + doodle_circle(CX, CY, 340, mc, sw=8)
        + doodle_circle(CX, CY, 310, mc, sw=3)
        + f'<text x="{CX}" y="{CY + 16}" font-size="88" fill="{mc}" '
        + f'font-family="Gmarket Sans Bold,sans-serif" text-anchor="middle" font-weight="900">{name}</text>'
        + svg_close()
    )


def generate_extras(ch_id: str) -> None:
    out_dir = CHANNELS_DIR / ch_id / "extras"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "channel_art.svg").write_text(channel_art(ch_id), encoding="utf-8")
    (out_dir / "profile_banner.svg").write_text(profile_banner(ch_id), encoding="utf-8")
    logger.info(f"[OK] {ch_id} extras 2종 생성")


if __name__ == "__main__":
    if hasattr(sys.stdout, "buffer"):
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    for ch_id in CHANNELS:
        generate_extras(ch_id)
    logger.info("7채널 채널아트·배너 SVG 생성 완료")
