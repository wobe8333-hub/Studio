# scripts/generate_branding/setup_folders.py
"""assets/channels/ 폴더 구조 일괄 생성"""
import sys
import io
from pathlib import Path
from loguru import logger

sys.path.insert(0, str(Path(__file__).parent))
from config import CHANNELS, CHANNELS_DIR, SUBDIRS


def create_folder_structure():
    for ch_id in CHANNELS:
        for subdir in SUBDIRS:
            path = CHANNELS_DIR / ch_id / subdir
            path.mkdir(parents=True, exist_ok=True)
            logger.info(f"  created: {path}")
    logger.info(f"\n[완료] {len(CHANNELS) * len(SUBDIRS)}개 폴더 생성")


if __name__ == "__main__":
    if hasattr(sys.stdout, "buffer"):
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    create_folder_structure()
