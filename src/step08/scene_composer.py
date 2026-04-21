"""
STEP 08 — 장면 합성기.

Phase 5 추가:
  캐릭터 이미지 + 배경 + 텍스트 말풍선 레이어 합성 (PIL 기반).
"""

from pathlib import Path
from typing import Optional

from loguru import logger


def compose_scene(
    character_path: Path,
    background_path: Optional[Path],
    narration_text: str,
    output_path: Path,
    width: int = 1920,
    height: int = 1080,
) -> bool:
    """
    캐릭터 + 배경 + 텍스트 합성 → 단일 장면 이미지.

    Args:
        character_path: 캐릭터 PNG 이미지
        background_path: 배경 이미지 (없으면 단색)
        narration_text: 자막/말풍선 텍스트 (앞 60자)
        output_path: 합성 결과 저장 경로
        width, height: 출력 해상도

    Returns:
        True: 성공
    """
    try:

        from PIL import Image, ImageDraw, ImageFont

        # 1) 배경 레이어
        if background_path and background_path.exists():
            bg = Image.open(background_path).convert("RGBA").resize((width, height))
        else:
            bg = Image.new("RGBA", (width, height), (30, 30, 50, 255))

        canvas = bg.copy()

        # 2) 캐릭터 레이어 (오른쪽 하단 배치, 높이의 60% 크기)
        if character_path and character_path.exists():
            char = Image.open(character_path).convert("RGBA")
            char_h = int(height * 0.6)
            char_w = int(char.width * char_h / char.height)
            char = char.resize((char_w, char_h), Image.LANCZOS)

            # 투명도 유지하며 합성
            char_x = width - char_w - 50
            char_y = height - char_h - 20
            canvas.paste(char, (char_x, char_y), char)

        # 3) 텍스트 오버레이 (하단 자막 바)
        if narration_text:
            draw = ImageDraw.Draw(canvas)
            text = narration_text[:60] + ("..." if len(narration_text) > 60 else "")

            # 자막 배경 반투명 박스
            bar_h = 80
            bar_y = height - bar_h - 10
            draw.rectangle([(0, bar_y), (width, height)], fill=(0, 0, 0, 160))

            # 텍스트 중앙 정렬
            try:
                # 시스템 폰트 시도
                font = ImageFont.truetype("malgun.ttf", 32)
            except Exception:
                font = ImageFont.load_default()

            bbox = draw.textbbox((0, 0), text, font=font)
            text_w = bbox[2] - bbox[0]
            text_x = (width - text_w) // 2
            text_y = bar_y + (bar_h - (bbox[3] - bbox[1])) // 2

            # 외곽선 (가독성)
            for dx, dy in [(-2, -2), (2, -2), (-2, 2), (2, 2)]:
                draw.text((text_x + dx, text_y + dy), text, font=font, fill=(0, 0, 0, 255))
            draw.text((text_x, text_y), text, font=font, fill=(255, 255, 255, 255))

        # 저장
        output_path.parent.mkdir(parents=True, exist_ok=True)
        canvas.convert("RGB").save(str(output_path), "PNG")
        return True

    except Exception as e:
        logger.debug(f"[SceneComposer] 합성 실패: {e}")
        return False


def compose_all_scenes(
    character_paths: list,
    script_sections: list,
    output_dir: Path,
    width: int = 1920,
    height: int = 1080,
) -> list:
    """섹션별 장면 이미지 일괄 합성."""
    output_dir.mkdir(parents=True, exist_ok=True)
    composed = []

    for i, (char_path, section) in enumerate(zip(character_paths, script_sections)):
        out_path = output_dir / f"composed_{i:03d}.png"
        narration = section.get("narration_text", "")[:60]

        ok = compose_scene(
            character_path=char_path,
            background_path=None,  # 향후 배경 생성 연동
            narration_text=narration,
            output_path=out_path,
            width=width,
            height=height,
        )
        if ok:
            composed.append(out_path)

    logger.info(f"[SceneComposer] {len(composed)}/{len(character_paths)} 장면 합성 완료")
    return composed
