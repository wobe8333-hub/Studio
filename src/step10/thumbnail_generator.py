"""STEP 10 — 에피소드 일러스트 기반 썸네일 합성 (사물궁이 스타일).

레이어 구조:
  L1 (풀스크린): Gemini 배경 전용 일러스트 (episode_illustration.py)
  L2 (캐릭터):   RunPod SD XL + LoRA 의상 캐릭터 (오른쪽 중앙)
  L3 (텍스트):   외곽선 제목 2줄 — 흰색 + 키워드만 채널 primary 색

AI 호출은 episode_illustration.py 에 위임. 이 파일은 PIL 합성만 담당.
⚠️ genai / google.generativeai 임포트 금지 (steps.md 규칙).
"""
import hashlib
import io
import os as _os
from pathlib import Path
from typing import Optional

from loguru import logger
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont

from src.step10.episode_illustration import (
    generate_background_illustration,
    generate_episode_illustration,
)

# ── 프로젝트 루트 (KAS_ROOT 우선 — 워크트리에서도 메인 에셋 참조) ────────────────
_ROOT = (
    Path(_os.environ["KAS_ROOT"]) if _os.environ.get("KAS_ROOT")
    else Path(__file__).resolve().parents[2]
)

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
    "CH1": {"primary": "#FFD700", "name": "머니그래픽"},
    "CH2": {"primary": "#4DD0E1", "name": "가설낙서"},
    "CH3": {"primary": "#4CAF50", "name": "홈팔레트"},
    "CH4": {"primary": "#CE93D8", "name": "오묘한심리"},
    "CH5": {"primary": "#FF7043", "name": "검은물음표"},
    "CH6": {"primary": "#C8A96E", "name": "오래된두루마리"},
    "CH7": {"primary": "#EF9A9A", "name": "워메이징"},
}

# ── 폰트 — 가독성 최우선 (유튜브 썸네일 표준) ───────────────────────────────
_FONT_CANDIDATES = [
    Path("C:/Windows/Fonts/malgunbd.ttf"),           # 맑은 고딕 Bold — 선명하고 굵음
    Path("C:/Windows/Fonts/malgun.ttf"),             # 맑은 고딕 Regular
    _ROOT / "assets/fonts/NanumBrush.ttf",
    Path("C:/Users/조찬우/Desktop/ai_stuidio_claude/assets/fonts/NanumBrush.ttf"),
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
    outline_width: int = 13,
) -> None:
    """검은 외곽선 텍스트 — 어떤 배경에서도 가독성 확보 (outline_width=13)."""
    x, y = pos
    for dx in range(-outline_width, outline_width + 1, 3):
        for dy in range(-outline_width, outline_width + 1, 3):
            if dx != 0 or dy != 0:
                draw.text((x + dx, y + dy), text, font=font, fill=outline_color)
    draw.text(pos, text, font=font, fill=fill)


def _measure_line_width(words: list[str], font: ImageFont.FreeTypeFont) -> float:
    total = 0.0
    for word in words:
        try:
            bbox = font.getbbox(word + " ")
            total += bbox[2] - bbox[0]
        except Exception:
            total += len(word) * font.size * 0.65
    return total


def _draw_word_line(
    draw: ImageDraw.ImageDraw,
    words: list[str],
    y: int,
    font: ImageFont.FreeTypeFont,
    primary_rgb: tuple,
    keyword_indices: set[int],
    pad_x: int = 60,
    outline_width: int = 8,
    max_width: int = 1860,
) -> None:
    """단어별 색상 렌더링. max_width 초과 시 폰트 자동 축소."""
    line_w = _measure_line_width(words, font)
    available = max_width - pad_x
    if line_w > available:
        scale = available / line_w
        try:
            font = ImageFont.truetype(font.path, max(40, int(font.size * scale)))
        except Exception:
            pass

    x = float(pad_x)
    for i, word in enumerate(words):
        color = primary_rgb if i in keyword_indices else (255, 255, 255)
        _draw_outlined_text(draw, (int(x), y), word, font, fill=color,
                            outline_width=outline_width)
        try:
            bbox = font.getbbox(word + " ")
            x += bbox[2] - bbox[0]
        except Exception:
            x += len(word) * font.size * 0.65


def _pick_text_zone(title: str) -> str:
    """제목 위치 결정 — title MD5 기반 (재현 가능).

    142장 실측: bottom 39%, top 20% → 가중치 idx 0~6 → top (35%), idx 7~19 → bottom (65%)
    """
    idx = int(hashlib.md5(title.encode("utf-8")).hexdigest()[:8], 16) % 20
    return "top" if idx < 7 else "bottom"


