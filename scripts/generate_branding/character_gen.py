# scripts/generate_branding/character_gen.py
"""Gemini Imagen API로 채널 캐릭터 PNG 생성"""
import sys
import io
import os
import time

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from pathlib import Path
from dotenv import load_dotenv
from loguru import logger

load_dotenv()

sys.path.insert(0, str(Path(__file__).parent))
from config import CHANNELS, CHANNELS_DIR

from google import genai
from google.genai import types

MODEL = "imagen-4.0-generate-001"


def generate_character(
    client: genai.Client, ch_id: str, pose_key: str
) -> bool:
    """단일 캐릭터 포즈 PNG를 생성하고 저장한다."""
    cfg = CHANNELS[ch_id]
    prompt = cfg["character_prompts"][pose_key]
    out_path = CHANNELS_DIR / ch_id / "characters" / f"character_{pose_key}.png"

    # 출력 디렉토리 보장
    out_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        result = client.models.generate_images(
            model=MODEL,
            prompt=prompt,
            config=types.GenerateImagesConfig(
                number_of_images=1,
                aspect_ratio="1:1",
            ),
        )
        image_bytes = result.generated_images[0].image.image_bytes
        out_path.write_bytes(image_bytes)
        logger.info(
            f"[OK] {ch_id}/{pose_key} -> character_{pose_key}.png "
            f"({len(image_bytes):,} bytes)"
        )
        return True
    except Exception as e:
        logger.error(f"[ERR] {ch_id}/{pose_key}: {e}")
        return False
    finally:
        time.sleep(1.5)  # API rate limit 방지


def run_all() -> None:
    """모든 채널의 모든 포즈 캐릭터 PNG를 순차 생성한다."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        logger.error("GEMINI_API_KEY 환경변수가 없습니다.")
        sys.exit(1)

    client = genai.Client(api_key=api_key)
    logger.info(f"Gemini Imagen API 준비 완료 (모델: {MODEL})")

    total = 0
    success = 0
    failures: list[str] = []

    for ch_id, cfg in CHANNELS.items():
        logger.info(f"\n[{ch_id}] {cfg['name']} ({cfg['domain']}) 캐릭터 생성 시작...")
        for pose in cfg["characters"]:
            total += 1
            if generate_character(client, ch_id, pose):
                success += 1
            else:
                failures.append(f"{ch_id}/{pose}")

    logger.info(f"\n[완료] {success}/{total}개 캐릭터 PNG 생성")
    if failures:
        logger.warning(f"[실패 목록] {failures}")
    else:
        logger.info("[실패 없음] 모든 포즈 생성 성공")


if __name__ == "__main__":
    run_all()
