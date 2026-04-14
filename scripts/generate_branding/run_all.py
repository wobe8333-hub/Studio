# scripts/generate_branding/run_all.py
"""7채널 브랜딩 에셋 전체 생성 파이프라인 오케스트레이터

Usage:
    python -m scripts.generate_branding.run_all              # 전체 7채널
    python -m scripts.generate_branding.run_all --channel CH1  # CH1만
"""
import sys
import io
import argparse

from pathlib import Path
from loguru import logger

sys.path.insert(0, str(Path(__file__).parent))
from config import CHANNELS, CHANNELS_DIR
from setup_folders import create_folder_structure
from logo_gen import generate_logo
from intro_gen import generate_intro
from outro_gen import generate_outro
from icon_gen import generate_icons
from template_gen import generate_templates
from extras_gen import generate_extras
from reference_cropper import crop_channel


STEPS = [
    ("폴더 구조 생성", None, create_folder_structure, False),
    ("로고 SVG", "logo", generate_logo, True),
    ("인트로 HTML", "intro", generate_intro, True),
    ("아웃트로 HTML", "outro", generate_outro, True),
    ("아이콘 SVG", "icons", generate_icons, True),
    ("템플릿 SVG", "templates", generate_templates, True),
    ("채널 아트·배너", "extras", generate_extras, True),
]


def _run_ch1() -> None:
    """CH1: 레퍼런스 crop → CSS 인트로/아웃트로 → 아이콘/엑스트라 SVG."""
    logger.info("=" * 60)
    logger.info("CH1 브랜딩 에셋 생성 (레퍼런스 crop 파이프라인)")
    logger.info("=" * 60)
    create_folder_structure()
    crop_channel("CH1", CHANNELS_DIR / "CH1")   # 22종 PNG 에셋
    generate_intro("CH1")                        # CSS keyframes 인트로 HTML
    generate_outro("CH1")                        # 지폐 20장 낙하 아웃트로 HTML
    generate_icons("CH1")                        # 아이콘 20종 SVG (레퍼런스에 없음)
    generate_extras("CH1")                       # 채널아트·배너 SVG
    logger.info("=" * 60)
    logger.info("[완료] CH1 파이프라인 완료")
    logger.info("=" * 60)


def run_all(channels: list[str] | None = None) -> None:
    """전체 또는 지정 채널 브랜딩 에셋 생성.

    Args:
        channels: None이면 전체 7채널. 리스트 지정 시 해당 채널만.
    """
    target = channels or list(CHANNELS)
    logger.info("=" * 60)
    logger.info(f"브랜딩 에셋 생성 시작: {', '.join(target)}")
    logger.info("=" * 60)

    for ch_id in target:
        if ch_id == "CH1":
            _run_ch1()
        else:
            # CH2~7: 기존 SVG 기반 파이프라인
            logger.info(f"\n[{ch_id}] SVG 파이프라인 시작")
            create_folder_structure()
            for step_name, _, fn, _ in STEPS[1:]:  # 폴더 생성 제외
                logger.info(f"  {step_name}")
                fn(ch_id)

    logger.info("\n" + "=" * 60)
    logger.info("[완료] 전체 파이프라인 완료")
    logger.info("캐릭터 PNG는 별도 실행: python scripts/generate_branding/character_gen.py")
    logger.info("=" * 60)


if __name__ == "__main__":
    if hasattr(sys.stdout, "buffer"):
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description="브랜딩 에셋 생성")
    parser.add_argument("--channel", default=None, help="단일 채널 ID (예: CH1)")
    args = parser.parse_args()
    channels = [args.channel] if args.channel else None
    run_all(channels)
