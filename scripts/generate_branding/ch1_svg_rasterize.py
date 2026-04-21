# scripts/generate_branding/ch1_svg_rasterize.py
"""Cairo 없이 Pillow 직접 드로잉으로 CH1 SVG 9종을 PNG 래스터화.

Windows 환경에서 cairosvg/svglib 모두 Cairo DLL 의존으로 실패하므로
SVG 스펙을 Pillow ImageDraw로 직접 구현.

생성 에셋:
  logo/logo.png                          (600×600)
  intro/intro_frame.png                  (512×512)
  intro/intro_text.png                   (620×156)
  intro/intro_sparkle.png               (256×256)
  outro/outro_bill.png                   (320×150)
  outro/outro_cta.png                    (600×120)
  templates/subtitle_bar_key.png         (1280×120)
  templates/subtitle_bar_dialog.png      (1280×120)
  templates/subtitle_bar_info.png        (1280×120)
"""
from __future__ import annotations

import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

# 프로젝트 루트 기준
KAS_ROOT = Path(__file__).parent.parent.parent
CH1_DIR = KAS_ROOT / "assets" / "channels" / "CH1"

# ─────────────────────────────────────────────
# 색상 상수
# ─────────────────────────────────────────────
CREAM   = (255, 253, 245)
DARK    = (44,  62,  80)
MINT    = (46,  204, 113)
GOLD    = (241, 196, 15)
WHITE   = (255, 255, 255)
RED     = (231, 76,  60)

# ─────────────────────────────────────────────
# 폰트 로더
# ─────────────────────────────────────────────
_FONT_REG  = "C:/Windows/Fonts/malgun.ttf"
_FONT_BOLD = "C:/Windows/Fonts/malgunbd.ttf"

def _font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    path = _FONT_BOLD if bold else _FONT_REG
    return ImageFont.truetype(path, size)


# ─────────────────────────────────────────────
# 헬퍼: 다이아몬드 폴리곤
# ─────────────────────────────────────────────
def _diamond(draw: ImageDraw.ImageDraw, cx: float, cy: float, r: float,
             fill: tuple) -> None:
    """cx, cy 중심, r 반지름 다이아몬드 폴리곤 그리기."""
    pts = [(cx, cy - r), (cx + r, cy), (cx, cy + r), (cx - r, cy)]
    draw.polygon(pts, fill=fill)


# ─────────────────────────────────────────────
# 헬퍼: 반투명 레이어 합성
# ─────────────────────────────────────────────
def _blend_rect(base: Image.Image, xy: tuple, fill: tuple,
                opacity: float, radius: int = 0) -> None:
    """base 이미지에 반투명(opacity) 둥근 사각형을 합성."""
    overlay = Image.new("RGBA", base.size, (0, 0, 0, 0))
    odraw = ImageDraw.Draw(overlay)
    alpha = int(255 * opacity)
    color = fill + (alpha,)
    if radius:
        odraw.rounded_rectangle(xy, radius=radius, fill=color)
    else:
        odraw.rectangle(xy, fill=color)
    base_rgba = base.convert("RGBA")
    result = Image.alpha_composite(base_rgba, overlay)
    base.paste(result.convert(base.mode), (0, 0))


# ─────────────────────────────────────────────
# 헬퍼: 텍스트 너비 측정
# ─────────────────────────────────────────────
def _text_width(draw: ImageDraw.ImageDraw, text: str, font) -> int:
    bbox = draw.textbbox((0, 0), text, font=font)
    return bbox[2] - bbox[0]


# ─────────────────────────────────────────────
# 1. logo.png (600×600)
# ─────────────────────────────────────────────
def gen_logo_png() -> Path:
    out = CH1_DIR / "logo" / "logo.png"
    out.parent.mkdir(parents=True, exist_ok=True)

    img = Image.new("RGB", (600, 600), CREAM)
    draw = ImageDraw.Draw(img)

    # 외곽 원 (dark stroke)
    draw.ellipse([40 - 1, 40 - 1, 560 + 1, 560 + 1],
                 outline=DARK, width=7)
    # 내측 원 (mint stroke)
    draw.ellipse([52, 52, 548, 548], outline=MINT, width=3)

    # 머리 (둥근 검정 사각 — character head)
    draw.rounded_rectangle([255, 158, 345, 263], radius=30, fill=DARK)

    # 왕관 (금색 폴리곤)
    crown = [(260, 150), (275, 120), (300, 142), (325, 120), (340, 150)]
    draw.polygon(crown, fill=GOLD)
    # W 텍스트 (왕관 위)
    f_w = _font(28, bold=True)
    draw.text((300, 133), "W", fill=DARK, font=f_w, anchor="mm")

    # "MoneyGraphic" 텍스트
    f_mg = _font(44, bold=True)
    draw.text((300, 420), "MoneyGraphic", fill=DARK, font=f_mg, anchor="mm")

    # 4개 다이아몬드 별 (상하좌우)
    for cx, cy in [(300, 50), (550, 300), (300, 550), (50, 300)]:
        _diamond(draw, cx, cy, 10, GOLD)

    img.save(out, "PNG", optimize=True)
    print("[OK] logo.png")
    return out


