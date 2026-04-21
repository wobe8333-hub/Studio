"""QC Layer 4 — 영상 무결성 검증 (프레임 드롭·해상도·코덱·FPS)"""
from __future__ import annotations

import subprocess
from pathlib import Path

from loguru import logger

from src.pipeline_v2.episode_schema import EpisodeMeta

TARGET_WIDTH = 1920
TARGET_HEIGHT = 1080
TARGET_FPS = 30
MAX_FRAME_DROP_COUNT = 5
ALLOWED_VIDEO_CODECS = {"h264", "hevc", "vp9"}
ALLOWED_AUDIO_CODECS = {"aac", "mp3", "opus"}


def _probe_video(video_path: str) -> dict:
    """FFprobe로 영상 스트림 정보 추출."""
    cmd = [
        "ffprobe", "-v", "quiet",
        "-print_format", "json",
        "-show_streams",
        "-show_format",
        video_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if result.returncode != 0:
        return {}

    import json
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return {}


def _count_frame_drops(video_path: str) -> int:
    """FFmpeg으로 프레임 드롭 감지 (pts_time 비연속 카운트)."""
    cmd = [
        "ffprobe", "-v", "quiet",
        "-select_streams", "v",
        "-show_entries", "packet=pts_time",
        "-of", "csv=p=0",
        video_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    pts_times = []
    for line in result.stdout.splitlines():
        try:
            pts_times.append(float(line.strip()))
        except ValueError:
            continue

    if len(pts_times) < 2:
        return 0

    drop_count = 0
    for i in range(1, len(pts_times)):
        gap = pts_times[i] - pts_times[i - 1]
        if gap > (1.0 / TARGET_FPS) * 2.5:
            drop_count += 1

    return drop_count


def run_layer4(meta: EpisodeMeta, video_path: str) -> dict:
    """QC Layer 4: 영상 무결성 전체 검증.

    Returns: {"passed": bool, "width": int, "height": int, "fps": float,
              "video_codec": str, "audio_codec": str, "frame_drops": int, "issues": [str]}
    """
    if not Path(video_path).exists():
        return {"passed": False, "issues": ["영상 파일 없음"]}

    issues: list[str] = []
    probe = _probe_video(video_path)

    video_stream = next(
        (s for s in probe.get("streams", []) if s.get("codec_type") == "video"), {}
    )
    audio_stream = next(
        (s for s in probe.get("streams", []) if s.get("codec_type") == "audio"), {}
    )

    width = int(video_stream.get("width", 0))
    height = int(video_stream.get("height", 0))
    video_codec = video_stream.get("codec_name", "unknown").lower()

    fps_str = video_stream.get("r_frame_rate", "0/1")
    try:
        num, den = fps_str.split("/")
        fps = float(num) / max(float(den), 1)
    except (ValueError, ZeroDivisionError):
        fps = 0.0

    audio_codec = audio_stream.get("codec_name", "unknown").lower()

    if width != TARGET_WIDTH or height != TARGET_HEIGHT:
        issues.append(f"해상도 불일치: {width}×{height} (목표 {TARGET_WIDTH}×{TARGET_HEIGHT})")

    if video_codec not in ALLOWED_VIDEO_CODECS:
        issues.append(f"비디오 코덱 비허용: {video_codec}")

    if audio_codec not in ALLOWED_AUDIO_CODECS:
        issues.append(f"오디오 코덱 비허용: {audio_codec}")

    if abs(fps - TARGET_FPS) > 2.0:
        issues.append(f"FPS 이탈: {fps:.1f} (목표 {TARGET_FPS}±2)")

    frame_drops = _count_frame_drops(video_path)
    if frame_drops > MAX_FRAME_DROP_COUNT:
        issues.append(f"프레임 드롭 과다: {frame_drops}건 (한계 {MAX_FRAME_DROP_COUNT})")

    meta.features.video_frame_drop_count = frame_drops

    passed = len(issues) == 0
    result = {
        "passed": passed,
        "width": width,
        "height": height,
        "fps": round(fps, 2),
        "video_codec": video_codec,
        "audio_codec": audio_codec,
        "frame_drops": frame_drops,
        "issues": issues,
    }
    logger.info(f"QC Layer4: passed={passed} {width}×{height} {fps:.1f}fps {video_codec} drops={frame_drops}")
    return result
