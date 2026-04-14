# scripts/generate_branding/svg_helpers.py
"""두들 스타일 SVG 헬퍼 — Manim SVGMobject 호환
   사용 가능한 요소: path, circle, rect, line, ellipse, text
"""
import math


def svg_open(width, height, bg_color="none"):
    """SVG 문서 헤더 + 선택적 배경 rect 반환"""
    bg = f'<rect width="{width}" height="{height}" fill="{bg_color}"/>' if bg_color != "none" else ""
    header = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}">'
    )
    return header + bg


def svg_close():
    return "</svg>"


def doodle_circle(cx, cy, r, color, sw=4, fill="none"):
    """불규칙 bezier 원 — 손그림 느낌"""
    o = 3
    d = (
        f"M {cx+r+o},{cy} "
        f"C {cx+r+o},{cy-r+o} {cx+o},{cy-r-o} {cx},{cy-r} "
        f"C {cx-r-o},{cy-r+o} {cx-r+o},{cy+o} {cx-r},{cy} "
        f"C {cx-r+o},{cy+r-o} {cx-o},{cy+r+o} {cx},{cy+r} "
        f"C {cx+r+o},{cy+r-o} {cx+r-o},{cy-o} {cx+r+o},{cy} Z"
    )
    return (
        f'<path d="{d}" fill="{fill}" stroke="{color}" '
        f'stroke-width="{sw}" stroke-linecap="round" stroke-linejoin="round"/>'
    )


def doodle_rect(x, y, w, h, color, sw=4, fill="none", rx=8):
    """두들 스타일 사각형"""
    o = 2
    return (
        f'<rect x="{x+o}" y="{y-o}" width="{w-o}" height="{h+o}" '
        f'rx="{rx}" fill="{fill}" stroke="{color}" '
        f'stroke-width="{sw}" stroke-linecap="round" stroke-linejoin="round"/>'
    )


def doodle_line(x1, y1, x2, y2, color, sw=3):
    """두들 직선 (약간 불규칙 bezier)"""
    mx, my = (x1 + x2) // 2 + 2, (y1 + y2) // 2 - 2
    return (
        f'<path d="M {x1},{y1} Q {mx},{my} {x2},{y2}" '
        f'fill="none" stroke="{color}" stroke-width="{sw}" stroke-linecap="round"/>'
    )


def doodle_text(text, x, y, size, color, anchor="middle", weight="bold"):
    return (
        f'<text x="{x}" y="{y}" font-size="{size}" fill="{color}" '
        f'font-family="Gmarket Sans Bold, sans-serif" '
        f'text-anchor="{anchor}" font-weight="{weight}">{text}</text>'
    )


def doodle_path(d, color, sw=4, fill="none"):
    """임의 두들 path"""
    return (
        f'<path d="{d}" fill="{fill}" stroke="{color}" '
        f'stroke-width="{sw}" stroke-linecap="round" stroke-linejoin="round"/>'
    )


def doodle_crown(cx, cy, size, color, sw=3):
    """왕관 두들 — CH1 머니그래픽 전용"""
    s = size
    d = (
        f"M {cx-s},{cy} L {cx-s},{cy-s*0.8} L {cx-s*0.4},{cy-s*0.3} "
        f"L {cx},{cy-s} L {cx+s*0.4},{cy-s*0.3} L {cx+s},{cy-s*0.8} L {cx+s},{cy} Z"
    )
    return doodle_path(d, color, sw, fill=color)


def doodle_star(cx, cy, r, color, sw=2):
    """별 두들"""
    pts = []
    for i in range(10):
        angle = math.pi * i / 5 - math.pi / 2
        rad = r if i % 2 == 0 else r * 0.4
        pts.append(f"{cx + rad * math.cos(angle):.1f},{cy + rad * math.sin(angle):.1f}")
    return doodle_path("M " + " L ".join(pts) + " Z", color, sw, fill=color)


def group(content, transform=""):
    t = f' transform="{transform}"' if transform else ""
    return f"<g{t}>{content}</g>"
