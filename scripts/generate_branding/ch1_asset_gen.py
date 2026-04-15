"""
ch1_asset_gen.py
────────────────
CH1 전용 PIL 기반 고퀄리티 에셋 생성기.

SD XL GPU 없이도 최고 퀄리티를 위해:
- 인트로/아웃트로 분해 요소: PIL 벡터급 클린 디자인
- 자막바 3종: RGBA 투명 배경, 채널 색상 계열
- 썸네일 3종: PIL 그라데이션 배경 + Imagen 캐릭터 합성
- 전환 3종: PIL 효과 (종이접기/잉크번짐/동심원)
"""
from __future__ import annotations

import io
import math
import random
import sys
from pathlib import Path

from loguru import logger
from PIL import Image, ImageDraw, ImageFont

if hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

# ── 경로 ────────────────────────────────────────────────────────────────────
KAS_ROOT = Path(__file__).parent.parent.parent
CH1_DIR = KAS_ROOT / "assets" / "channels" / "CH1"

# ── CH1 색상 팔레트 ──────────────────────────────────────────────────────────
MINT = (46, 204, 113)       # #2ECC71 — main_color
DARK = (44, 62, 80)         # #2C3E50 — stroke / text
GOLD = (241, 196, 15)       # #F1C40F — 왕관 / 별
BLUE = (52, 152, 219)       # #3498DB — sub_color
WHITE = (255, 255, 255)
CREAM = (255, 255, 255)     # 흰색 배경 (크림색에서 변경)


# ── 유틸 ────────────────────────────────────────────────────────────────────

def rgba(color: tuple, alpha: int = 255) -> tuple:
    """3-tuple → 4-tuple RGBA"""
    return (*color[:3], alpha)


def get_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    """한국어 지원 폰트 로드 (fallback → default)."""
    candidates = [
        "C:/Windows/Fonts/malgunbd.ttf" if bold else "C:/Windows/Fonts/malgun.ttf",
        "C:/Windows/Fonts/gulim.ttc",
        "C:/Windows/Fonts/NanumGothicBold.ttf" if bold else "C:/Windows/Fonts/NanumGothic.ttf",
    ]
    for fp in candidates:
        if Path(fp).exists():
            try:
                return ImageFont.truetype(fp, size)
            except Exception:
                pass
    return ImageFont.load_default()


def draw_star(
    draw: ImageDraw.Draw,
    cx: int, cy: int, r: int,
    color: tuple,
    n_points: int = 4,
    inner_ratio: float = 0.35,
) -> None:
    """n_points 뾰족 별 그리기."""
    pts: list[tuple[float, float]] = []
    for i in range(n_points * 2):
        angle = math.pi * i / n_points - math.pi / 2
        radius = r if i % 2 == 0 else r * inner_ratio
        pts.append((cx + radius * math.cos(angle), cy + radius * math.sin(angle)))
    draw.polygon(pts, fill=color)


# ── 인트로 분해 요소 4종 ────────────────────────────────────────────────────


def gen_intro_frame() -> None:
    """장식 프레임: 원형 테두리 + 금색 별 4개 (512×512, RGBA)."""
    W = H = 512
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    cx, cy = W // 2, H // 2

    # 외곽 원 (어두운, 두꺼운 선)
    R_OUT, R_IN = 240, 228
    draw.ellipse([cx - R_OUT, cy - R_OUT, cx + R_OUT, cy + R_OUT],
                 outline=rgba(DARK, 220), width=7)
    # 내부 원 (민트, 얇은 선)
    draw.ellipse([cx - R_IN, cy - R_IN, cx + R_IN, cy + R_IN],
                 outline=rgba(MINT, 200), width=3)

    # 4방향 금색 별 (원 위에 올라타듯)
    for deg in (0, 90, 180, 270):
        rad = math.radians(deg)
        sx = cx + int(R_OUT * math.cos(rad))
        sy = cy + int(R_OUT * math.sin(rad))
        draw_star(draw, sx, sy, 22, rgba(GOLD), n_points=4)

    # 45° 코너 작은 별
    for deg in (45, 135, 225, 315):
        rad = math.radians(deg)
        sx = cx + int((R_OUT - 14) * math.cos(rad))
        sy = cy + int((R_OUT - 14) * math.sin(rad))
        draw_star(draw, sx, sy, 10, rgba(GOLD, 180), n_points=4)

    img.save(CH1_DIR / "intro" / "intro_frame.png", "PNG")
    logger.info("[OK] intro_frame.png (512×512)")


