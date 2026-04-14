"""
reference_cropper.py
────────────────────
essential_branding/CH1.png 레퍼런스 이미지에서 요소를 bbox 기반으로 crop한 뒤
PIL 배경제거 + LANCZOS 업스케일을 적용하여 assets/channels/CH1/ 하위에 저장.

rembg(onnxruntime) 없이 PIL 기반 흰색/밝은 배경 알파 제거 사용.
"""
from __future__ import annotations
from pathlib import Path
import numpy as np
from PIL import Image
from loguru import logger

from scripts.generate_branding.config import CH1_CROP_REGIONS, CH1_POST_POLICY

REFERENCE_ROOT = Path("essential_branding")

_CH1_OUTPUT_MAP: dict[str, str] = {
    "logo":                "logo/logo.png",
    "character_explain":   "characters/character_explain.png",
    "character_rich":      "characters/character_rich.png",
    "character_money":     "characters/character_money.png",
    "character_lucky":     "characters/character_lucky.png",
    "intro_frame":         "intro/intro_frame.png",
    "intro_text":          "intro/intro_text.png",
    "intro_character":     "intro/intro_character.png",
    "intro_sparkle":       "intro/intro_sparkle.png",
    "outro_background":    "outro/outro_background.png",
    "outro_bill":          "outro/outro_bill.png",
    "outro_character":     "outro/outro_character.png",
    "outro_cta":           "outro/outro_cta.png",
    "thumbnail_sample_1":  "templates/thumbnail_sample_1.png",
    "thumbnail_sample_2":  "templates/thumbnail_sample_2.png",
    "thumbnail_sample_3":  "templates/thumbnail_sample_3.png",
    "subtitle_bar_key":    "templates/subtitle_bar_key.png",
    "subtitle_bar_dialog": "templates/subtitle_bar_dialog.png",
    "subtitle_bar_info":   "templates/subtitle_bar_info.png",
    "transition_paper":    "templates/transition_paper.png",
    "transition_ink":      "templates/transition_ink.png",
    "transition_zoom":     "templates/transition_zoom.png",
}


def _remove_light_bg(img: Image.Image, threshold: int = 230) -> Image.Image:
    """밝은(흰색/크림) 배경을 알파 채널로 제거.

    RGB 세 채널이 모두 threshold 이상인 픽셀을 투명화.
    레퍼런스 CH1.png의 배경이 흰색/크림색이므로 이 방식이 효과적.
    """
    rgba = img.convert("RGBA")
    arr = np.array(rgba, dtype=np.uint8)
    # R, G, B 모두 threshold 초과 → 배경 픽셀
    mask = (arr[:, :, 0] > threshold) & (arr[:, :, 1] > threshold) & (arr[:, :, 2] > threshold)
    arr[mask, 3] = 0  # 알파=0 (완전 투명)
    return Image.fromarray(arr, mode="RGBA")


def _resize_by_policy(img: Image.Image, policy: dict) -> Image.Image:
    """target(정확 크기) 또는 longer_side(긴 변 맞춤) 정책으로 LANCZOS 리사이즈."""
    if "target" in policy:
        tw, th = policy["target"]
        ratio = min(tw / img.width, th / img.height)
        nw, nh = max(1, int(img.width * ratio)), max(1, int(img.height * ratio))
        resized = img.resize((nw, nh), Image.Resampling.LANCZOS)
        # 투명 캔버스 (RGBA) 또는 흰색 캔버스 (RGB)
        if img.mode == "RGBA":
            canvas = Image.new("RGBA", (tw, th), (0, 0, 0, 0))
            canvas.paste(resized, ((tw - nw) // 2, (th - nh) // 2), resized)
        else:
            canvas = Image.new("RGB", (tw, th), (255, 255, 255))
            canvas.paste(resized, ((tw - nw) // 2, (th - nh) // 2))
        return canvas
    if "longer_side" in policy:
        side = policy["longer_side"]
        ratio = side / max(img.width, img.height)
        nw, nh = max(1, int(img.width * ratio)), max(1, int(img.height * ratio))
        return img.resize((nw, nh), Image.Resampling.LANCZOS)
    return img


def _apply_pipeline(cropped: Image.Image, policy: dict) -> Image.Image:
    """crop 결과에 배경제거 → 리사이즈 파이프라인 적용."""
    if policy.get("bg_remove"):
        img = _remove_light_bg(cropped)          # RGBA, 배경 투명
    else:
        img = cropped.convert("RGB")             # 배경 유지
    return _resize_by_policy(img, policy)


def crop_channel(channel: str, out_dir: Path) -> None:
    """레퍼런스 이미지에서 요소를 crop하여 out_dir에 저장.

    Args:
        channel: "CH1" (현재 CH1만 지원)
        out_dir: 출력 루트 디렉토리 (예: Path("assets/channels/CH1"))
    """
    if channel != "CH1":
        raise NotImplementedError(
            f"{channel} crop 미구현 — CH1 승인 후 확장 예정"
        )
    src_path = REFERENCE_ROOT / "CH1.png"
    if not src_path.exists():
        raise FileNotFoundError(f"레퍼런스 이미지 없음: {src_path}")

    base = Image.open(src_path).convert("RGBA")
    logger.info(f"레퍼런스 로드: {src_path} ({base.size})")

    for name, bbox in CH1_CROP_REGIONS.items():
        rel_path = _CH1_OUTPUT_MAP[name]
        policy = CH1_POST_POLICY[name]
        target = out_dir / rel_path
        target.parent.mkdir(parents=True, exist_ok=True)

        cropped = base.crop(bbox)
        processed = _apply_pipeline(cropped, policy)
        processed.save(target, format="PNG")
        logger.info(f"  {name}: {bbox} → {target} ({processed.size}, {processed.mode})")

    logger.info(f"CH1 crop 완료: {len(CH1_CROP_REGIONS)}개 파일 → {out_dir}")


if __name__ == "__main__":
    import sys, io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    crop_channel("CH1", Path("assets/channels/CH1"))
