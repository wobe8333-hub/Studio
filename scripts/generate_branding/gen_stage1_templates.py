"""1단계: 자막바·장면전환·로워서드 10종 × 7채널 SVG 생성.

사용법:
    python scripts/generate_branding/gen_stage1_templates.py
"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.path.insert(0, str(__file__).split("scripts")[0])

from pathlib import Path
from loguru import logger
from scripts.generate_branding.config import CHANNELS, CHANNELS_DIR
from scripts.generate_branding.svg_helpers import svg_open, svg_close, doodle_rect


# ─── 자막바 10종 ──────────────────────────────────────────────────────────────

def _subtitle_bars(ch_id: str) -> dict[str, str]:
    c = CHANNELS[ch_id]
    mc = c["main_color"]
    sec = c.get("secondary_color", "#333333")
    bg = c["bg_color"]
    subs = c.get("sub_colors", [mc, sec, "#FFFFFF"])
    sc1 = subs[0] if len(subs) > 0 else mc
    sc2 = subs[1] if len(subs) > 1 else sec
    dark = "#1A1A1A" if bg == "#FFFFFF" else bg
    W, H = 1280, 120

    def txt(x, y, size, fill, content, bold=True):
        weight = "900" if bold else "400"
        return (f'<text x="{x}" y="{y}" font-size="{size}" fill="{fill}" '
                f'font-family="Gmarket Sans Bold,sans-serif" text-anchor="middle" '
                f'font-weight="{weight}">{content}</text>')

    return {
        "subtitle_bar_01.svg": (  # 기본: 어두운 배경 + 메인컬러 테두리
            svg_open(W, H, dark)
            + doodle_rect(4, 4, W-8, H-8, mc, sw=3, rx=6)
            + txt(W//2, 78, 46, "#FFFFFF", "자막 텍스트 영역")
            + svg_close()
        ),
        "subtitle_bar_02.svg": (  # 강조: 메인컬러 배경
            svg_open(W, H, mc)
            + doodle_rect(4, 4, W-8, H-8, sec, sw=3, rx=6)
            + txt(W//2, 78, 46, sec, "강조 텍스트 영역")
            + svg_close()
        ),
        "subtitle_bar_03.svg": (  # 미니멀: 하단 선만
            svg_open(W, H, "none")
            + f'<rect x="0" y="{H-6}" width="{W}" height="6" fill="{mc}" rx="3"/>'
            + txt(W//2, 80, 46, sec, "자막 텍스트 영역")
            + svg_close()
        ),
        "subtitle_bar_04.svg": (  # 둥근 필
            svg_open(W, H, "none")
            + f'<rect x="40" y="10" width="{W-80}" height="{H-20}" fill="{mc}" rx="{(H-20)//2}"/>'
            + txt(W//2, 76, 44, "#FFFFFF" if mc != "#FFFFFF" else sec, "자막 텍스트 영역")
            + svg_close()
        ),
        "subtitle_bar_05.svg": (  # 좌측 액센트 바
            svg_open(W, H, dark)
            + f'<rect x="0" y="0" width="10" height="{H}" fill="{mc}" rx="0"/>'
            + txt(W//2 + 5, 78, 46, "#FFFFFF", "자막 텍스트 영역")
            + svg_close()
        ),
        "subtitle_bar_06.svg": (  # 이중 테두리
            svg_open(W, H, dark)
            + doodle_rect(4, 4, W-8, H-8, mc, sw=4, rx=8)
            + doodle_rect(12, 12, W-24, H-24, mc, sw=2, rx=4)
            + txt(W//2, 78, 42, "#FFFFFF", "자막 텍스트 영역")
            + svg_close()
        ),
        "subtitle_bar_07.svg": (  # 점선 테두리
            svg_open(W, H, dark)
            + f'<rect x="4" y="4" width="{W-8}" height="{H-8}" fill="none" '
            + f'stroke="{mc}" stroke-width="3" stroke-dasharray="16,8" rx="6"/>'
            + txt(W//2, 78, 46, mc, "자막 텍스트 영역")
            + svg_close()
        ),
        "subtitle_bar_08.svg": (  # 그라디언트 배경
            svg_open(W, H)
            + f'<defs><linearGradient id="g8_{ch_id}" x1="0%" y1="0%" x2="100%" y2="0%">'
            + f'<stop offset="0%" style="stop-color:{mc};stop-opacity:1"/>'
            + f'<stop offset="100%" style="stop-color:{sc1};stop-opacity:0.7"/>'
            + f'</linearGradient></defs>'
            + f'<rect width="{W}" height="{H}" fill="url(#g8_{ch_id})"/>'
            + txt(W//2, 78, 46, "#FFFFFF", "자막 텍스트 영역")
            + svg_close()
        ),
        "subtitle_bar_09.svg": (  # 채널명 워터마크
            svg_open(W, H, dark)
            + doodle_rect(4, 4, W-8, H-8, mc, sw=3, rx=6)
            + txt(W//2, 78, 42, "#FFFFFF", "자막 텍스트 영역")
            + f'<text x="{W-20}" y="{H-14}" font-size="18" fill="{mc}" '
            + f'text-anchor="end" opacity="0.7">{c["name"]}</text>'
            + svg_close()
        ),
        "subtitle_bar_10.svg": (  # 굵은 테두리 + 서브컬러
            svg_open(W, H, dark)
            + doodle_rect(2, 2, W-4, H-4, sc2, sw=6, rx=0)
            + doodle_rect(10, 10, W-20, H-20, mc, sw=3, rx=4)
            + txt(W//2, 78, 44, "#FFFFFF", "자막 텍스트 영역")
            + svg_close()
        ),
    }


# ─── 장면전환 10종 ────────────────────────────────────────────────────────────

def _transitions(ch_id: str) -> dict[str, str]:
    c = CHANNELS[ch_id]
    mc = c["main_color"]
    sec = c.get("secondary_color", "#333333")
    subs = c.get("sub_colors", [mc])
    sc1 = subs[0] if subs else mc
    W, H = 1920, 1080

    return {
        "transition_01.svg": (  # 좌→우 와이프
            svg_open(W, H)
            + f'<defs><linearGradient id="t1_{ch_id}" x1="0%" y1="0%" x2="100%" y2="0%">'
            + f'<stop offset="0%" style="stop-color:{mc};stop-opacity:1"/>'
            + f'<stop offset="100%" style="stop-color:{mc};stop-opacity:0"/>'
            + f'</linearGradient></defs>'
            + f'<rect width="{W}" height="{H}" fill="url(#t1_{ch_id})"/>'
            + svg_close()
        ),
        "transition_02.svg": (  # 우→좌 와이프
            svg_open(W, H)
            + f'<defs><linearGradient id="t2_{ch_id}" x1="100%" y1="0%" x2="0%" y2="0%">'
            + f'<stop offset="0%" style="stop-color:{mc};stop-opacity:1"/>'
            + f'<stop offset="100%" style="stop-color:{mc};stop-opacity:0"/>'
            + f'</linearGradient></defs>'
            + f'<rect width="{W}" height="{H}" fill="url(#t2_{ch_id})"/>'
            + svg_close()
        ),
        "transition_03.svg": (  # 잉크 블롯
            svg_open(W, H)
            + f'<defs><radialGradient id="t3_{ch_id}" cx="50%" cy="50%" r="70%">'
            + f'<stop offset="0%" style="stop-color:{mc};stop-opacity:1"/>'
            + f'<stop offset="100%" style="stop-color:{mc};stop-opacity:0"/>'
            + f'</radialGradient></defs>'
            + f'<ellipse cx="{W//2}" cy="{H//2}" rx="{W//2}" ry="{H//2}" fill="url(#t3_{ch_id})"/>'
            + svg_close()
        ),
        "transition_04.svg": (  # 줌 동심원
            svg_open(W, H, sec)
            + f'<circle cx="{W//2}" cy="{H//2}" r="800" fill="{mc}" opacity="0.9"/>'
            + f'<circle cx="{W//2}" cy="{H//2}" r="400" fill="{sec}"/>'
            + svg_close()
        ),
        "transition_05.svg": (  # 수직 슬라이드
            svg_open(W, H, sec)
            + f'<rect x="0" y="0" width="{W//2}" height="{H}" fill="{mc}"/>'
            + svg_close()
        ),
        "transition_06.svg": (  # 페이퍼 폴드
            svg_open(W, H, "#FFFFFF")
            + f'<defs><linearGradient id="t6_{ch_id}" x1="0%" y1="0%" x2="100%" y2="100%">'
            + f'<stop offset="0%" style="stop-color:{mc};stop-opacity:1"/>'
            + f'<stop offset="60%" style="stop-color:#FFFDF5;stop-opacity:1"/>'
            + f'<stop offset="100%" style="stop-color:#FFFFFF;stop-opacity:0"/>'
            + f'</linearGradient></defs>'
            + f'<rect width="{W}" height="{H}" fill="url(#t6_{ch_id})"/>'
            + svg_close()
        ),
        "transition_07.svg": (  # 솔리드 페이드
            svg_open(W, H, mc) + svg_close()
        ),
        "transition_08.svg": (  # 대각선 와이프
            svg_open(W, H)
            + f'<defs><linearGradient id="t8_{ch_id}" x1="0%" y1="0%" x2="100%" y2="100%">'
            + f'<stop offset="0%" style="stop-color:{mc};stop-opacity:1"/>'
            + f'<stop offset="50%" style="stop-color:{mc};stop-opacity:0.5"/>'
            + f'<stop offset="100%" style="stop-color:{mc};stop-opacity:0"/>'
            + f'</linearGradient></defs>'
            + f'<polygon points="0,0 {W},0 0,{H}" fill="url(#t8_{ch_id})"/>'
            + svg_close()
        ),
        "transition_09.svg": (  # 수평 스플릿
            svg_open(W, H)
            + f'<rect x="0" y="0" width="{W}" height="{H//2}" fill="{mc}"/>'
            + f'<rect x="0" y="{H//2}" width="{W}" height="{H//2}" fill="{sc1}"/>'
            + svg_close()
        ),
        "transition_10.svg": (  # 컬러 번개 (지그재그)
            svg_open(W, H, sec)
            + f'<polyline points="0,0 {W//4},{H//2} {W//2},0 {W*3//4},{H//2} {W},{0}" '
            + f'fill="{mc}" stroke="{mc}" stroke-width="4"/>'
            + f'<rect x="0" y="{H//2}" width="{W}" height="{H//2}" fill="{mc}" opacity="0.8"/>'
            + svg_close()
        ),
    }


# ─── 로워서드 10종 ────────────────────────────────────────────────────────────

def _lower_thirds(ch_id: str) -> dict[str, str]:
    c = CHANNELS[ch_id]
    mc = c["main_color"]
    sec = c.get("secondary_color", "#333333")
    bg = c["bg_color"]
    subs = c.get("sub_colors", [mc])
    sc1 = subs[0] if subs else mc
    dark = "#1A1A1A" if bg == "#FFFFFF" else bg
    W, H = 1920, 200
    name, domain = c["name"], c["domain"]

    def txt(x, y, size, fill, content, anchor="start", bold=True):
        weight = "900" if bold else "400"
        return (f'<text x="{x}" y="{y}" font-size="{size}" fill="{fill}" '
                f'font-family="Gmarket Sans Bold,sans-serif" text-anchor="{anchor}" '
                f'font-weight="{weight}">{content}</text>')

    return {
        "lower_third_01.svg": (  # 기본: 어두운 배경 + 좌측 액센트
            svg_open(W, H, dark)
            + f'<rect x="40" y="20" width="8" height="160" fill="{mc}" rx="4"/>'
            + txt(72, 90, 52, "#FFFFFF", "이름 / 출처")
            + txt(72, 148, 34, mc, f"{name} · {domain}", bold=False)
            + svg_close()
        ),
        "lower_third_02.svg": (  # 라이트: 메인컬러 배경
            svg_open(W, H, mc)
            + txt(60, 90, 52, "#FFFFFF" if mc != "#FFFFFF" else sec, "이름 / 출처")
            + txt(60, 148, 34, "#FFFFFF" if mc != "#FFFFFF" else sec, f"{name} · {domain}", bold=False)
            + svg_close()
        ),
        "lower_third_03.svg": (  # 미니멀: 선만
            svg_open(W, H, "none")
            + f'<line x1="40" y1="{H-10}" x2="900" y2="{H-10}" stroke="{mc}" stroke-width="3"/>'
            + txt(40, 100, 52, sec, "이름 / 출처")
            + txt(40, 158, 34, mc, f"{name} · {domain}", bold=False)
            + svg_close()
        ),
        "lower_third_04.svg": (  # 박스 스타일
            svg_open(W, H, "none")
            + f'<rect x="30" y="20" width="860" height="160" fill="{dark}" rx="8"/>'
            + f'<rect x="30" y="20" width="860" height="8" fill="{mc}" rx="4"/>'
            + txt(60, 100, 50, "#FFFFFF", "이름 / 출처")
            + txt(60, 158, 32, mc, f"{name} · {domain}", bold=False)
            + svg_close()
        ),
        "lower_third_05.svg": (  # 투톤 분할
            svg_open(W, H, "none")
            + f'<rect x="0" y="60" width="500" height="140" fill="{mc}"/>'
            + f'<rect x="500" y="60" width="700" height="140" fill="{dark}"/>'
            + txt(250, 150, 46, "#FFFFFF" if mc != "#FFFFFF" else sec, "이름", anchor="middle")
            + txt(850, 122, 34, "#FFFFFF", "/ 출처", bold=False)
            + txt(850, 168, 28, mc, f"{name}", bold=False)
            + svg_close()
        ),
        "lower_third_06.svg": (  # 투명 오버레이
            svg_open(W, H, "none")
            + f'<rect x="30" y="30" width="820" height="140" fill="{dark}" opacity="0.75" rx="6"/>'
            + f'<rect x="30" y="30" width="6" height="140" fill="{mc}"/>'
            + txt(52, 100, 50, "#FFFFFF", "이름 / 출처")
            + txt(52, 152, 32, mc, f"{name} · {domain}", bold=False)
            + svg_close()
        ),
        "lower_third_07.svg": (  # 이름+직함 스택
            svg_open(W, H, dark)
            + f'<rect x="0" y="0" width="{W}" height="4" fill="{mc}"/>'
            + txt(60, 80, 58, "#FFFFFF", "이름 영역")
            + txt(60, 140, 38, mc, "직함 · 소속", bold=False)
            + txt(60, 182, 26, "#AAAAAA", f"{name}", bold=False)
            + svg_close()
        ),
        "lower_third_08.svg": (  # 아이콘 플레이스홀더
            svg_open(W, H, dark)
            + f'<rect x="20" y="20" width="160" height="160" fill="{mc}" opacity="0.2" rx="8"/>'
            + f'<text x="100" y="112" font-size="40" fill="{mc}" text-anchor="middle">logo</text>'
            + f'<rect x="200" y="20" width="4" height="160" fill="{mc}"/>'
            + txt(224, 90, 50, "#FFFFFF", "이름 / 출처")
            + txt(224, 148, 34, mc, f"{name} · {domain}", bold=False)
            + svg_close()
        ),
        "lower_third_09.svg": (  # 볼드 임팩트
            svg_open(W, H, mc)
            + f'<rect x="0" y="0" width="{W}" height="6" fill="{sec}"/>'
            + f'<rect x="0" y="{H-6}" width="{W}" height="6" fill="{sec}"/>'
            + txt(W//2, 110, 64, "#FFFFFF" if mc != "#FFFFFF" else sec, "이름 / 출처", anchor="middle")
            + txt(W//2, 168, 36, "#FFFFFF" if mc != "#FFFFFF" else sec, f"{name}", anchor="middle", bold=False)
            + svg_close()
        ),
        "lower_third_10.svg": (  # 채널 브랜딩 바
            svg_open(W, H, "none")
            + f'<rect x="0" y="0" width="{W}" height="{H}" fill="{dark}" opacity="0.9"/>'
            + f'<rect x="0" y="0" width="{W}" height="4" fill="{mc}"/>'
            + f'<rect x="0" y="{H-4}" width="{W}" height="4" fill="{mc}"/>'
            + txt(40, 90, 50, "#FFFFFF", "이름 / 출처")
            + txt(40, 148, 32, mc, f"{name} · {domain}", bold=False)
            + f'<text x="{W-40}" y="{H//2+10}" font-size="28" fill="{mc}" '
            + f'text-anchor="end" font-family="Gmarket Sans Bold,sans-serif" opacity="0.8">{name}</text>'
            + svg_close()
        ),
    }


# ─── 메인 ─────────────────────────────────────────────────────────────────────

def main():
    total = 0
    for ch_id in CHANNELS:
        sub_dir = CHANNELS_DIR / ch_id / "templates"
        sub_dir.mkdir(parents=True, exist_ok=True)
        tr_dir = CHANNELS_DIR / ch_id / "transitions"
        tr_dir.mkdir(parents=True, exist_ok=True)

        bars = _subtitle_bars(ch_id)
        for fname, content in bars.items():
            (sub_dir / fname).write_text(content, encoding="utf-8")

        trans = _transitions(ch_id)
        for fname, content in trans.items():
            (tr_dir / fname).write_text(content, encoding="utf-8")

        lowers = _lower_thirds(ch_id)
        for fname, content in lowers.items():
            (sub_dir / fname).write_text(content, encoding="utf-8")

        count = len(bars) + len(trans) + len(lowers)
        total += count
        logger.info(f"[OK] {ch_id} — 자막바 {len(bars)}종 + 장면전환 {len(trans)}종 + 로워서드 {len(lowers)}종")

    print(f"\n=== 1단계 완료 ===")
    print(f"총 {total}개 SVG 생성")
    print(f"저장 위치: assets/channels/CH{{N}}/templates/ + transitions/")


if __name__ == "__main__":
    main()
