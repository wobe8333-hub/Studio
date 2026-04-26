"""STEP 10 — 에피소드 일러스트 기반 3-레이어 썸네일 합성.

레이어 구조:
  L1 (풀스크린): Gemini 에피소드 일러스트 (episode_illustration.py)
  L2 (우상단):   채널 로고 워터마크 (128×128)
  L3 (하단 25%): 채널색 카피 밴드 + 큰 제목 텍스트

AI 호출은 episode_illustration.py 에 위임. 이 파일은 PIL 합성만 담당.
⚠️ genai / google.generativeai 임포트 금지 (steps.md 규칙).
"""
import re
from pathlib import Path

from loguru import logger
from PIL import Image, ImageDraw, ImageFont

from src.step10.episode_illustration import generate_episode_illustration

# ── 프로젝트 루트 ──────────────────────────────────────────────────────────────
_ROOT = Path(__file__).resolve().parents[2]

# ── 폴백용 채널별 베이스 템플릿 경로 ───────────────────────────────────────────
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
    "CH1": {"band": (180, 120,  0, 230), "highlight": (255, 215,   0), "primary": "#FFD700", "name": "머니그래픽"},
    "CH2": {"band": (  0,  60,  80, 230), "highlight": ( 77, 208, 225), "primary": "#4DD0E1", "name": "가설낙서"},
    "CH3": {"band": (  0,  80,   0, 230), "highlight": ( 76, 175,  80), "primary": "#4CAF50", "name": "홈팔레트"},
    "CH4": {"band": ( 80,   0, 120, 230), "highlight": (206, 147, 216), "primary": "#CE93D8", "name": "오묘한심리"},
    "CH5": {"band": (100,  20,   0, 230), "highlight": (255, 112,  67), "primary": "#FF7043", "name": "검은물음표"},
    "CH6": {"band": ( 80,  55,   0, 230), "highlight": (200, 169, 110), "primary": "#C8A96E", "name": "오래된두루마리"},
    "CH7": {"band": (120,  20,  20, 230), "highlight": (239, 154, 154), "primary": "#EF9A9A", "name": "워메이징"},
}

# ── 워터마크 경로 ──────────────────────────────────────────────────────────────
_WATERMARK_PATHS: dict[str, Path] = {
    ch: _ROOT / f"assets/channels/{ch}/badges/logo_watermark.png"
    for ch in [f"CH{i}" for i in range(1, 8)]
}
_LOGO_FALLBACK: dict[str, Path] = {
    ch: _ROOT / f"assets/channels/{ch}/logo/logo.png"
    for ch in [f"CH{i}" for i in range(1, 8)]
}

# ── 폰트 ─────────────────────────────────────────────────────────────────────
_FONT_CANDIDATES = [
    Path("C:/Windows/Fonts/malgun.ttf"),
    Path("/usr/share/fonts/truetype/nanum/NanumGothic.ttf"),
    Path("/System/Library/Fonts/AppleSDGothicNeo.ttc"),
]


def _load_font(size: int) -> ImageFont.FreeTypeFont:
    for candidate in _FONT_CANDIDATES:
        if candidate.exists():
            try:
                return ImageFont.truetype(str(candidate), size)
            except Exception:
                continue
    logger.warning("[STEP10] 한국어 폰트 없음 — 텍스트가 깨질 수 있음")
    return ImageFont.load_default()


def _hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    h = hex_color.lstrip("#")
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))  # type: ignore


def _wrap_text(text: str, max_chars: int = 14) -> list[str]:
    """제목을 max_chars 기준으로 최대 2줄 분리."""
    if len(text) <= max_chars:
        return [text]
    words = text.split()
    if len(words) == 1:
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


def _draw_caption(
    draw: ImageDraw.ImageDraw,
    title: str,
    mode: str,
    colors: dict,
    W: int,
    band_top: int,
) -> None:
    """하단 카피 밴드 위에 mode별 제목 텍스트 렌더링 (큰 글씨)."""
    primary_rgb = _hex_to_rgb(colors["primary"])
    pad_x = 48
    y0 = band_top + 16

    if mode == "02":
        m = re.search(r'\d+', title)
        if m:
            number_str = m.group()
            rest = (title[:m.start()].strip() + " " + title[m.end():].strip()).strip()
            font_num = _load_font(160)
            font_rest = _load_font(80)
            draw.text((pad_x, y0 - 20), number_str, font=font_num, fill=primary_rgb)
            for i, line in enumerate(_wrap_text(rest)[:2]):
                draw.text((340, y0 + i * 96), line, font=font_rest, fill=(255, 255, 255))
            return

    if mode == "03":
        words = title.split()
        last_word = words[-1] + "?"
        rest = " ".join(words[:-1])
        font_title = _load_font(88)
        lines = _wrap_text(rest)
        for i, line in enumerate(lines[:2]):
            draw.text((pad_x, y0 + i * 104), line, font=font_title, fill=(255, 255, 255))
        draw.text((pad_x, y0 + len(lines) * 104), last_word, font=font_title, fill=primary_rgb)
        return

    # mode 01 기본: 흰색 텍스트 (96px)
    font_title = _load_font(96)
    for i, line in enumerate(_wrap_text(title)[:2]):
        draw.text((pad_x, y0 + i * 108), line, font=font_title, fill=(255, 255, 255))


