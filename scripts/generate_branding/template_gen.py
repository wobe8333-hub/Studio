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


# ─── CH1 전용 자막바/로어써드 (4종) ─────────────────────────────────────────

def ch1_subtitle_bar_basic(ch_id: str) -> str:
    """기본 자막바: 검정 배경 + 골드 테두리 + 흰 텍스트."""
    cfg = CHANNELS[ch_id]
    mc = cfg["main_color"]
    sec = cfg.get("secondary_color", "#333333")
    return (
        svg_open(1280, 120, sec)
        + doodle_rect(4, 4, 1272, 112, mc, sw=3, rx=6)
        + f'<text x="640" y="78" font-size="46" fill="#FFFFFF" '
        + 'font-family="Gmarket Sans Bold,sans-serif" text-anchor="middle" font-weight="900">자막 텍스트 영역</text>'
        + svg_close()
    )


def ch1_subtitle_bar_emphasis(ch_id: str) -> str:
    """강조 자막바: 골드 배경 + 검정 테두리 + 검정 텍스트."""
    cfg = CHANNELS[ch_id]
    mc = cfg["main_color"]
    sec = cfg.get("secondary_color", "#333333")
    return (
        svg_open(1280, 120, mc)
        + doodle_rect(4, 4, 1272, 112, sec, sw=3, rx=6)
        + f'<text x="640" y="78" font-size="46" fill="{sec}" '
        + 'font-family="Gmarket Sans Bold,sans-serif" text-anchor="middle" font-weight="900">강조 텍스트 영역</text>'
        + svg_close()
    )


def ch1_subtitle_bar_L(ch_id: str) -> str:
    """L자형 로어써드: 세로+가로 바 + 채널 정보."""
    cfg = CHANNELS[ch_id]
    mc = cfg["main_color"]
    sec = cfg.get("secondary_color", "#333333")
    return (
        svg_open(1920, 200, "none")
        + f'<rect x="40" y="20" width="6" height="160" fill="{mc}" rx="3"/>'
        + f'<rect x="40" y="160" width="600" height="6" fill="{mc}" rx="3"/>'
        + f'<rect x="46" y="26" width="600" height="128" fill="{sec}" opacity="0.88" rx="4"/>'
        + f'<text x="72" y="90" font-size="48" fill="#FFFFFF" '
        + 'font-family="Gmarket Sans Bold,sans-serif" font-weight="900">이름 · 직함</text>'
        + f'<text x="72" y="140" font-size="30" fill="{mc}" '
        + f'font-family="Gmarket Sans,sans-serif">{cfg["name"]} · {cfg["domain"]}</text>'
        + svg_close()
    )


def ch1_subtitle_bar_bubble(ch_id: str) -> str:
    """말풍선 자막바."""
    cfg = CHANNELS[ch_id]
    mc = cfg["main_color"]
    sec = cfg.get("secondary_color", "#333333")
    return (
        svg_open(800, 180, "none")
        + f'<rect x="8" y="8" width="784" height="120" fill="{mc}" '
        + f'stroke="{sec}" stroke-width="3" rx="16"/>'
        + f'<polygon points="80,128 130,128 95,172" fill="{mc}" '
        + f'stroke="{sec}" stroke-width="3" stroke-linejoin="round"/>'
        + f'<text x="400" y="76" font-size="42" fill="{sec}" '
        + 'font-family="Gmarket Sans Bold,sans-serif" text-anchor="middle" font-weight="900">말풍선 텍스트</text>'
        + svg_close()
    )


# ─── CH1 전용 썸네일 템플릿 (5종) ────────────────────────────────────────────

