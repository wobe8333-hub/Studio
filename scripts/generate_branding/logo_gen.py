# scripts/generate_branding/logo_gen.py
"""7채널 로고 SVG 생성 — 두들 원형 배지 스타일 (500x500px)"""
import io
import sys
from pathlib import Path

from loguru import logger

sys.path.insert(0, str(Path(__file__).parent))
from svg_helpers import (
    doodle_circle,
    doodle_crown,
    doodle_line,
    doodle_path,
    doodle_rect,
    doodle_star,
    doodle_text,
    svg_close,
    svg_open,
)

from config import CHANNELS, CHANNELS_DIR


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
    logger.info(f"[OK] {ch_id} 로고 SVG → {out.name}")

    # SVG 저장 후 PNG 래스터화
    rasterize_logo(ch_id)


def rasterize_logo(ch_id: str) -> tuple[Path, Path]:
    """SVG 로고 → PNG 1024px (logo.png) + 256px (logo_sm.png) 래스터화.

    cairosvg가 설치되어 있으면 SVG를 정확하게 래스터화한다.
    없으면 Pillow로 원형 배지 PNG를 직접 생성한다.

    Returns:
        (logo_png_path, logo_sm_png_path) 튜플
    """
    svg_path = CHANNELS_DIR / ch_id / "logo" / "logo.svg"
    png_1024 = CHANNELS_DIR / ch_id / "logo" / "logo.png"
    png_256  = CHANNELS_DIR / ch_id / "logo" / "logo_sm.png"
    png_1024.parent.mkdir(parents=True, exist_ok=True)

    try:
        import cairosvg
        cairosvg.svg2png(
            url=str(svg_path), write_to=str(png_1024),
            output_width=1024, output_height=1024,
        )
        cairosvg.svg2png(
            url=str(svg_path), write_to=str(png_256),
            output_width=256, output_height=256,
        )
        logger.info(f"[OK] {ch_id} 로고 PNG (cairosvg) → logo.png + logo_sm.png")
    except ImportError:
        # cairosvg 미설치 → Pillow 폴백
        logger.warning(f"[{ch_id}] cairosvg 없음 — Pillow 폴백으로 원형 배지 PNG 생성")
        _fallback_logo_png(ch_id, png_1024, 1024)
        _fallback_logo_png(ch_id, png_256, 256)

    return png_1024, png_256


def _fallback_logo_png(ch_id: str, out_path: Path, size: int) -> None:
    """cairosvg 미설치 시 Pillow로 원형 배지 PNG 직접 생성.

    채널 메인 컬러와 배경 컬러를 사용해 간결한 원형 배지를 그린다.
    """
    from PIL import Image, ImageDraw, ImageFont

    cfg = CHANNELS[ch_id]

    # 색상 파싱 헬퍼 (config.py에 의존하지 않기 위해 인라인)
    def _hex_to_rgba(hex_color: str, alpha: int = 255) -> tuple[int, int, int, int]:
        h = hex_color.lstrip("#")
        r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
        return (r, g, b, alpha)

    main_rgba = _hex_to_rgba(cfg["main_color"])
    bg_rgba   = _hex_to_rgba(cfg["bg_color"])

    img  = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    cx, cy = size // 2, size // 2
    r = int(size * 0.42)

    # 배경 원
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=bg_rgba)
    # 외곽선
    lw = max(2, size // 80)
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], outline=main_rgba, width=lw)

    # 채널명 텍스트 (하단)
    font_size = max(10, size // 8)
    try:
        font = ImageFont.truetype("arial.ttf", font_size)
    except Exception:
        font = ImageFont.load_default()
    draw.text(
        (cx, cy + int(r * 0.55)),
        cfg["name"],
        fill=main_rgba,
        font=font,
        anchor="mm",
    )

    img.save(str(out_path))
    logger.info(f"[OK] {ch_id} 로고 PNG fallback → {out_path.name} ({size}px)")


if __name__ == "__main__":
    if hasattr(sys.stdout, "buffer"):
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    for ch_id in CHANNELS:
        generate_logo(ch_id)
    logger.info("7채널 로고 SVG + PNG 생성 완료")
