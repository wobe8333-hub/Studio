"""STEP 10 — 에피소드 일러스트 기반 썸네일 합성 (사물궁이 스타일).

레이어 구조:
  L1 (풀스크린): Gemini 에피소드 일러스트 (episode_illustration.py)
  L2 (상단):     텍스트 가독성 그라디언트 오버레이
  L3 (텍스트):   외곽선 제목 2줄 (흰색 + 채널 primary 색)
  L4 (우상단):   채널 로고 워터마크 128×128
  L5 (하단):     얇은 반투명 스트립 + 채널명 라벨

AI 호출은 episode_illustration.py 에 위임. 이 파일은 PIL 합성만 담당.
⚠️ genai / google.generativeai 임포트 금지 (steps.md 규칙).
"""
from pathlib import Path

from loguru import logger
from PIL import Image, ImageDraw, ImageFont

from src.step10.episode_illustration import CHANNEL_MASCOT_PERSONA, generate_episode_illustration

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
    "CH1": {"band": (180, 120,  0, 230), "highlight": (255, 215,   0), "primary": "#FFD700", "name": "머니그래픽"},  # noqa: E501
    "CH2": {"band": (  0,  60,  80, 230), "highlight": ( 77, 208, 225), "primary": "#4DD0E1", "name": "가설낙서"},   # noqa: E501
    "CH3": {"band": (  0,  80,   0, 230), "highlight": ( 76, 175,  80), "primary": "#4CAF50", "name": "홈팔레트"},   # noqa: E501
    "CH4": {"band": ( 80,   0, 120, 230), "highlight": (206, 147, 216), "primary": "#CE93D8", "name": "오묘한심리"},  # noqa: E501
    "CH5": {"band": (100,  20,   0, 230), "highlight": (255, 112,  67), "primary": "#FF7043", "name": "검은물음표"},  # noqa: E501
    "CH6": {"band": ( 80,  55,   0, 230), "highlight": (200, 169, 110), "primary": "#C8A96E", "name": "오래된두루마리"},  # noqa: E501
    "CH7": {"band": (120,  20,  20, 230), "highlight": (239, 154, 154), "primary": "#EF9A9A", "name": "워메이징"},   # noqa: E501
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