def ch1_thumbnail_standard(ch_id: str) -> str:
    """표준 썸네일: 캐릭터 좌+제목 우."""
    cfg = CHANNELS[ch_id]
    mc, sec = cfg["main_color"], cfg.get("secondary_color", "#333333")
    return (
        svg_open(1280, 720, "#FFFFFF")
        + doodle_rect(6, 6, 1268, 708, mc, sw=5, rx=12)
        + doodle_rect(24, 24, 600, 672, sec, sw=2, rx=8)
        + f'<text x="324" y="380" font-size="18" fill="{sec}" text-anchor="middle" opacity="0.4">캐릭터 영역</text>'
        + doodle_rect(648, 24, 608, 320, mc, sw=2, rx=8)
        + f'<text x="952" y="200" font-size="18" fill="{mc}" text-anchor="middle" opacity="0.6">제목 영역</text>'
        + doodle_rect(648, 368, 608, 328, sec, sw=2, rx=8)
        + f'<text x="952" y="540" font-size="32" fill="#FFFFFF" text-anchor="middle" '
        + f'font-family="Gmarket Sans Bold,sans-serif" font-weight="900">{cfg["name"]}</text>'
        + svg_close()
    )


def ch1_thumbnail_impact(ch_id: str) -> str:
    """임팩트 썸네일: 큰 텍스트 중앙 + 사이드 캐릭터."""
    cfg = CHANNELS[ch_id]
    mc, sec = cfg["main_color"], cfg.get("secondary_color", "#333333")
    return (
        svg_open(1280, 720, sec)
        + doodle_rect(6, 6, 1268, 708, mc, sw=6, rx=0)
        + f'<text x="640" y="340" font-size="96" fill="{mc}" text-anchor="middle" '
        + f'font-family="Gmarket Sans Bold,sans-serif" font-weight="900">제목</text>'
        + f'<text x="640" y="430" font-size="40" fill="#FFFFFF" text-anchor="middle" '
        + f'font-family="Gmarket Sans,sans-serif">부제목 / 키워드</text>'
        + doodle_rect(1040, 100, 200, 520, mc, sw=2, rx=8)
        + f'<text x="1140" y="370" font-size="14" fill="{mc}" text-anchor="middle" opacity="0.5">캐릭터</text>'
        + svg_close()
    )


def ch1_thumbnail_compare(ch_id: str) -> str:
    """좌우비교 썸네일."""
    cfg = CHANNELS[ch_id]
    mc = cfg["main_color"]
    sec = cfg.get("secondary_color", "#333333")
    red = cfg.get("accent_red", "#DC2626")
    green = cfg.get("accent_green", "#16A34A")
    return (
        svg_open(1280, 720, "#FFFFFF")
        + doodle_rect(6, 6, 624, 708, red, sw=4, rx=8)
        + f'<text x="318" y="380" font-size="28" fill="{red}" text-anchor="middle">좌측 항목</text>'
        + doodle_rect(650, 6, 624, 708, green, sw=4, rx=8)
        + f'<text x="962" y="380" font-size="28" fill="{green}" text-anchor="middle">우측 항목</text>'
        + f'<rect x="620" y="0" width="40" height="720" fill="{mc}"/>'
        + f'<text x="640" y="370" font-size="36" fill="{sec}" text-anchor="middle" font-weight="900">VS</text>'
        + svg_close()
    )


def ch1_thumbnail_question(ch_id: str) -> str:
    """질문형 썸네일: 물음표 강조."""
    cfg = CHANNELS[ch_id]
    mc, sec = cfg["main_color"], cfg.get("secondary_color", "#333333")
    return (
        svg_open(1280, 720, "#FFF8E7")
        + doodle_rect(6, 6, 1268, 708, mc, sw=5, rx=12)
        + f'<text x="200" y="480" font-size="400" fill="{mc}" text-anchor="middle" opacity="0.15" '
        + f'font-family="Georgia,serif" font-weight="900">?</text>'
        + doodle_rect(380, 100, 860, 520, sec, sw=2, rx=8)
        + f'<text x="810" y="380" font-size="28" fill="#FFFFFF" text-anchor="middle">질문 텍스트 영역</text>'
        + svg_close()
    )