def _keyword_indices(words: list[str]) -> set[int]:
    """숫자 포함 단어 우선 강조, 없으면 마지막 단어."""
    has_digit = {i for i, w in enumerate(words) if any(c.isdigit() for c in w)}
    return has_digit if has_digit else {len(words) - 1}


def _draw_title(
    draw: ImageDraw.ImageDraw,
    title: str,
    colors: dict,
    W: int,
    H: int,
    zone: str = "bottom",
) -> None:
    """제목 2줄 렌더링.

    - 왼쪽 정렬 (x=40px)
    - line1: 흰색 90px / line2: 키워드 primary 색 118px
    - 외곽선 13px
    """
    primary_rgb = _hex_to_rgb(colors["primary"])
    pad_x = 40
    outline = 13

    line1, line2 = _split_title_smart(title)
    font1 = _load_font(90)
    font2 = _load_font(118)

    def _line_h(f: ImageFont.FreeTypeFont) -> int:
        try:
            bb = f.getbbox("가나다")
            return bb[3] - bb[1]
        except Exception:
            return f.size + 8

    h1 = _line_h(font1)
    h2 = _line_h(font2)
    gap = 12

    if zone == "top":
        y1 = 40
        y2 = y1 + h1 + gap
    else:
        y2 = H - 44 - h2
        y1 = y2 - gap - h1

    if line1:
        _draw_word_line(draw, line1.split(), y1, font1, primary_rgb,
                        keyword_indices=set(), pad_x=pad_x, outline_width=outline)
    if line2:
        words2 = line2.split()
        _draw_word_line(draw, words2, y2, font2, primary_rgb,
                        keyword_indices=_keyword_indices(words2),
                        pad_x=pad_x, outline_width=outline)


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


def _remove_background(img: Image.Image) -> Image.Image:
    """배경 제거. rembg 우선 → 흰색 임계값 폴백.

    RunPod이 순수 흰 배경으로 생성한 캐릭터 PNG에서 배경 제거.
    """
    try:
        from rembg import remove as rembg_remove
        buf = io.BytesIO()
        img.convert("RGB").save(buf, format="PNG")
        out_bytes = rembg_remove(buf.getvalue())
        return Image.open(io.BytesIO(out_bytes)).convert("RGBA")
    except (ImportError, SystemExit):
        # rembg 미설치 or onnxruntime 없음 → 흰 배경 폴백
        pass
    except Exception as e:
        logger.debug(f"[STEP10] rembg 실패: {e}")

    # 폴백: 흰색(240+) 픽셀 → 투명
    rgba = img.convert("RGBA")
    data = list(rgba.getdata())
    new_data = [
        (r, g, b, 0) if r > 240 and g > 240 and b > 240 else (r, g, b, a)
        for r, g, b, a in data
    ]
    rgba.putdata(new_data)
    # 경계 부드럽게 — 가우시안 블러 마스크로 안티앨리어싱
    try:
        r_ch, g_ch, b_ch, a_ch = rgba.split()
        a_smooth = a_ch.filter(ImageFilter.GaussianBlur(radius=1))
        rgba = Image.merge("RGBA", (r_ch, g_ch, b_ch, a_smooth))
    except Exception:
        pass
    return rgba


def _composite_character(
    base: Image.Image,
    char_img: Image.Image,
    height_ratio: float = 0.65,
) -> Image.Image:
    """L2 캐릭터를 오른쪽 중앙에 합성.

    142장 실측: 캐릭터 right-center ~45%, 프레임 높이의 40~65% 차지.
    x 중심 = 화면의 72% (오른쪽 중심), y 중심 = 수직 중앙.
    """
    W, H = base.size
    target_h = int(H * height_ratio)
    aspect = char_img.width / char_img.height if char_img.height > 0 else 1.0
    target_w = int(target_h * aspect)

    char_resized = char_img.resize((target_w, target_h), Image.LANCZOS)

    # 오른쪽 중앙 배치 (수평 72%, 수직 50%)
    x = int(W * 0.72) - target_w // 2
    y = int(H * 0.50) - target_h // 2

    # 화면 범위 클리핑
    x = max(0, min(x, W - target_w))
    y = max(0, min(y, H - target_h))

    result = base.copy().convert("RGBA")
    result.paste(char_resized, (x, y), char_resized)
    return result


