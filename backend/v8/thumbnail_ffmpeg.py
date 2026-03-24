import os
import shutil
import subprocess
from pathlib import Path
from typing import Dict, Any, List

from backend.v8 import V8FFmpegNotFound, V8ThumbnailPolicyError


def _find_ffmpeg() -> str:
    env_path = os.getenv("FFMPEG_PATH")
    if env_path:
        exe = Path(env_path)
        if exe.exists():
            return str(exe)
    found = shutil.which("ffmpeg")
    if found:
        return found
    raise V8FFmpegNotFound("ffmpeg not found for thumbnail generation")


def _choose_font(candidates: List[str]) -> str | None:
    for p in candidates:
        if os.path.exists(p):
            return p
    return None


def _escape_drawtext_text(text: str) -> str:
    # drawtext에서 문제가 될 수 있는 일부 문자 이스케이프
    t = text.replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'")
    t = t.replace("\n", " ")
    return t


def build_thumbnail(
    base_image: Path,
    title_text: str,
    channel_config: Dict[str, Any],
    output_path: Path,
) -> None:
    """
    FFmpeg-only 썸네일 생성 (1280x720, scale cover + crop).
    텍스트 오버레이는 channels.json 정책을 따른다.
    """
    if not base_image.is_file():
        raise FileNotFoundError(f"thumbnail base image not found: {base_image}")

    ffmpeg = _find_ffmpeg()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    text_enabled = bool(channel_config.get("thumbnail_text_enabled"))
    policy = str(channel_config.get("thumbnail_text_policy") or "skip").lower()
    font_candidates = list(channel_config.get("thumbnail_font_candidates") or [])

    base_filter = "scale=1280:720:force_original_aspect_ratio=increase,crop=1280:720"

    def run_ffmpeg(filter_str: str) -> subprocess.CompletedProcess:
        cmd = [
            ffmpeg,
            "-y",
            "-i",
            str(base_image),
            "-vf",
            filter_str,
            "-frames:v",
            "1",
            str(output_path),
        ]
        return subprocess.run(cmd, capture_output=True, text=True)

    if not text_enabled:
        result = run_ffmpeg(base_filter)
        if result.returncode != 0:
            raise RuntimeError(f"ffmpeg thumbnail without text failed: {result.stderr[:500]}")
        return

    font_path = _choose_font(font_candidates)
    if font_path is None:
        if policy == "fail":
            raise V8ThumbnailPolicyError("no thumbnail font found and policy='fail'")
        # policy=skip → 텍스트 없이 생성
        result = run_ffmpeg(base_filter)
        if result.returncode != 0:
            raise RuntimeError(f"ffmpeg thumbnail without text failed: {result.stderr[:500]}")
        return

    safe_text = _escape_drawtext_text(title_text)
    drawtext_filter = (
        f"{base_filter},"
        f"drawtext=fontfile='{font_path}':text='{safe_text}':"
        f"fontcolor=white:fontsize=48:box=1:boxcolor=black@0.6:boxborderw=20:"
        f"x=(w-text_w)/2:y=h-text_h-40"
    )

    # 1차: drawtext 포함 시도
    result = run_ffmpeg(drawtext_filter)
    if result.returncode == 0:
        return

    # drawtext 실패
    if policy == "fail":
        raise V8ThumbnailPolicyError(
            f"ffmpeg drawtext failed with policy='fail': {result.stderr[:500]}"
        )

    # policy=skip → 텍스트 없이 재시도
    fallback = run_ffmpeg(base_filter)
    if fallback.returncode != 0:
        raise RuntimeError(f"ffmpeg thumbnail fallback without text failed: {fallback.stderr[:500]}")