def ch1_thumbnail_urgent(ch_id: str) -> str:
    """긴급 썸네일: 빨간 강조 테두리."""
    cfg = CHANNELS[ch_id]
    mc = cfg["main_color"]
    sec = cfg.get("secondary_color", "#333333")
    red = cfg.get("accent_red", "#DC2626")
    return (
        svg_open(1280, 720, "#FFFFFF")
        + doodle_rect(6, 6, 1268, 708, red, sw=8, rx=4)
        + f'<rect x="6" y="6" width="1268" height="80" fill="{red}"/>'
        + f'<text x="640" y="60" font-size="38" fill="#FFFFFF" text-anchor="middle" '
        + f'font-family="Gmarket Sans Bold,sans-serif" font-weight="900">긴급 · BREAKING</text>'
        + doodle_rect(24, 110, 1232, 580, sec, sw=2, rx=6)
        + f'<text x="640" y="420" font-size="24" fill="{mc}" text-anchor="middle">제목 및 내용 영역</text>'
        + svg_close()
    )


# ─── CH1 전용 섹션구분자 (3종) ────────────────────────────────────────────────

def ch1_section_divider_basic(ch_id: str) -> str:
    cfg = CHANNELS[ch_id]
    mc = cfg["main_color"]
    return (
        svg_open(1920, 60, "none")
        + f'<line x1="0" y1="30" x2="1920" y2="30" stroke="{mc}" stroke-width="3" stroke-dasharray="12,6"/>'
        + svg_close()
    )


def ch1_section_divider_title(ch_id: str) -> str:
    cfg = CHANNELS[ch_id]
    mc, sec = cfg["main_color"], cfg.get("secondary_color", "#333333")
    return (
        svg_open(1920, 100, "none")
        + f'<rect x="0" y="0" width="1920" height="100" fill="{mc}" rx="0"/>'
        + f'<text x="960" y="66" font-size="44" fill="{sec}" text-anchor="middle" '
        + f'font-family="Gmarket Sans Bold,sans-serif" font-weight="900">섹션 제목</text>'
        + svg_close()
    )


def ch1_section_divider_box(ch_id: str) -> str:
    cfg = CHANNELS[ch_id]
    mc = cfg["main_color"]
    sec = cfg.get("secondary_color", "#333333")
    return (
        svg_open(1280, 160, "none")
        + doodle_rect(0, 0, 1280, 160, mc, sw=4, rx=12)
        + f'<text x="640" y="94" font-size="44" fill="{sec}" text-anchor="middle" '
        + f'font-family="Gmarket Sans Bold,sans-serif" font-weight="900">강조 박스 텍스트</text>'
        + svg_close()
    )


# ─── CH2~7 공통 템플릿 (4종) ─────────────────────────────────────────────────
TEMPLATES: dict = {
    "subtitle_bar.svg": subtitle_bar,
    "thumbnail_template.svg": thumbnail_template,
    "transition_wipe.svg": transition_wipe,
    "lower_third.svg": lower_third,
}

# ─── CH1 전용 템플릿 (12종) ────────────────────────────────────────────────────
CH1_TEMPLATES: dict = {
    "subtitle_bar_basic.svg":      ch1_subtitle_bar_basic,
    "subtitle_bar_emphasis.svg":   ch1_subtitle_bar_emphasis,
    "subtitle_bar_L.svg":          ch1_subtitle_bar_L,
    "subtitle_bar_bubble.svg":     ch1_subtitle_bar_bubble,
    "thumbnail_standard.svg":      ch1_thumbnail_standard,
    "thumbnail_impact.svg":        ch1_thumbnail_impact,
    "thumbnail_compare.svg":       ch1_thumbnail_compare,
    "thumbnail_question.svg":      ch1_thumbnail_question,
    "thumbnail_urgent.svg":        ch1_thumbnail_urgent,
    "section_divider_basic.svg":   ch1_section_divider_basic,
    "section_divider_title.svg":   ch1_section_divider_title,
    "section_divider_box.svg":     ch1_section_divider_box,
}