def _compose_thumbnail(
    base_img: Image.Image,
    channel_id: str,
    title: str,
    mode: str,
) -> Image.Image:
    """3-레이어 합성: L1 풀스크린 일러스트 + L2 워터마크 + L3 하단 카피 밴드."""
    W, H = 1920, 1080
    img = base_img.convert("RGBA").resize((W, H), Image.LANCZOS)
    colors = CHANNEL_COLORS.get(channel_id, CHANNEL_COLORS["CH1"])

    # L2: 우상단 채널 로고 워터마크 (128×128)
    wm_path = _WATERMARK_PATHS.get(channel_id)
    fb_path = _LOGO_FALLBACK.get(channel_id)
    wm_src = wm_path if (wm_path and wm_path.exists()) else (fb_path if (fb_path and fb_path.exists()) else None)
    if wm_src:
        try:
            wm = Image.open(wm_src).convert("RGBA").resize((128, 128), Image.LANCZOS)
            wm_x = W - 128 - 24
            wm_y = 20
            img.paste(wm, (wm_x, wm_y), wm)
        except Exception as e:
            logger.debug(f"[STEP10] 워터마크 합성 실패 (무시): {e}")

    # L3: 하단 25% 채널색 불투명 밴드
    band_top = int(H * 0.75)
    band = Image.new("RGBA", (W, H - band_top), colors["band"])
    img.paste(band, (0, band_top), band)

    # 밴드 상단 강조선 (highlight 4px)
    draw = ImageDraw.Draw(img)
    draw.rectangle([(0, band_top), (W, band_top + 4)], fill=colors["highlight"])

    # 채널명 소형 라벨 (밴드 상단 왼쪽)
    font_label = _load_font(36)
    draw.text((48, band_top + 8), colors["name"], font=font_label, fill=colors["highlight"])

    # 제목 텍스트
    _draw_caption(draw, title, mode, colors, W, band_top + 50)

    return img.convert("RGB")


def _generate_placeholder(title: str, output_path: Path) -> bool:
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
    """주제(topic dict)만으로 썸네일 초안 생성.

    Step08 실행 전 '썸네일 먼저' 워크플로우용.
    runs/{channel_id}/{run_id}/step10/thumbnail_preview.png 에 저장.
    """
    from src.core.ssot import get_run_dir
    title = topic.get("reinterpreted_title") or topic.get("topic", "제목 없음")
    run_dir = get_run_dir(channel_id, run_id)
    out_dir = run_dir / "step10"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "thumbnail_preview.png"
    ok = generate_thumbnail(channel_id, title, "01", out_path, run_id=run_id)
    if ok:
        logger.info(f"[STEP10] 썸네일 초안 생성: {out_path}")
    return ok


def generate_thumbnail(
    channel_id: str,
    title: str,
    mode: str,
    output_path: Path,
    *,
    run_id: str = "unknown",
) -> bool:
    """에피소드 일러스트 + PIL 합성으로 썸네일 생성.

    1. generate_episode_illustration() 으로 AI 풀스크린 일러스트 생성 (L1)
    2. 실패 시 채널 베이스 PNG 폴백
    3. _compose_thumbnail() 으로 3-레이어 합성 후 저장

    Args:
        channel_id: "CH1" ~ "CH7"
        title: 영상 제목 (카피 텍스트 원본)
        mode: "01" | "02" | "03"
        output_path: 저장 경로 (.png)
        run_id: 비용 추적용 실행 ID

    Returns:
        True: 성공 (합성 또는 플레이스홀더)
        False: 완전 실패
    """
    # 1. AI 에피소드 일러스트 생성
    illust_path = output_path.parent / "_episode_illust.png"
    illust = generate_episode_illustration(channel_id, title, run_id, illust_path)

    if illust is not None:
        try:
            base_img = Image.open(illust)
        except Exception as e:
            logger.warning(f"[STEP10] 일러스트 로드 실패: {e}")
            illust = None

    # 2. 폴백: 채널 베이스 PNG
    if illust is None:
        base_path = CHANNEL_BASE_TEMPLATES.get(channel_id)
        if base_path and base_path.exists():
            try:
                base_img = Image.open(base_path)
                logger.info(f"[STEP10] 베이스 PNG 폴백 사용: {channel_id}")
            except Exception as e:
                logger.warning(f"[STEP10] 베이스 PNG 로드 실패 → 플레이스홀더: {e}")
                return _generate_placeholder(title, output_path)
        else:
            logger.warning(f"[STEP10] 베이스 없음({channel_id}) → 플레이스홀더")
            return _generate_placeholder(title, output_path)

    # 3. 3-레이어 합성
    try:
        result = _compose_thumbnail(base_img, channel_id, title, mode)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        result.save(str(output_path))
        logger.info(f"[STEP10] 썸네일 생성: {output_path.name} (mode={mode})")
        return True
    except Exception as e:
        logger.warning(f"[STEP10] PIL 합성 실패 → 플레이스홀더: {e}")
        return _generate_placeholder(title, output_path)
