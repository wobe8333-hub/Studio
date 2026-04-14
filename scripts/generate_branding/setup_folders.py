# scripts/generate_branding/setup_folders.py
"""assets/channels/ 폴더 구조 일괄 생성"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from config import CHANNELS, CHANNELS_DIR, SUBDIRS

def create_folder_structure():
    for ch_id in CHANNELS:
        for subdir in SUBDIRS:
            path = CHANNELS_DIR / ch_id / subdir
            path.mkdir(parents=True, exist_ok=True)
            print(f"  created: {path}")
    print(f"\n[완료] {len(CHANNELS) * len(SUBDIRS)}개 폴더 생성")

if __name__ == "__main__":
    create_folder_structure()
