"""채널 로고를 우상단 워터마크 크기(128×128, 투명 배경)로 변환.

thumbnail_generator.py 가 L2 레이어로 우상단에 합성하는 자산을 생성한다.
AI 호출 없음 — PIL 단순 리사이즈만 사용.

실행:
    python scripts/generate_branding/gen_watermarks.py
"""
import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
CHANNELS_DIR = ROOT / "assets" / "channels"
CHANNELS = [f"CH{i}" for i in range(1, 8)]
WATERMARK_SIZE = (128, 128)


def generate_watermark(ch: str) -> bool:
    logo_path = CHANNELS_DIR / ch / "logo" / "logo.png"
    out_path = CHANNELS_DIR / ch / "badges" / "logo_watermark.png"

    if not logo_path.exists():
        print(f"[SKIP] {ch}: 로고 없음 ({logo_path})")
        return False

    out_path.parent.mkdir(parents=True, exist_ok=True)
    img = Image.open(logo_path).convert("RGBA")
    img = img.resize(WATERMARK_SIZE, Image.LANCZOS)
    img.save(str(out_path))
    print(f"[OK] {ch}: {out_path.name} ({WATERMARK_SIZE[0]}×{WATERMARK_SIZE[1]}px)")
    return True


if __name__ == "__main__":
    success = 0
    for ch in CHANNELS:
        if generate_watermark(ch):
            success += 1
    print(f"\n완료: {success}/{len(CHANNELS)}채널 워터마크 생성")
    sys.exit(0 if success > 0 else 1)