def _compose_thumbnail(
    base_img: Image.Image,
    channel_id: str,
    title: str,
    char_img: Optional[Image.Image] = None,
) -> Image.Image:
    """L1 배경 + L2 캐릭터(선택) + L3 외곽선 제목 합성."""
    W, H = 1920, 1080
    colors = CHANNEL_COLORS.get(channel_id, CHANNEL_COLORS["CH1"])

    # L1: 배경 파스텔 보정 (채도 0.88)
    img_rgb = base_img.convert("RGB").resize((W, H), Image.LANCZOS)
    img_rgb = ImageEnhance.Color(img_rgb).enhance(0.88)
    img = img_rgb.convert("RGBA")

    # L2: 캐릭터 합성 (오른쪽 중앙)
    if char_img is not None:
        try:
            img = _composite_character(img, char_img)
        except Exception as e:
            logger.warning(f"[STEP10] L2 캐릭터 합성 실패 (스킵): {e}")

    # L3: 제목 텍스트
    zone = _pick_text_zone(title)
    draw = ImageDraw.Draw(img)
    _draw_title(draw, title, colors, W, H, zone=zone)

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


def generate_thumbnail(
    channel_id: str,
    title: str,
    output_path: Path,
    *,
    run_id: str = "unknown",
    force_parody: bool = False,
) -> bool:
    """3-레이어 썸네일 생성.

    L1: Gemini 배경 전용 일러스트 (generate_background_illustration)
    L2: RunPod SD XL + LoRA 의상 캐릭터 (오른쪽 중앙)
    L3: 외곽선 제목 — 키워드만 채널 primary 색, 나머지 흰색

    RunPod 미설정 시 L2 없이 L1 + L3 로 graceful fallback.
    배경 생성 실패 시 채널 베이스 PNG → 플레이스홀더 순 폴백.
    """
    # ── L1: 배경 전용 일러스트 ────────────────────────────────────────────────
    bg_path = output_path.parent / "_episode_bg.png"
    bg_result = generate_background_illustration(
        channel_id, title, run_id, bg_path, force_parody=force_parody
    )

    base_img: Optional[Image.Image] = None
    if bg_result is not None:
        try:
            base_img = Image.open(bg_result)
        except Exception as e:
            logger.warning(f"[STEP10] 배경 이미지 로드 실패: {e}")

    if base_img is None:
        base_path = CHANNEL_BASE_TEMPLATES.get(channel_id)
        if base_path and base_path.exists():
            try:
                base_img = Image.open(base_path)
                logger.info(f"[STEP10] 베이스 PNG 폴백: {channel_id}")
            except Exception as e:
                logger.warning(f"[STEP10] 베이스 PNG 로드 실패 → 플레이스홀더: {e}")
                return _generate_placeholder(title, output_path)
        else:
            logger.warning(f"[STEP10] 배경 없음({channel_id}) → 플레이스홀더")
            return _generate_placeholder(title, output_path)

    # ── L2: RunPod 캐릭터 생성 ────────────────────────────────────────────────
    char_img: Optional[Image.Image] = None
    try:
        from src.adapters.runpod_sd import generate_character_to_file
        from src.step08.character_manager import (
            build_loomix_char_prompt,
            select_costume_for_topic,
        )

        costume = select_costume_for_topic(channel_id, title)
        char_prompts = build_loomix_char_prompt(
            channel_id, expression="surprised", costume=costume
        )
        char_path = output_path.parent / "_episode_char.png"
        char_ok = generate_character_to_file(
            positive_prompt=char_prompts["positive"],
            negative_prompt=char_prompts["negative"],
            output_path=char_path,
            seed=char_prompts["seed"],
            width=512,
            height=768,
        )
        if char_ok and char_path.exists():
            char_img = _remove_background(Image.open(char_path))
            logger.info(f"[STEP10] L2 캐릭터 준비: 의상={costume}")
    except Exception as e:
        logger.warning(f"[STEP10] L2 캐릭터 생성 실패 (L1+L3 만 사용): {e}")

    # ── L1 + L2 + L3 합성 ────────────────────────────────────────────────────
    try:
        result = _compose_thumbnail(base_img, channel_id, title, char_img=char_img)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        result.save(str(output_path))
        layers = "L1+L2+L3" if char_img is not None else "L1+L3"
        logger.info(f"[STEP10] 썸네일 생성 ({layers}): {output_path.name}")
        return True
    except Exception as e:
        logger.warning(f"[STEP10] PIL 합성 실패 → 플레이스홀더: {e}")
        return _generate_placeholder(title, output_path)


def generate_thumbnail_from_topic(channel_id: str, run_id: str, topic: dict) -> bool:
    """주제(topic dict)만으로 썸네일 초안 생성.

    runs/{channel_id}/{run_id}/step10/thumbnail_preview.png 에 저장.
    """
    from src.core.ssot import get_run_dir
    title = topic.get("reinterpreted_title") or topic.get("topic", "제목 없음")
    run_dir = get_run_dir(channel_id, run_id)
    out_dir = run_dir / "step10"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "thumbnail_preview.png"
    ok = generate_thumbnail(channel_id, title, out_path, run_id=run_id)
    if ok:
        logger.info(f"[STEP10] 썸네일 초안 생성: {out_path}")
    return ok
