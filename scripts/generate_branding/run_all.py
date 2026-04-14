# scripts/generate_branding/run_all.py
"""7채널 브랜딩 에셋 전체 생성 파이프라인 오케스트레이터"""
import sys
import io

from pathlib import Path
from loguru import logger

sys.path.insert(0, str(Path(__file__).parent))
from config import CHANNELS
from setup_folders import create_folder_structure
from logo_gen import generate_logo
from intro_gen import generate_intro
from outro_gen import generate_outro
from icon_gen import generate_icons
from template_gen import generate_templates
from extras_gen import generate_extras


STEPS = [
    ("폴더 구조 생성", None, create_folder_structure, False),
    ("로고 SVG", "logo", generate_logo, True),
    ("인트로 HTML", "intro", generate_intro, True),
    ("아웃트로 HTML", "outro", generate_outro, True),
    ("아이콘 SVG", "icons", generate_icons, True),
    ("템플릿 SVG", "templates", generate_templates, True),
    ("채널 아트·배너", "extras", generate_extras, True),
]


def run_all(skip_characters: bool = True) -> None:
    logger.info("=" * 60)
    logger.info("7채널 브랜딩 에셋 전체 생성 시작")
    logger.info("=" * 60)

    for step_name, _, fn, per_channel in STEPS:
        logger.info(f"\n[STEP] {step_name}")
        if per_channel:
            for ch_id in CHANNELS:
                fn(ch_id)
        else:
            fn()

    logger.info("\n" + "=" * 60)
    logger.info("[완료] 전체 파이프라인 완료")
    if skip_characters:
        logger.info("캐릭터 PNG는 별도 실행: python scripts/generate_branding/character_gen.py")
    logger.info("=" * 60)


if __name__ == "__main__":
    run_all()
