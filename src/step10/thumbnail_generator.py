"""STEP 10 — PIL 합성 기반 썸네일 생성 (Figma 베이스 + 텍스트 레이어)."""
import re
from pathlib import Path

from loguru import logger
from PIL import Image, ImageDraw, ImageFont

# ── 프로젝트 루트 ──────────────────────────────────────────────────────────────
_ROOT = Path(__file__).resolve().parents[2]

# ── 채널별 베이스 템플릿 경로 ──────────────────────────────────────────────────
CHANNEL_BASE_TEMPLATES: dict[str, Path] = {
    "CH1": _ROOT / "assets/channels/CH1/thumbnails/base.png",
    "CH2": _ROOT / "assets/channels/CH2/thumbnails/base.png",
    "CH3": _ROOT / "assets/channels/CH3/thumbnails/base.png",
    "CH4": _ROOT / "assets/channels/CH4/thumbnails/base.png",
    "CH5": _ROOT / "assets/channels/CH5/thumbnails/base.png",
    "CH6": _ROOT / "assets/channels/CH6/thumbnails/base.png",
    "CH7": _ROOT / "assets/channels/CH7/thumbnails/base.png",
}

# ── 채널별 색상 스펙 ───────────────────────────────────────────────────────────
CHANNEL_COLORS: dict[str, dict] = {
    "CH1": {"overlay": (180, 120,  0, 235), "top_line": (255, 215,   0), "primary": "#FFD700", "name": "경제"},
    "CH2": {"overlay": (  0,  60,  80, 235), "top_line": ( 77, 208, 225), "primary": "#4DD0E1", "name": "과학"},
    "CH3": {"overlay": (  0,  80,  0, 235), "top_line": ( 76, 175,  80), "primary": "#4CAF50", "name": "부동산"},
    "CH4": {"overlay": ( 80,   0, 120, 235), "top_line": (206, 147, 216), "primary": "#CE93D8", "name": "심리"},
    "CH5": {"overlay": (100,  20,   0, 235), "top_line": (255, 112,  67), "primary": "#FF7043", "name": "미스터리"},
    "CH6": {"overlay": ( 80,  55,   0, 235), "top_line": (200, 169, 110), "primary": "#C8A96E", "name": "역사"},
    "CH7": {"overlay": (120,  20,  20, 235), "top_line": (239, 154, 154), "primary": "#EF9A9A", "name": "전쟁사"},
}

# ── 폰트 ─────────────────────────────────────────────────────────────────────
_FONT_CANDIDATES = [
    Path("C:/Windows/Fonts/malgun.ttf"),                                    # Windows
    Path("/usr/share/fonts/truetype/nanum/NanumGothic.ttf"),               # Ubuntu
    Path("/System/Library/Fonts/AppleSDGothicNeo.ttc"),                    # macOS
]


def _load_font(size: int) -> ImageFont.FreeTypeFont:
    """플랫폼별 한국어 폰트 탐색, 실패 시 기본 폰트 반환."""
    for candidate in _FONT_CANDIDATES:
        if candidate.exists():
            try:
                return ImageFont.truetype(str(candidate), size)
            except Exception:
                continue
    logger.warning("[STEP10] 한국어 폰트 없음 — 텍스트가 깨질 수 있음")
    return ImageFont.load_default()


def _hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    """#RRGGBB → (R, G, B)."""
    h = hex_color.lstrip("#")
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))  # type: ignore


def _wrap_text(text: str, max_chars: int = 16) -> list[str]:
    """제목을 max_chars 기준으로 최대 2줄 분리."""
    if len(text) <= max_chars:
        return [text]
    words = text.split()
    if len(words) == 1:
        # 공백 없는 한국어: 글자 수 기준 강제 분리
        return [text[:max_chars], text[max_chars:max_chars * 2]]
    line1: list[str] = []
    line2: list[str] = []
    for w in words:
        if len(" ".join(line1 + [w])) <= max_chars:
            line1.append(w)
        else:
            line2.append(w)
    if not line1:
        return [text[:max_chars], text[max_chars:max_chars * 2]]
    return [" ".join(line1), " ".join(line2)] if line2 else [" ".join(line1)]


