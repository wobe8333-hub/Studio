"""Step Final — 인트로 + 본편 + 아웃트로 FFmpeg 합성.

승인된 영상에 채널 인트로(3초)와 아웃트로(10초)를 붙여 최종 영상을 생성한다.

인트로: assets/channels/{CH}/intro/intro_frame.png → 3초 정지 클립
아웃트로: assets/channels/{CH}/outro/outro_background.png + outro_bill.png → 10초 클립

추후 Playwright로 HTML 애니메이션을 MP4로 렌더링하도록 업그레이드 가능.
"""

import subprocess
from pathlib import Path

from loguru import logger

from src.core.config import KAS_ROOT
from src.core.ssot import get_run_dir, now_iso, sha256_file, write_json

# 인트로/아웃트로 길이 (초)
INTRO_DURATION_SEC = 3
OUTRO_DURATION_SEC = 10


def _png_to_clip(png_path: Path, duration: int, output_path: Path) -> bool:
    """단일 PNG → 지정 길이의 MP4 클립 생성 (FFmpeg loop)."""
    if not png_path.exists():
        logger.warning(f"[FINAL] PNG 없음: {png_path}")
        return False
    cmd = [
        "ffmpeg", "-y",
        "-loop", "1",
        "-i", str(png_path),
        "-t", str(duration),
        "-vf", "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2",
        "-c:v", "libx264", "-crf", "22", "-preset", "medium",
        "-pix_fmt", "yuv420p",
        "-an",
        str(output_path),
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, timeout=60)
        if result.returncode != 0:
            logger.error(f"[FINAL] FFmpeg PNG→클립 실패: {result.stderr[-200:]}")
            return False
        return output_path.exists() and output_path.stat().st_size > 0
    except Exception as e:
        logger.error(f"[FINAL] PNG→클립 예외: {e}")
        return False


def _build_outro_composite(channel_id: str, tmp_dir: Path) -> Path | None:
    """아웃트로: outro_background + outro_bill + outro_cta → 합성 PNG."""
    from PIL import Image

    asset_dir = KAS_ROOT / "assets" / "channels" / channel_id / "outro"
    bg_path   = asset_dir / "outro_background.png"
    bill_path = asset_dir / "outro_bill.png"
    cta_path  = asset_dir / "outro_cta.png"
    char_path = asset_dir / "outro_character.png"

    if not bg_path.exists():
        return None

    try:
        base = Image.open(bg_path).convert("RGBA").resize((1920, 1080))
        for overlay_path in [char_path, bill_path, cta_path]:
            if overlay_path.exists():
                ov = Image.open(overlay_path).convert("RGBA")
                ov = ov.resize((1920, 1080), Image.LANCZOS)
                base = Image.alpha_composite(base, ov)

        out_path = tmp_dir / "outro_composite.png"
        base.convert("RGB").save(out_path)
        return out_path
    except Exception as e:
        logger.warning(f"[FINAL] 아웃트로 합성 실패 → 배경만 사용: {e}")
        return bg_path


def run_intro_outro(channel_id: str, run_id: str) -> Path | None:
    """인트로 + 본편 + 아웃트로를 합쳐 video_final.mp4 생성."""
    run_dir   = get_run_dir(channel_id, run_id)
    step08_dir = run_dir / "step08"
    asset_dir  = KAS_ROOT / "assets" / "channels" / channel_id

    # 본편 영상 (우선순위: video_narr.mp4 > video.mp4)
    main_video = step08_dir / "video_narr.mp4"
    if not main_video.exists():
        main_video = step08_dir / "video.mp4"
    if not main_video.exists():
        logger.error(f"[FINAL] 본편 영상 없음: {step08_dir}")
        return None

    tmp_dir    = run_dir / "_final_tmp"
    tmp_dir.mkdir(parents=True, exist_ok=True)
    final_dir  = run_dir / "step_final"
    final_dir.mkdir(parents=True, exist_ok=True)

    # ── 인트로 클립 ────────────────────────────────────────────────
    intro_png  = asset_dir / "intro" / "intro_frame.png"
    intro_clip = tmp_dir / "intro.mp4"
    has_intro  = _png_to_clip(intro_png, INTRO_DURATION_SEC, intro_clip)

    # ── 아웃트로 클립 ───────────────────────────────────────────────
    outro_png  = _build_outro_composite(channel_id, tmp_dir)
    outro_clip = tmp_dir / "outro.mp4"
    has_outro  = _png_to_clip(outro_png, OUTRO_DURATION_SEC, outro_clip) if outro_png else False

    # ── concat 목록 작성 ────────────────────────────────────────────
    concat_list = tmp_dir / "concat_list.txt"
    clips = []
    if has_intro:
        clips.append(intro_clip)
    clips.append(main_video)
    if has_outro:
        clips.append(outro_clip)

    with open(concat_list, "w", encoding="utf-8") as f:
        for clip in clips:
            f.write(f"file '{clip.as_posix()}'\n")

    # ── FFmpeg concat ───────────────────────────────────────────────
    final_path = final_dir / "video_final.mp4"
    cmd = [
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0",
        "-i", str(concat_list),
        "-c:v", "libx264", "-crf", "22", "-preset", "medium",
        "-c:a", "aac", "-b:a", "192k",
        str(final_path),
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, timeout=300)
        if result.returncode != 0:
            logger.error(f"[FINAL] FFmpeg concat 실패: {result.stderr[-300:]}")
            return None
    except Exception as e:
        logger.error(f"[FINAL] concat 예외: {e}")
        return None

    if not final_path.exists() or final_path.stat().st_size == 0:
        logger.error("[FINAL] video_final.mp4 생성 실패")
        return None

    # ── 메타데이터 기록 ─────────────────────────────────────────────
    size_mb = final_path.stat().st_size / 1_048_576
    report = {
        "channel_id": channel_id,
        "run_id":     run_id,
        "final_path": str(final_path),
        "size_mb":    round(size_mb, 2),
        "intro_used": has_intro,
        "outro_used": has_outro,
        "sha256":     sha256_file(final_path),
        "created_at": now_iso(),
    }
    write_json(final_dir / "final_report.json", report)

    logger.info(
        f"[FINAL] {channel_id}/{run_id} 최종 영상 완성 ✅\n"
        f"        인트로={has_intro} / 아웃트로={has_outro} / {size_mb:.1f}MB\n"
        f"        → {final_path}"
    )
    return final_path