def _split_title_smart(title: str) -> tuple[str, str]:
    """제목을 임팩트 2줄로 분리. 두 번째 줄이 채널 primary 색으로 강조된다."""
    words = title.split()
    if len(words) <= 1:
        return title, ""
    # "?" 기준: 앞/뒤 분리
    if "?" in title:
        q = title.index("?")
        prefix_words = title[:q].split()
        mid = max(1, len(prefix_words) * 2 // 3)
        return " ".join(prefix_words[:mid]), " ".join(prefix_words[mid:]) + "?"
    mid = max(1, len(words) // 2)
    return " ".join(words[:mid]), " ".join(words[mid:])


def _draw_outlined_text(
    draw: ImageDraw.ImageDraw,
    pos: tuple[int, int],
    text: str,
    font: ImageFont.FreeTypeFont,
    fill: tuple,
    outline_color: tuple = (0, 0, 0),
    outline_width: int = 8,
) -> None:
    """검은 외곽선 텍스트 (YouTube 썸네일 표준)."""
    x, y = pos
    for dx in range(-outline_width, outline_width + 1, 3):
        for dy in range(-outline_width, outline_width + 1, 3):
            if dx != 0 or dy != 0:
                draw.text((x + dx, y + dy), text, font=font, fill=outline_color)
    draw.text(pos, text, font=font, fill=fill)


def _draw_top_title(
    draw: ImageDraw.ImageDraw,
    title: str,
    colors: dict,
    W: int,
    H: int,
    mode: str,
) -> None:
    """상단 제목: 흰색 1줄 + 채널 primary 색 2줄. mode 04는 빨간 원·화살표 추가."""
    primary_rgb = _hex_to_rgb(colors["primary"])
    pad_x = 50

    # mode 04 (미스터리·전쟁): 이미지 중앙에 빨간 원 + 화살표
    if mode == "04":
        cx, cy, cr = int(W * 0.26), int(H * 0.58), 72
        draw.ellipse(
            [(cx - cr, cy - cr), (cx + cr, cy + cr)],
            fill=None, outline=(220, 20, 20), width=9,
        )
        draw.polygon(
            [(cx + cr + 12, cy - 28), (cx + cr + 100, cy), (cx + cr + 12, cy + 28)],
            fill=(255, 50, 50),
        )

    line1, line2 = _split_title_smart(title)

    font1 = _load_font(115)
    y1 = 40
    if line1:
        _draw_outlined_text(draw, (pad_x, y1), line1, font1, fill=(255, 255, 255))

    font2 = _load_font(132)
    y2 = y1 + 126
    if line2:
        _draw_outlined_text(draw, (pad_x, y2), line2, font2, fill=primary_rgb)


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


def _compose_thumbnail(
    base_img: Image.Image,
    channel_id: str,
    title: str,
    mode: str,
) -> Image.Image:
    """사물궁이 스타일 합성: L1 풀스크린 일러스트 + L2 상단 그라디언트
    + L3 외곽선 제목(상단) + L4 워터마크 + L5 하단 채널 라벨."""
    W, H = 1920, 1080
    img = base_img.convert("RGBA").resize((W, H), Image.LANCZOS)
    colors = CHANNEL_COLORS.get(channel_id, CHANNEL_COLORS["CH1"])

    # L2: 상단 텍스트 가독성 그라디언트 (위→투명, 높이 44%)
    text_zone_h = int(H * 0.44)
    grad = Image.new("RGBA", (W, text_zone_h), (0, 0, 0, 0))
    for y in range(text_zone_h):
        alpha = int(190 * (1.0 - (y / text_zone_h) ** 0.55))
        Image.new("RGBA", (W, 1), (0, 0, 0, alpha)).save  # type: ignore
        grad.paste(Image.new("RGBA", (W, 1), (0, 0, 0, alpha)), (0, y))
    img.paste(grad, (0, 0), grad)

    # L5 바탕: 하단 얇은 반투명 스트립 (채널명 라벨용)
    strip_h = int(H * 0.07)
    img.paste(
        Image.new("RGBA", (W, strip_h), (0, 0, 0, 155)),
        (0, H - strip_h),
        Image.new("RGBA", (W, strip_h), (0, 0, 0, 155)),
    )

    # L4: 워터마크 (우상단 128×128)
    wm_path = _WATERMARK_PATHS.get(channel_id)
    fb_path = _LOGO_FALLBACK.get(channel_id)
    wm_src = (
        wm_path if (wm_path and wm_path.exists())
        else (fb_path if (fb_path and fb_path.exists()) else None)
    )
    if wm_src:
        try:
            wm = Image.open(wm_src).convert("RGBA").resize((128, 128), Image.LANCZOS)
            img.paste(wm, (W - 128 - 24, 20), wm)
        except Exception as e:
            logger.debug(f"[STEP10] 워터마크 합성 실패 (무시): {e}")

    draw = ImageDraw.Draw(img)

    # L3: 외곽선 제목 2줄 (상단)
    _draw_top_title(draw, title, colors, W, H, mode)

    # L5 텍스트: 채널명 라벨 (하단 스트립)
    font_label = _load_font(34)
    draw.text((50, H - strip_h + 12), colors["name"], font=font_label, fill=colors["highlight"])

    return img.convert("RGB")


def _get_preferred_mode(channel_id: str) -> str:
    """채널 카테고리에 따라 최적 mode를 반환.

    정보형(CH1·3·6): mode 02 (숫자 리스트 강조)
    자극형(CH2·4): mode 03 (질문형)
    자극형 강(CH5·7): mode 04 (빨간 원 + 화살표 어텐션)
    """
    info = CHANNEL_MASCOT_PERSONA.get(channel_id, {})
    category = info.get("category", "info") if isinstance(info, dict) else "info"
    if category == "stimulating_strong":
        return "04"
    if category == "stimulating":
        return "03"
    return "02"


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
    mode = _get_preferred_mode(channel_id)
    ok = generate_thumbnail(channel_id, title, mode, out_path, run_id=run_id)
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
