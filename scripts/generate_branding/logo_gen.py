# scripts/generate_branding/logo_gen.py
"""7채널 로고 SVG 생성 — 두들 원형 배지 스타일 (500x500px)"""
import sys
import io

from pathlib import Path
from loguru import logger

sys.path.insert(0, str(Path(__file__).parent))
from config import CHANNELS, CHANNELS_DIR
from svg_helpers import (
    svg_open, svg_close, doodle_circle, doodle_text,
    doodle_path, doodle_crown, doodle_star, doodle_line, doodle_rect, group
)


def _draw_economy_icon(cx, cy, size, color):
    """왕관 아이콘 — CH1 경제"""
    return doodle_crown(cx, cy - size * 0.15, size * 0.35, color, sw=3)


def _draw_science_icon(cx, cy, size, color):
    """플라스크 아이콘 — CH2 과학"""
    s = size * 0.3
    flask = doodle_path(
        f"M {cx - s * 0.4},{cy - s} L {cx - s * 0.6},{cy + s * 0.5} "
        f"Q {cx},{cy + s * 1.2} {cx + s * 0.6},{cy + s * 0.5} L {cx + s * 0.4},{cy - s} Z",
        color, sw=3
    )
    cap = doodle_line(cx - s * 0.5, cy - s, cx + s * 0.5, cy - s, color, sw=3)
    return flask + cap


def _draw_house_icon(cx, cy, size, color):
    """집 아이콘 — CH3 부동산"""
    s = size * 0.3
    body = doodle_path(
        f"M {cx},{cy - s} L {cx + s},{cy} L {cx + s},{cy + s} "
        f"L {cx - s},{cy + s} L {cx - s},{cy} Z",
        color, sw=3
    )
    roof = doodle_path(
        f"M {cx - s * 1.2},{cy} L {cx},{cy - s * 1.3} L {cx + s * 1.2},{cy}",
        color, sw=3
    )
    return body + roof


def _draw_brain_icon(cx, cy, size, color):
    """뇌 아이콘 — CH4 심리"""
    r = size * 0.28
    left = doodle_circle(cx - r * 0.5, cy, r, color, sw=3)
    right = doodle_circle(cx + r * 0.5, cy, r, color, sw=3)
    mid = doodle_line(cx, cy - r, cx, cy + r, color, sw=2)
    return left + right + mid


def _draw_question_icon(cx, cy, size, color):
    """물음표 아이콘 — CH5 미스터리"""
    s = size * 0.3
    q = doodle_path(
        f"M {cx - s * 0.5},{cy - s} Q {cx - s * 0.5},{cy - s * 1.5} {cx},{cy - s * 1.5} "
        f"Q {cx + s * 0.5},{cy - s * 1.5} {cx + s * 0.5},{cy - s} "
        f"Q {cx + s * 0.5},{cy - s * 0.3} {cx},{cy} L {cx},{cy + s * 0.3}",
        color, sw=4
    )
    dot = doodle_circle(cx, cy + s * 0.7, s * 0.15, color, sw=3, fill=color)
    return q + dot


def _draw_scroll_icon(cx, cy, size, color):
    """두루마리 아이콘 — CH6 역사"""
    s = size * 0.3
    body = doodle_rect(cx - s, cy - s * 0.7, s * 2, s * 1.4, color, sw=3)
    lroll = doodle_circle(cx - s, cy, s * 0.25, color, sw=3)
    rroll = doodle_circle(cx + s, cy, s * 0.25, color, sw=3)
    l1 = doodle_line(cx - s * 0.6, cy - s * 0.3, cx + s * 0.6, cy - s * 0.3, color, sw=2)
    l2 = doodle_line(cx - s * 0.6, cy, cx + s * 0.6, cy, color, sw=2)
    l3 = doodle_line(cx - s * 0.6, cy + s * 0.3, cx + s * 0.6, cy + s * 0.3, color, sw=2)
    return body + lroll + rroll + l1 + l2 + l3


def _draw_sword_icon(cx, cy, size, color):
    """교차 검 아이콘 — CH7 전쟁사"""
    s = size * 0.35
    s1 = doodle_line(cx - s, cy - s, cx + s, cy + s, color, sw=4)
    s2 = doodle_line(cx + s, cy - s, cx - s, cy + s, color, sw=4)
    center = doodle_star(cx, cy, s * 0.15, color, sw=2)
    return s1 + s2 + center


DOMAIN_ICON_FN = {
    "경제": _draw_economy_icon,
    "과학": _draw_science_icon,
    "부동산": _draw_house_icon,
    "심리": _draw_brain_icon,
    "미스터리": _draw_question_icon,
    "역사": _draw_scroll_icon,
    "전쟁사": _draw_sword_icon,
}


def generate_logo(ch_id: str) -> None:
    cfg = CHANNELS[ch_id]
    w, h = 500, 500
    cx, cy, r = 250, 250, 200
    main = cfg["main_color"]
    bg = cfg["bg_color"]
    name = cfg["name"]

    icon_fn = DOMAIN_ICON_FN.get(cfg["domain"], _draw_economy_icon)
    icon_svg = icon_fn(cx, cy - 40, r, main)

    parts = [
        svg_open(w, h, bg_color=bg),
        # 외곽 두들 원 (이중)
        doodle_circle(cx, cy, r, main, sw=6),
        doodle_circle(cx, cy, r - 12, main, sw=2),
        # 도메인 아이콘
        icon_svg,
        # 채널명 텍스트
        doodle_text(name, cx, cy + int(r * 0.55), size=36, color=main),
        svg_close(),
    ]
    content = "\n".join(parts)
    out = CHANNELS_DIR / ch_id / "logo" / "logo.svg"
    out.write_text(content, encoding="utf-8")
    logger.info(f"[OK] {ch_id} 로고 → {out.name}")


if __name__ == "__main__":
    if hasattr(sys.stdout, "buffer"):
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    for ch_id in CHANNELS:
        generate_logo(ch_id)
    logger.info("7채널 로고 SVG 생성 완료")