# ─────────────────────────────────────────────
# 2. intro_frame.png (512×512)
# ─────────────────────────────────────────────
def gen_intro_frame_png() -> Path:
    out = CH1_DIR / "intro" / "intro_frame.png"
    out.parent.mkdir(parents=True, exist_ok=True)

    img = Image.new("RGB", (512, 512), CREAM)
    draw = ImageDraw.Draw(img)

    # 외곽 원 (dark)
    draw.ellipse([16, 16, 496, 496], outline=DARK, width=5)
    # 내측 원 (mint)
    draw.ellipse([28, 28, 484, 484], outline=MINT, width=3)

    # 8개 금색 별 (45° 간격, 반지름 240 위치)
    cx, cy, r = 256, 256, 238
    for i in range(8):
        angle = math.radians(i * 45)
        sx = cx + r * math.cos(angle)
        sy = cy + r * math.sin(angle)
        _diamond(draw, sx, sy, 10, GOLD)

    img.save(out, "PNG", optimize=True)
    print("[OK] intro_frame.png")
    return out


# ─────────────────────────────────────────────
# 3. intro_text.png (620×156)
# ─────────────────────────────────────────────
def gen_intro_text_png() -> Path:
    out = CH1_DIR / "intro" / "intro_text.png"
    out.parent.mkdir(parents=True, exist_ok=True)

    img = Image.new("RGB", (620, 156), CREAM)
    draw = ImageDraw.Draw(img)

    # 좌측 민트 악센트 바
    draw.rectangle([0, 0, 8, 156], fill=MINT)

    # "머니그래픽" 텍스트 (mint, bold, center)
    f = _font(72, bold=True)
    draw.text((320, 90), "머니그래픽", fill=MINT, font=f, anchor="mm")

    img.save(out, "PNG", optimize=True)
    print("[OK] intro_text.png")
    return out


# ─────────────────────────────────────────────
# 4. intro_sparkle.png (256×256)
# ─────────────────────────────────────────────
def gen_intro_sparkle_png() -> Path:
    out = CH1_DIR / "intro" / "intro_sparkle.png"
    out.parent.mkdir(parents=True, exist_ok=True)

    img = Image.new("RGB", (256, 256), CREAM)
    draw = ImageDraw.Draw(img)

    # 4-point 별 (금색) — 메인
    pts1 = [(128, 28), (149, 107), (228, 128), (149, 149),
            (128, 228), (107, 149), (28, 128), (107, 107)]
    draw.polygon(pts1, fill=GOLD)

    # 45도 회전 오버레이 (반투명) — Image 합성
    overlay = Image.new("RGBA", (256, 256), (0, 0, 0, 0))
    odraw = ImageDraw.Draw(overlay)
    # 단순화: 45도 회전 별 (근사)
    rot_pts = []
    for px, py in pts1:
        rx = (px - 128) * math.cos(math.radians(45)) - (py - 128) * math.sin(math.radians(45)) + 128
        ry = (px - 128) * math.sin(math.radians(45)) + (py - 128) * math.cos(math.radians(45)) + 128
        rot_pts.append((rx, ry))
    odraw.polygon(rot_pts, fill=GOLD + (178,))  # opacity 0.7
    img_rgba = img.convert("RGBA")
    img = Image.alpha_composite(img_rgba, overlay).convert("RGB")

    draw = ImageDraw.Draw(img)
    # 중앙 흰 점
    draw.ellipse([120, 120, 136, 136], fill=WHITE)

    img.save(out, "PNG", optimize=True)
    print("[OK] intro_sparkle.png")
    return out


# ─────────────────────────────────────────────
# 5. outro_bill.png (320×150)
# ─────────────────────────────────────────────
def gen_outro_bill_png() -> Path:
    out = CH1_DIR / "outro" / "outro_bill.png"
    out.parent.mkdir(parents=True, exist_ok=True)

    img = Image.new("RGB", (320, 150), MINT)
    draw = ImageDraw.Draw(img)

    # 민트 배경 둥근 사각 (이미 mint 배경)
    # 흰 내부 프레임
    draw.rounded_rectangle([8, 8, 312, 142], radius=7, outline=WHITE, width=2)

    # ₩ 기호 (대형)
    f_won = _font(70, bold=True)
    draw.text((55, 95), "₩", fill=WHITE, font=f_won, anchor="mm")

    # "50,000" 텍스트
    f_num = _font(30, bold=True)
    draw.text((200, 50), "50,000", fill=WHITE, font=f_num, anchor="mm")

    # 코너 금색 별 2개
    _diamond(draw, 292, 25, 9, GOLD)
    _diamond(draw, 292, 125, 9, GOLD)

    img.save(out, "PNG", optimize=True)
    print("[OK] outro_bill.png")
    return out


