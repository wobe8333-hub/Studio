"""쇼츠 자동 파생 — 감정 피크 + 엔그램 밀도 탐지 → 30~60초 구간 클리핑"""
from __future__ import annotations

import subprocess
from pathlib import Path

from loguru import logger

from src.pipeline_v2.episode_schema import EpisodeMeta

SHORTS_ROOT = Path("runs/pipeline_v2")
MIN_CLIP_SEC = 30
MAX_CLIP_SEC = 60
MAX_CLIPS = 5
TARGET_RESOLUTION = "1080x1920"  # 세로형 9:16


def _probe_keyframes(video_path: str) -> list[float]:
    """FFprobe로 감정 피크 후보 타임스탬프 추출 (I-frame 기준)."""
    cmd = [
        "ffprobe", "-v", "quiet",
        "-select_streams", "v",
        "-show_entries", "packet=pts_time,flags",
        "-of", "csv=p=0",
        video_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    timestamps = []
    for line in result.stdout.splitlines():
        parts = line.split(",")
        if len(parts) >= 2 and "K" in parts[1]:
            try:
                timestamps.append(float(parts[0]))
            except ValueError:
                pass
    return timestamps


def _select_peak_segments(
    timestamps: list[float],
    total_duration: float,
    emotion_peaks: list[int],
) -> list[tuple[float, float]]:
    """감정 피크 타임스탬프 기준으로 클립 구간 선택.

    Returns: [(start_sec, end_sec), ...]
    """
    if not emotion_peaks:
        # 피크 데이터 없으면 균등 분할
        step = total_duration / (MAX_CLIPS + 1)
        return [(i * step, min(i * step + MAX_CLIP_SEC, total_duration)) for i in range(1, MAX_CLIPS + 1)]

    segments = []
    for peak in emotion_peaks[:MAX_CLIPS]:
        start = max(0, peak - MIN_CLIP_SEC // 3)
        end = min(total_duration, start + MAX_CLIP_SEC)
        if end - start >= MIN_CLIP_SEC:
            segments.append((start, end))

    return segments[:MAX_CLIPS]


def _clip_segment(
    video_path: str,
    start: float,
    end: float,
    output_path: Path,
    episode_id: str,
) -> Path | None:
    """FFmpeg로 세그먼트 클리핑 + 세로 크롭 (9:16)."""
    duration = end - start
    cmd = [
        "ffmpeg", "-y",
        "-i", video_path,
        "-ss", str(start), "-t", str(duration),
        # 16:9 → 9:16 센터 크롭
        "-vf", "crop=ih*9/16:ih:(iw-ih*9/16)/2:0,scale=1080:1920",
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        "-c:a", "aac", "-b:a", "128k",
        str(output_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        logger.warning(f"클립 생성 실패 ({start:.0f}~{end:.0f}s): {result.stderr[-200:]}")
        return None
    return output_path


def derive_shorts(meta: EpisodeMeta, video_path: str | None = None) -> list[str]:
    """롱폼 영상에서 쇼츠 3~5개 자동 파생.

    Returns: 생성된 쇼츠 파일 경로 목록
    """
    if not video_path:
        video_path = meta.video_path
    if not video_path or not Path(video_path).exists():
        logger.warning(f"롱폼 영상 없음: {video_path}")
        return []

    out_dir = SHORTS_ROOT / meta.episode_id / "shorts"
    out_dir.mkdir(parents=True, exist_ok=True)

    total_duration = float(meta.features.duration_sec or 0)
    if total_duration < MIN_CLIP_SEC:
        logger.warning(f"영상이 너무 짧음 ({total_duration}s), 쇼츠 파생 스킵")
        return []

    keyframes = _probe_keyframes(video_path)
    emotion_peaks = meta.features.emotion_peaks

    segments = _select_peak_segments(keyframes, total_duration, emotion_peaks)
    logger.info(f"쇼츠 파생 시작: {meta.episode_id} — {len(segments)}개 구간 탐지")

    shorts_paths: list[str] = []
    for i, (start, end) in enumerate(segments, 1):
        out_path = out_dir / f"shorts_{i:02d}_{int(start)}s.mp4"
        result = _clip_segment(video_path, start, end, out_path, meta.episode_id)
        if result:
            shorts_paths.append(str(result))
            logger.info(f"쇼츠 #{i} 생성: {out_path.name} ({end - start:.0f}s)")

    meta.features.shorts_derived_count = len(shorts_paths)
    logger.info(f"쇼츠 파생 완료: {len(shorts_paths)}/{len(segments)}")
    return shorts_paths