def gen_intro_text() -> None:
    """채널명 텍스트 배너: '머니그래픽' (620×156, RGBA)."""
    W, H = 620, 156
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # 배경 배너 (어두운 반투명)
    draw.rounded_rectangle([0, 16, W, H - 16], radius=14, fill=rgba(DARK, 235))

    # 왼쪽 민트 강조 바
    draw.rounded_rectangle([0, 16, 10, H - 16], radius=6, fill=rgba(MINT))

    # 채널명
    font = get_font(72, bold=True)
    text = "머니그래픽"
    bbox = draw.textbbox((0, 0), text, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    tx = (W - tw) // 2 + 5
    ty = H // 2 - th // 2 - 2
    draw.text((tx, ty), text, fill=rgba(MINT), font=font)

    img.save(CH1_DIR / "intro" / "intro_text.png", "PNG")
    logger.info("[OK] intro_text.png (620×156)")


def gen_intro_character() -> None:
    """인트로 캐릭터: character_explain.png 512×512 리사이즈."""
    src = CH1_DIR / "characters" / "character_explain.png"
    if not src.exists():
        logger.warning("character_explain.png 없음 — intro_character.png 스킵")
        return
    img = Image.open(src).convert("RGBA").resize((512, 512), Image.LANCZOS)
    img.save(CH1_DIR / "intro" / "intro_character.png", "PNG")
    logger.info("[OK] intro_character.png (512×512, Imagen 캐릭터 재사용)")


def gen_intro_sparkle() -> None:
    """스파클: 4꼭지 금색 별 빛나는 효과 (256×256, RGBA)."""
    W = H = 256
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    cx, cy = W // 2, H // 2

    # 글로우 헤일로
    draw_star(draw, cx, cy, 115, rgba(GOLD, 60), n_points=4, inner_ratio=0.1)

    # 주 별 (굵은 4꼭지)
    draw_star(draw, cx, cy, 100, rgba(GOLD, 240), n_points=4, inner_ratio=0.22)

    # 45° 겹치는 별 (얇고 살짝 투명)
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d2 = ImageDraw.Draw(overlay)
    draw_star(d2, cx, cy, 85, rgba(GOLD, 160), n_points=4, inner_ratio=0.22)
    overlay = overlay.rotate(45, center=(cx, cy))
    img.alpha_composite(overlay)

    # 중앙 밝은 점
    draw.ellipse([cx - 8, cy - 8, cx + 8, cy + 8], fill=rgba(WHITE, 220))

    img.save(CH1_DIR / "intro" / "intro_sparkle.png", "PNG")
    logger.info("[OK] intro_sparkle.png (256×256)")


# ── 아웃트로 분해 요소 4종 ──────────────────────────────────────────────────


def gen_outro_background() -> None:
    """아웃트로 배경: 흰색 기반 민트 액센트 (1280×720, RGB)."""
    W, H = 1280, 720
    img = Image.new("RGB", (W, H), WHITE)
    draw = ImageDraw.Draw(img)
    cx, cy = W // 2, H // 2

    # 연한 민트 방사형 후광 (흰 배경 위)
    for i in range(14, 0, -1):
        r_glow = 60 + i * 48
        alpha_val = max(0, 30 - i * 2)
        color = (
            255 - alpha_val,
            255 - alpha_val + min(alpha_val, MINT[1] - 200),
            255 - alpha_val,
        )
        draw.ellipse([cx - r_glow, cy - r_glow, cx + r_glow, cy + r_glow],
                     outline=(180, 230, 200), width=2)

    # 하단 민트 그라데이션 바
    for y in range(H - 120, H):
        t = (y - (H - 120)) / 120
        r = int(WHITE[0] * (1 - t) + MINT[0] * t)
        g = int(WHITE[1] * (1 - t) + MINT[1] * t)
        b = int(WHITE[2] * (1 - t) + MINT[2] * t)
        draw.line([(0, y), (W, y)], fill=(r, g, b))

    # ₩ 장식 (연한 민트, 배경용)
    font = get_font(48, bold=True)
    for (x, y) in [(60, 40), (160, 560), (1080, 60), (1020, 520),
                   (580, 20), (660, 640), (30, 340)]:
        draw.text((x, y), "₩", fill=(200, 235, 215), font=font)

    img.save(CH1_DIR / "outro" / "outro_background.png", "PNG")
    logger.info("[OK] outro_background.png (1280×720)")


def gen_outro_bill() -> None:
    """지폐 일러스트: 심플한 한국 지폐 스타일 (320×150, RGBA)."""
    W, H = 320, 150
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # 지폐 본체 (민트)
    draw.rounded_rectangle([2, 2, W - 2, H - 2], radius=10,
                             fill=rgba(MINT, 245), outline=rgba(DARK, 200), width=2)

    # 내부 보조 테두리
    draw.rounded_rectangle([10, 10, W - 10, H - 10], radius=6,
                             outline=rgba(WHITE, 100), width=1)

    # ₩ 심볼 (크게, 왼쪽)
    font_big = get_font(62, bold=True)
    draw.text((22, 28), "₩", fill=rgba(WHITE, 235), font=font_big)

    # 금액
    font_sm = get_font(24, bold=True)
    draw.text((122, 58), "50,000", fill=rgba(WHITE, 200), font=font_sm)

    # 오른쪽 별 장식
    draw_star(draw, W - 38, 35, 14, rgba(GOLD), n_points=4)
    draw_star(draw, W - 38, H - 35, 14, rgba(GOLD, 190), n_points=4)

    img.save(CH1_DIR / "outro" / "outro_bill.png", "PNG")
    logger.info("[OK] outro_bill.png (320×150)")


def gen_outro_character() -> None:
    """아웃트로 캐릭터: character_money.png 512×512 리사이즈."""
    src = CH1_DIR / "characters" / "character_money.png"
    if not src.exists():
        logger.warning("character_money.png 없음 — outro_character.png 스킵")
        return
    img = Image.open(src).convert("RGBA").resize((512, 512), Image.LANCZOS)
    img.save(CH1_DIR / "outro" / "outro_character.png", "PNG")
    logger.info("[OK] outro_character.png (512×512, Imagen 캐릭터 재사용)")


def gen_outro_cta() -> None:
    """CTA 버튼: 구독(빨강) + 좋아요(민트) (600×120, RGBA)."""
    W, H = 600, 120
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    sub_w = 270
    gap = 20
    # 구독 버튼 (유튜브 빨간색)
    draw.rounded_rectangle([0, 0, sub_w, H], radius=58,
                             fill=(231, 76, 60, 242))

    # 좋아요 버튼 (민트)
    draw.rounded_rectangle([sub_w + gap, 0, W, H], radius=58,
                             fill=rgba(MINT, 242))

    font = get_font(40, bold=True)
    # 구독 텍스트 + 🔔 대체 (PIL 기본 폰트에 이모지 불가 → 글자만)
    draw.text((54, 34), "구독", fill=rgba(WHITE), font=font)
    # 좋아요 텍스트
    draw.text((sub_w + gap + 32, 34), "좋아요", fill=rgba(WHITE), font=font)

    img.save(CH1_DIR / "outro" / "outro_cta.png", "PNG")
    logger.info("[OK] outro_cta.png (600×120)")


# ── 자막바 3종 ────────────────────────────────────────────────────────────────


def gen_subtitle_bar_key() -> None:
    """KEY 자막바: 핵심 용어 강조형 (1280×120, RGBA)."""
    W, H = 1280, 120
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # 배경 (반투명 다크)
    draw.rounded_rectangle([0, 8, W, H - 8], radius=10, fill=rgba(DARK, 225))

    # 왼쪽 민트 강조 바
    draw.rounded_rectangle([0, 8, 9, H - 8], radius=5, fill=rgba(MINT))

    # KEY 배지
    badge_x1, badge_y1, badge_x2, badge_y2 = 18, 24, 108, H - 24
    draw.rounded_rectangle([badge_x1, badge_y1, badge_x2, badge_y2],
                             radius=8, fill=rgba(MINT))
    font_badge = get_font(26, bold=True)
    draw.text((27, 34), "KEY", fill=rgba(DARK), font=font_badge)

    # 텍스트 영역
    font_text = get_font(42, bold=True)
    draw.text((124, 30), "핵심 용어 텍스트 영역", fill=rgba(WHITE, 220), font=font_text)

    # 우측 별 장식
    draw_star(draw, W - 48, H // 2, 15, rgba(GOLD), n_points=4)
    draw_star(draw, W - 84, H // 2, 9, rgba(GOLD, 160), n_points=4)

    img.save(CH1_DIR / "templates" / "subtitle_bar_key.png", "PNG")
    logger.info("[OK] subtitle_bar_key.png (1280×120)")


def gen_subtitle_bar_dialog() -> None:
    """DIALOG 자막바: 나레이션 대화형 하단 가로줄 (1280×120, RGBA)."""
    W, H = 1280, 120
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # 반투명 어두운 배경
    draw.rounded_rectangle([0, 4, W, H - 4], radius=8, fill=(20, 30, 40, 205))

    # 하단 민트 액센트 라인
    draw.rectangle([24, H - 13, W - 24, H - 9], fill=rgba(MINT, 185))

    # 텍스트
    font_text = get_font(40)
    draw.text((30, 34), "나레이션 / 대화 텍스트 영역", fill=(240, 240, 240, 230), font=font_text)

    img.save(CH1_DIR / "templates" / "subtitle_bar_dialog.png", "PNG")
    logger.info("[OK] subtitle_bar_dialog.png (1280×120)")


def gen_subtitle_bar_info() -> None:
    """INFO 자막바: 정보 강조 민트 배경형 (1280×120, RGBA)."""
    W, H = 1280, 120
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # 민트 배경
    draw.rounded_rectangle([0, 4, W, H - 4], radius=8, fill=rgba(MINT, 235))

    # INFO 원 배지 (다크)
    bx1, by1, bx2, by2 = 14, 18, 14 + 84, 18 + 84
    draw.ellipse([bx1, by1, bx2, by2], fill=rgba(DARK, 220))
    font_i = get_font(46, bold=True)
    draw.text((40, 22), "i", fill=rgba(WHITE), font=font_i)

    # 텍스트 (어두운, 읽기 쉽게)
    font_text = get_font(42, bold=True)
    draw.text((116, 30), "정보 강조 텍스트 영역", fill=rgba(DARK), font=font_text)

    img.save(CH1_DIR / "templates" / "subtitle_bar_info.png", "PNG")
    logger.info("[OK] subtitle_bar_info.png (1280×120)")


# ── 썸네일 3종 (PIL 그라데이션 + 캐릭터 합성) ────────────────────────────────


def _make_gradient_bg(w: int, h: int, c1: tuple, c2: tuple, mode: str = "lr") -> Image.Image:
    """좌→우(lr) 또는 위→아래(tb) 그라데이션 RGB 이미지."""
    img = Image.new("RGB", (w, h))
    draw = ImageDraw.Draw(img)
    steps = w if mode == "lr" else h
    for i in range(steps):
        t = i / steps
        color = (
            int(c1[0] * (1 - t) + c2[0] * t),
            int(c1[1] * (1 - t) + c2[1] * t),
            int(c1[2] * (1 - t) + c2[2] * t),
        )
        if mode == "lr":
            draw.line([(i, 0), (i, h)], fill=color)
        else:
            draw.line([(0, i), (w, i)], fill=color)
    return img


def gen_thumbnail(
    idx: int,
    title_lines: list[str],
    char_name: str,
    accent: tuple,
) -> None:
    """썸네일 1장 생성: Imagen 크림 배경 + 캐릭터 합성 + 타이포 (1920×1080, RGB).

    배경: templates/_tmp/thumb{idx}_bg.png (Imagen 4.0 크림 일러스트, 좌측 비움)
    캐릭터: 우측 합성 (알파 마스크)
    타이포: 좌측 다크 텍스트 (크림 배경에 최적)
    """
    W, H = 1920, 1080

    # Imagen 크림 배경 로드 (없으면 크림 단색 폴백)
    bg_path = CH1_DIR / "templates" / "_tmp" / f"thumb{idx}_bg.png"
    if bg_path.exists():
        img = Image.open(bg_path).convert("RGB")
        img = img.resize((W, H), Image.LANCZOS)
    else:
        logger.warning(f"[WARN] {bg_path.name} 없음 — 크림 배경으로 대체")
        img = Image.new("RGB", (W, H), CREAM)

    # RGBA 합성 레이어 준비
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw_ov = ImageDraw.Draw(overlay)

    # 하단 액센트 바 (민트 반투명)
    bar_y = H - 80
    draw_ov.rectangle([0, bar_y, W, H], fill=(*accent[:3], 220))
    img_rgba = img.convert("RGBA")
    img = Image.alpha_composite(img_rgba, overlay).convert("RGB")

    draw = ImageDraw.Draw(img)

    # 캐릭터 (우측 배치, 알파 합성)
    char_src = CH1_DIR / "characters" / f"character_{char_name}.png"
    if char_src.exists():
        char_img = Image.open(char_src).convert("RGBA")
        char_size = 860
        char_img = char_img.resize((char_size, char_size), Image.LANCZOS)
        cx = W - char_size - 40
        cy = H - char_size - 60  # 하단 고정 (발이 바에 걸치도록)
        base_rgba = img.convert("RGBA")
        base_rgba.paste(char_img, (cx, cy), char_img)
        img = base_rgba.convert("RGB")
        draw = ImageDraw.Draw(img)

    # 채널명 (좌상단, 액센트 색)
    font_ch = get_font(32, bold=True)
    draw.text((80, 52), "머니그래픽", fill=accent[:3], font=font_ch)

    # 제목 (좌측, 다크 + 드롭 섀도우 4px)
    font_title = get_font(108, bold=True)
    for i, line in enumerate(title_lines):
        ty = 300 + i * 135
        # 드롭 섀도우 (4px offset)
        draw.text((84, ty + 4), line, fill=(0, 0, 0, 120), font=font_title)
        # 메인 텍스트 (다크)
        draw.text((80, ty), line, fill=DARK, font=font_title)

    # 하단 바 서브타이틀
    font_sub = get_font(36, bold=True)
    draw.text((80, bar_y + 18), "경제를 쉽게, 머니그래픽", fill=rgba(WHITE, 240), font=font_sub)

    out = CH1_DIR / "templates" / f"thumbnail_sample_{idx}.png"
    img.save(out, "PNG")
    logger.info(f"[OK] thumbnail_sample_{idx}.png (1920×1080)")


def gen_thumbnails() -> None:
    """CH1 썸네일 3종 생성 — Imagen 크림 배경 기반."""
    configs = [
        (1, ["코인 차트의", "마법!"],      "explain", MINT),
        (2, ["금리 인상,", "내 지갑은?"],  "money",   GOLD),
        (3, ["주식 초보,", "이것만 알아!"], "rich",    BLUE),
    ]
    for idx, title_lines, char, accent in configs:
        gen_thumbnail(idx, title_lines, char, accent)


# ── 전환 3종 ────────────────────────────────────────────────────────────────


def gen_transition_paper() -> None:
    """전환 paper: 종이 접힘 시뮬레이션 (1920×1080, RGB)."""
    W, H = 1920, 1080
    img = Image.new("RGB", (W, H))
    draw = ImageDraw.Draw(img)

    # 크림 → 어두운 그라데이션 (좌→우)
    for x in range(W):
        t = x / W
        # 좌: 따뜻한 크림 / 우: 다크
        r = int(CREAM[0] * (1 - t) + DARK[0] * t)
        g = int(CREAM[1] * (1 - t) + DARK[1] * t)
        b = int(CREAM[2] * (1 - t) + DARK[2] * t)
        draw.line([(x, 0), (x, H)], fill=(r, g, b))

    # 종이 접힘 선 (중앙 세로)
    fold_x = W // 2
    # 그림자
    for i in range(8, 0, -1):
        draw.line([(fold_x + i, 0), (fold_x + i, H)],
                  fill=(0, 0, 0), width=1)
    # 반짝이는 흰 접힘 선
    for i in range(3):
        draw.line([(fold_x - 2 + i, 0), (fold_x - 2 + i, H)],
                  fill=(220, 220, 220), width=1)

    # 중앙 로고 원 (민트)
    r_logo = 100
    cx, cy = fold_x, H // 2
    draw.ellipse([cx - r_logo, cy - r_logo, cx + r_logo, cy + r_logo],
                 outline=MINT, width=5)
    draw.ellipse([cx - r_logo + 12, cy - r_logo + 12,
                  cx + r_logo - 12, cy + r_logo - 12],
                 outline=MINT, width=2)
    # 별 장식
    draw_star(draw, cx, cy, 40, GOLD, n_points=4)

    img.save(CH1_DIR / "templates" / "transition_paper.png", "PNG")
    logger.info("[OK] transition_paper.png (1920×1080)")


def gen_transition_ink() -> None:
    """전환 ink: 잉크 번짐 방사형 그라데이션 (1920×1080, RGB)."""
    W, H = 1920, 1080
    img = Image.new("RGB", (W, H), WHITE)
    draw = ImageDraw.Draw(img)
    cx, cy = W // 2, H // 2
    max_r = int(math.sqrt(cx ** 2 + cy ** 2)) + 20

    # 방사형: 중앙 다크 → 외곽 민트 → 흰색
    steps = 100
    for i in range(steps, 0, -1):
        t = i / steps
        r_curr = int(max_r * (1 - t * 0.75))
        if t > 0.6:
            # 중앙 (다크)
            t2 = (t - 0.6) / 0.4
            color = (
                int(DARK[0] * t2 + MINT[0] * (1 - t2)),
                int(DARK[1] * t2 + MINT[1] * (1 - t2)),
                int(DARK[2] * t2 + MINT[2] * (1 - t2)),
            )
        else:
            # 외곽 (민트 → 흰색)
            t2 = t / 0.6
            color = (
                int(MINT[0] * t2 + WHITE[0] * (1 - t2)),
                int(MINT[1] * t2 + WHITE[1] * (1 - t2)),
                int(MINT[2] * t2 + WHITE[2] * (1 - t2)),
            )
        draw.ellipse([cx - r_curr, cy - r_curr, cx + r_curr, cy + r_curr],
                     fill=color)

    # 잉크 번짐 점 (랜덤 — seed 고정)
    rng = random.Random(42)
    for _ in range(18):
        bx = rng.randint(cx - 380, cx + 380)
        by = rng.randint(cy - 280, cy + 280)
        br = rng.randint(6, 36)
        draw.ellipse([bx - br, by - br, bx + br, by + br], fill=DARK)

    img.save(CH1_DIR / "templates" / "transition_ink.png", "PNG")
    logger.info("[OK] transition_ink.png (1920×1080)")


def gen_transition_zoom() -> None:
    """전환 zoom: 확대 동심원 (1920×1080, RGB)."""
    W, H = 1920, 1080
    img = Image.new("RGB", (W, H), DARK)
    draw = ImageDraw.Draw(img)
    cx, cy = W // 2, H // 2
    max_r = 720

    # 방사선 (얇고 연함)
    n_lines = 12
    for i in range(n_lines):
        angle = math.pi * 2 * i / n_lines
        x1 = cx + int(70 * math.cos(angle))
        y1 = cy + int(70 * math.sin(angle))
        x2 = cx + int(max_r * math.cos(angle))
        y2 = cy + int(max_r * math.sin(angle))
        draw.line([(x1, y1), (x2, y2)], fill=(MINT[0] // 4, MINT[1] // 4, MINT[2] // 4), width=1)

    # 동심원 (밖 → 안, 민트/골드 교대)
    n_rings = 14
    for i in range(n_rings):
        t = i / n_rings
        r = int(max_r * (1 - t * 0.93))
        color = MINT if i % 2 == 0 else GOLD
        draw.ellipse([cx - r, cy - r, cx + r, cy + r],
                     outline=color, width=3)

    # 중앙 채움 (민트)
    ir = 62
    draw.ellipse([cx - ir, cy - ir, cx + ir, cy + ir], fill=MINT)
    # 중앙 별 장식 (다크)
    draw_star(draw, cx, cy, ir - 12, DARK, n_points=4)

    img.save(CH1_DIR / "templates" / "transition_zoom.png", "PNG")
    logger.info("[OK] transition_zoom.png (1920×1080)")


# ── 메인 ─────────────────────────────────────────────────────────────────────


def generate_ch1_assets() -> None:
    """CH1 PIL 에셋 전체 생성 (16종)."""
    logger.info("=" * 60)
    logger.info("CH1 PIL 에셋 생성 시작 (16종)")
    logger.info("=" * 60)

    # 인트로 분해 요소
    gen_intro_frame()
    gen_intro_text()
    gen_intro_character()
    gen_intro_sparkle()

    # 아웃트로 분해 요소
    gen_outro_background()
    gen_outro_bill()
    gen_outro_character()
    gen_outro_cta()

    # 자막바 3종
    gen_subtitle_bar_key()
    gen_subtitle_bar_dialog()
    gen_subtitle_bar_info()

    # 썸네일 3종
    gen_thumbnails()

    # 전환 3종
    gen_transition_paper()
    gen_transition_ink()
    gen_transition_zoom()

    logger.info("=" * 60)
    logger.info("[완료] CH1 에셋 16종 생성 완료")
    logger.info("=" * 60)


if __name__ == "__main__":
    generate_ch1_assets()