# ─────────────────────────────────────────────
# 6. outro_cta.png (600×120)
# ─────────────────────────────────────────────
def gen_outro_cta_png() -> Path:
    out = CH1_DIR / "outro" / "outro_cta.png"
    out.parent.mkdir(parents=True, exist_ok=True)

    img = Image.new("RGB", (600, 120), CREAM)
    draw = ImageDraw.Draw(img)

    # 좌측 구독 버튼 (빨강)
    draw.rounded_rectangle([0, 0, 280, 120], radius=12, fill=RED)
    f = _font(44, bold=True)
    draw.text((140, 60), "구독", fill=WHITE, font=f, anchor="mm")

    # 우측 좋아요 버튼 (민트)
    draw.rounded_rectangle([320, 0, 600, 120], radius=12, fill=MINT)
    draw.text((460, 60), "좋아요", fill=WHITE, font=f, anchor="mm")

    img.save(out, "PNG", optimize=True)
    print("[OK] outro_cta.png")
    return out


# ─────────────────────────────────────────────
# 7. subtitle_bar_key.png (1280×120)
# ─────────────────────────────────────────────
def gen_subtitle_bar_key_png() -> Path:
    out = CH1_DIR / "templates" / "subtitle_bar_key.png"
    out.parent.mkdir(parents=True, exist_ok=True)

    img = Image.new("RGB", (1280, 120), CREAM)
    # dark bar opacity 0.92
    _blend_rect(img, [20, 10, 1260, 110], DARK, opacity=0.92, radius=8)

    draw = ImageDraw.Draw(img)
    # 민트 KEY 배지
    draw.rounded_rectangle([30, 20, 110, 100], radius=6, fill=MINT)
    f_key = _font(22, bold=True)
    draw.text((70, 60), "KEY", fill=WHITE, font=f_key, anchor="mm")

    # 텍스트
    f_txt = _font(30)
    draw.text((140, 60), "핵심 용어 텍스트 영역", fill=WHITE, font=f_txt, anchor="lm")

    # 금색 별 2개 (우측)
    _diamond(draw, 1195, 60, 10, GOLD)
    _diamond(draw, 1240, 60, 10, GOLD)

    img.save(out, "PNG", optimize=True)
    print("[OK] subtitle_bar_key.png")
    return out


# ─────────────────────────────────────────────
# 8. subtitle_bar_dialog.png (1280×120)
# ─────────────────────────────────────────────
def gen_subtitle_bar_dialog_png() -> Path:
    out = CH1_DIR / "templates" / "subtitle_bar_dialog.png"
    out.parent.mkdir(parents=True, exist_ok=True)

    img = Image.new("RGB", (1280, 120), CREAM)
    # dark bar opacity 0.80
    _blend_rect(img, [20, 10, 1260, 110], DARK, opacity=0.80, radius=8)

    draw = ImageDraw.Draw(img)
    # 민트 언더라인
    draw.rectangle([20, 108, 1260, 112], fill=MINT)

    # 나레이션 텍스트
    f = _font(28)
    draw.text((60, 60), "나레이션 텍스트 영역", fill=(*CREAM, 255), font=f, anchor="lm")

    img.save(out, "PNG", optimize=True)
    print("[OK] subtitle_bar_dialog.png")
    return out


# ─────────────────────────────────────────────
# 9. subtitle_bar_info.png (1280×120)
# ─────────────────────────────────────────────
def gen_subtitle_bar_info_png() -> Path:
    out = CH1_DIR / "templates" / "subtitle_bar_info.png"
    out.parent.mkdir(parents=True, exist_ok=True)

    img = Image.new("RGB", (1280, 120), MINT)
    draw = ImageDraw.Draw(img)

    # dark 원형 i 배지
    draw.ellipse([15, 25, 85, 95], fill=DARK)
    f_i = _font(34, bold=True)
    draw.text((50, 60), "i", fill=WHITE, font=f_i, anchor="mm")

    # 정보 텍스트
    f = _font(30)
    draw.text((105, 60), "정보 강조 텍스트 영역", fill=DARK, font=f, anchor="lm")

    img.save(out, "PNG", optimize=True)
    print("[OK] subtitle_bar_info.png")
    return out


# ─────────────────────────────────────────────
# 오케스트레이터
# ─────────────────────────────────────────────
def generate_ch1_svg_pngs() -> None:
    """CH1 SVG 스펙 기반 PNG 9종을 Pillow로 직접 생성."""
    print("CH1 SVG → PNG 래스터화 (Pillow 직접 드로잉) 시작")
    generators = [
        gen_logo_png,
        gen_intro_frame_png,
        gen_intro_text_png,
        gen_intro_sparkle_png,
        gen_outro_bill_png,
        gen_outro_cta_png,
        gen_subtitle_bar_key_png,
        gen_subtitle_bar_dialog_png,
        gen_subtitle_bar_info_png,
    ]
    success = 0
    for fn in generators:
        try:
            fn()
            success += 1
        except Exception as e:
            print(f"[ERR] {fn.__name__}: {e}")
    print(f"\n[완료] {success}/{len(generators)}종 PNG 생성")


if __name__ == "__main__":
    generate_ch1_svg_pngs()
