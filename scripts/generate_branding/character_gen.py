# scripts/generate_branding/character_gen.py
"""Gemini Imagen API로 채널 캐릭터 PNG 생성

Usage:
    python scripts/generate_branding/character_gen.py              # 전체 7채널
    python scripts/generate_branding/character_gen.py --channel CH1  # CH1만 (Best-of-3)
"""
import argparse
import io
import os
import sys
import time

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from pathlib import Path

from dotenv import load_dotenv
from loguru import logger

load_dotenv()

sys.path.insert(0, str(Path(__file__).parent))
from google import genai
from google.genai import types
from nano_banana_helper import generate_with_reference

from config import CHANNELS, CHANNELS_DIR, KAS_ROOT

MODEL = "imagen-4.0-generate-001"


def generate_character(
    client: genai.Client, ch_id: str, pose_key: str
) -> bool:
    """단일 캐릭터 포즈 PNG를 생성하고 저장한다.

    CH1: gemini-3.1-flash-image-preview (멀티모달 레퍼런스 입력)
    CH2~7: Imagen 4.0 (텍스트 전용)
    """
    cfg = CHANNELS[ch_id]
    prompt = cfg["character_prompts"][pose_key]
    out_path = CHANNELS_DIR / ch_id / "characters" / f"character_{pose_key}.png"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    # CH1 전용: Gemini 멀티모달 (레퍼런스 이미지 입력으로 두들 스타일 전이)
    if ch_id == "CH1":
        reference = KAS_ROOT / "essential_branding" / "CH1.png"
        ok = generate_with_reference(reference, prompt, out_path)
        time.sleep(1.5)
        return ok

    # CH2~7: Imagen 4.0 (기존 경로 유지)
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


def generate_ch1_characters(client: genai.Client) -> dict[str, bool]:
    """CH1 캐릭터 4종을 gemini-3.1-flash-image-preview 멀티모달로 생성한다.

    Returns:
        {pose_key: True/False} — 생성 성공 여부
    """
    from nano_banana_helper import generate_with_reference

    cfg = CHANNELS["CH1"]
    reference = KAS_ROOT / "essential_branding" / "CH1.png"
    results: dict[str, bool] = {}

    for pose in cfg["characters"]:
        prompt = cfg["character_prompts"][pose]
        out_path = CHANNELS_DIR / "CH1" / "characters" / f"character_{pose}.png"
        out_path.parent.mkdir(parents=True, exist_ok=True)

        logger.info(f"[CH1/{pose}] 생성 중...")
        ok = generate_with_reference(reference, prompt, out_path)
        results[pose] = ok
        logger.info(f"[CH1/{pose}] {'완료' if ok else '실패'}")
        time.sleep(1.5)

    return results


def run_all(channels: list[str] | None = None) -> None:
    """모든 채널 또는 지정 채널의 캐릭터 PNG를 순차 생성한다.

    CH1은 Best-of-3 variant 경로, CH2~7은 표준 단일 생성 경로.
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        logger.error("GEMINI_API_KEY 환경변수가 없습니다.")
        sys.exit(1)

    client = genai.Client(api_key=api_key)
    logger.info(f"Gemini Imagen API 준비 완료 (모델: {MODEL})")

    target = channels or list(CHANNELS.keys())
    total = 0
    success = 0
    failures: list[str] = []

    for ch_id in target:
        cfg = CHANNELS[ch_id]
        logger.info(f"\n[{ch_id}] {cfg['name']} ({cfg['domain']}) 캐릭터 생성 시작...")

        if ch_id == "CH1":
            # CH1 전용: Gemini 멀티모달 (레퍼런스 이미지 스타일 전이)
            ch1_results = generate_ch1_characters(client)
            for pose, ok in ch1_results.items():
                total += 1
                if ok:
                    success += 1
                else:
                    failures.append(f"CH1/{pose}")
        else:
            # CH2~7: 표준 단일 생성
            for pose in cfg["characters"]:
                total += 1
                if generate_character(client, ch_id, pose):
                    success += 1
                else:
                    failures.append(f"{ch_id}/{pose}")

    logger.info(f"\n[완료] {success}/{total}개 캐릭터 PNG/variant 생성")
    if failures:
        logger.warning(f"[실패 목록] {failures}")
    else:
        logger.info("[실패 없음] 모든 포즈 생성 성공")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="채널 캐릭터 PNG 생성")
    parser.add_argument("--channel", default=None, help="단일 채널 ID (예: CH1)")
    args = parser.parse_args()
    channels = [args.channel] if args.channel else None
    run_all(channels)