# ─── CH1 트랜지션 SVG (5종, transitions/ 폴더) ────────────────────────────────
def _tr_ink(ch_id: str) -> str:
    mc = CHANNELS[ch_id]["main_color"]
    return (
        svg_open(1920, 1080)
        + '<defs><radialGradient id="ink" cx="50%" cy="50%" r="70%">'
        + f'<stop offset="0%" style="stop-color:{mc};stop-opacity:1"/>'
        + f'<stop offset="100%" style="stop-color:{mc};stop-opacity:0"/>'
        + '</radialGradient></defs>'
        + '<ellipse cx="960" cy="540" rx="960" ry="540" fill="url(#ink)"/>'
        + svg_close()
    )

def _tr_zoom(ch_id: str) -> str:
    mc = CHANNELS[ch_id]["main_color"]
    sec = CHANNELS[ch_id].get("secondary_color", "#333333")
    return (
        svg_open(1920, 1080, sec)
        + f'<circle cx="960" cy="540" r="800" fill="{mc}" opacity="0.9"/>'
        + f'<circle cx="960" cy="540" r="400" fill="{sec}"/>'
        + svg_close()
    )

def _tr_slide(ch_id: str) -> str:
    mc = CHANNELS[ch_id]["main_color"]
    sec = CHANNELS[ch_id].get("secondary_color", "#333333")
    return (
        svg_open(1920, 1080, sec)
        + f'<rect x="0" y="0" width="960" height="1080" fill="{mc}"/>'
        + svg_close()
    )

def _tr_paper(ch_id: str) -> str:
    mc = CHANNELS[ch_id]["main_color"]
    return (
        svg_open(1920, 1080, "#FFFFFF")
        + '<defs><linearGradient id="paper" x1="0%" y1="0%" x2="100%" y2="100%">'
        + f'<stop offset="0%" style="stop-color:{mc};stop-opacity:1"/>'
        + '<stop offset="60%" style="stop-color:#FFFDF5;stop-opacity:1"/>'
        + '<stop offset="100%" style="stop-color:#FFFFFF;stop-opacity:0"/>'
        + '</linearGradient></defs>'
        + '<rect width="1920" height="1080" fill="url(#paper)"/>'
        + svg_close()
    )

def _tr_fade(ch_id: str) -> str:
    mc = CHANNELS[ch_id]["main_color"]
    return (
        svg_open(1920, 1080, mc)
        + svg_close()
    )

CH1_TRANSITIONS: dict = {
    "transition_ink.svg":   _tr_ink,
    "transition_zoom.svg":  _tr_zoom,
    "transition_slide.svg": _tr_slide,
    "transition_paper.svg": _tr_paper,
    "transition_fade.svg":  _tr_fade,
}


def generate_templates(ch_id: str) -> None:
    """채널별 SVG 템플릿 생성. CH1은 12종, CH2~7은 4종."""
    out_dir = CHANNELS_DIR / ch_id / "templates"
    out_dir.mkdir(parents=True, exist_ok=True)
    templates = CH1_TEMPLATES if ch_id == "CH1" else TEMPLATES
    for fname, fn in templates.items():
        (out_dir / fname).write_text(fn(ch_id), encoding="utf-8")
    logger.info(f"[OK] {ch_id} 템플릿 {len(templates)}종 생성")


def generate_transitions(ch_id: str) -> None:
    """transitions/ 폴더에 전환 SVG 5종 생성 (CH1 전용)."""
    out_dir = CHANNELS_DIR / ch_id / "transitions"
    out_dir.mkdir(parents=True, exist_ok=True)
    transitions = CH1_TRANSITIONS if ch_id == "CH1" else {}
    for fname, fn in transitions.items():
        (out_dir / fname).write_text(fn(ch_id), encoding="utf-8")
    if transitions:
        logger.info(f"[OK] {ch_id} 트랜지션 {len(transitions)}종 생성")


if __name__ == "__main__":
    if hasattr(sys.stdout, "buffer"):
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    for ch_id in CHANNELS:
        generate_templates(ch_id)
        generate_transitions(ch_id)
    logger.info("7채널 템플릿 SVG 생성 완료")