def _draw_title(
    draw: ImageDraw.ImageDraw,
    title: str,
    mode: str,
    colors: dict,
    W: int,
    y: int,
) -> None:
    """mode별 제목 텍스트 렌더링."""
    primary_rgb = _hex_to_rgb(colors["primary"])

    if mode == "02":
        m = re.search(r'\d+', title)
        if m:
            number_str = m.group()
            rest = (title[:m.start()].strip() + " " + title[m.end():].strip()).strip()
            font_num = _load_font(160)
            font_rest = _load_font(72)
            draw.text((48, y - 30), number_str, font=font_num, fill=primary_rgb)
            for i, line in enumerate(_wrap_text(rest)[:2]):
                draw.text((320, y + i * 88), line, font=font_rest, fill=(255, 255, 255))
            return
        # 숫자 없으면 아래 기본 경로(mode 01)로 fall-through

    if mode == "03":
        words = title.split()
        last_word = words[-1] + "?"
        rest = " ".join(words[:-1])
        font_title = _load_font(80)
        lines = _wrap_text(rest)
        for i, line in enumerate(lines[:2]):
            draw.text((48, y + i * 96), line, font=font_title, fill=(255, 255, 255))
        draw.text((48, y + len(lines) * 96), last_word, font=font_title, fill=primary_rgb)
        return

    # mode 01 기본: 흰색 텍스트
    font_title = _load_font(80)
    for i, line in enumerate(_wrap_text(title)[:2]):
        draw.text((48, y + i * 96), line, font=font_title, fill=(255, 255, 255))


def _compose_thumbnail(
    base_img: Image.Image,
    channel_id: str,
    title: str,
    mode: str,
) -> Image.Image:
    """베이스 이미지 위에 4레이어 합성."""
    W, H = 1920, 1080
    img = base_img.convert("RGBA").resize((W, H), Image.LANCZOS)
    draw = ImageDraw.Draw(img)
    colors = CHANNEL_COLORS.get(channel_id, CHANNEL_COLORS["CH1"])

    # Layer 2: 하단 38% 반투명 오버레이
    overlay_top = int(H * 0.62)
    overlay = Image.new("RGBA", (W, H - overlay_top), colors["overlay"])
    img.paste(overlay, (0, overlay_top), overlay)

    # 상단 구분선
    draw.rectangle([(0, overlay_top), (W, overlay_top + 4)], fill=colors["top_line"])

    # Layer 3: 채널명 소형 텍스트
    font_label = _load_font(40)
    label_text = f"{channel_id} · {colors['name']}"
    draw.text((48, overlay_top + 18), label_text, font=font_label, fill=colors["top_line"])

    # Layer 4: 제목 텍스트
    _draw_title(draw, title, mode, colors, W, overlay_top + 72)

    return img.convert("RGB")


def _generate_placeholder(title: str, output_path: Path) -> bool:
    """베이스 없을 때 단색 플레이스홀더 생성."""
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        img = Image.new("RGB", (1920, 1080), color=(30, 30, 30))
        draw = ImageDraw.Draw(img)
        font = _load_font(80)
        draw.text((60, 480), title[:32], font=font, fill=(200, 200, 200))
        img.save(str(output_path))
        return True
    except Exception as e:
        logger.warning(f"[STEP10] 플레이스홀더 생성 실패: {e}")
        return False


def generate_thumbnail_from_topic(channel_id: str, run_id: str, topic: dict) -> bool:
    """주제(topic dict)만으로 썸네일 초안 생성 — script.json 불필요.

    Step08 실행 전 '썸네일 먼저' 워크플로우용.
    runs/{channel_id}/{run_id}/step10/thumbnail_preview.png 에 저장.
    """
    from src.core.ssot import get_run_dir
    title = topic.get("reinterpreted_title") or topic.get("topic", "제목 없음")
    run_dir  = get_run_dir(channel_id, run_id)
    out_dir  = run_dir / "step10"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "thumbnail_preview.png"
    ok = generate_thumbnail(channel_id, title, "01", out_path)
    if ok:
        logger.info(f"[STEP10] 썸네일 초안 생성: {out_path}")
    return ok


def generate_thumbnail(channel_id: str, title: str, mode: str, output_path: Path) -> bool:
    """채널 베이스 PNG + PIL 합성으로 썸네일 생성.

    Args:
        channel_id: "CH1" ~ "CH7"
        title: 영상 제목
        mode: "01" | "02" | "03"
        output_path: 저장 경로 (.png)

    Returns:
        True: 성공 (합성 또는 플레이스홀더)
        False: 완전 실패
    """
    base_path = CHANNEL_BASE_TEMPLATES.get(channel_id)
    if not base_path or not base_path.exists():
        logger.warning(f"[STEP10] 베이스 없음({channel_id}) → 플레이스홀더")
        return _generate_placeholder(title, output_path)

    try:
        base_img = Image.open(base_path)
        result = _compose_thumbnail(base_img, channel_id, title, mode)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        result.save(str(output_path))
        logger.info(f"[STEP10] 썸네일 생성: {output_path.name} (mode={mode})")
        return True
    except Exception as e:
        logger.warning(f"[STEP10] PIL 합성 실패 → 플레이스홀더: {e}")
        return _generate_placeholder(title, output_path)
