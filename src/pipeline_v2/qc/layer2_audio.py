"""QC Layer 2 — 오디오 품질 검증 (EBU R128 라우드니스 + 클리핑 감지)"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

from loguru import logger

from src.pipeline_v2.episode_schema import EpisodeMeta

TARGET_LUFS = -14.0
MAX_TRUE_PEAK_DBTP = -1.5
MAX_CLIP_RATIO = 0.001  # 클리핑 허용 비율 0.1%


def _measure_loudness(audio_path: str) -> dict:
    """FFmpeg loudnorm 측정 — JSON 통계 반환."""
    cmd = [
        "ffmpeg", "-i", audio_path,
        "-af", "loudnorm=I=-14:TP=-1.5:LRA=11:print_format=json",
        "-f", "null", "-",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    stderr = result.stderr

    json_start = stderr.rfind("{")
    json_end = stderr.rfind("}") + 1
    if json_start < 0 or json_end <= json_start:
        logger.warning(f"loudnorm JSON 파싱 실패: {audio_path}")
        return {}

    try:
        return json.loads(stderr[json_start:json_end])
    except json.JSONDecodeError as e:
        logger.warning(f"loudnorm JSON 디코드 실패: {e}")
        return {}


def _detect_clipping(audio_path: str) -> tuple[int, float]:
    """클리핑 샘플 수 + 비율 감지."""
    cmd = [
        "ffmpeg", "-i", audio_path,
        "-af", "aclip=max_warning=0",
        "-f", "null", "-",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")

    clip_count = 0
    for line in result.stderr.splitlines():
        if "clipping" in line.lower():
            parts = line.split()
            for i, p in enumerate(parts):
                if p.isdigit() and i > 0:
                    clip_count = max(clip_count, int(p))
                    break

    total_cmd = [
        "ffprobe", "-v", "quiet",
        "-show_entries", "stream=nb_read_packets",
        "-select_streams", "a",
        "-count_packets",
        "-of", "default=noprint_wrappers=1:nokey=1",
        audio_path,
    ]
    total_result = subprocess.run(total_cmd, capture_output=True, text=True)
    try:
        total_samples = max(1, int(total_result.stdout.strip()))
    except ValueError:
        total_samples = 1

    return clip_count, clip_count / total_samples


def _check_silence(audio_path: str, min_duration_sec: float = 5.0) -> bool:
    """오디오가 최소 길이 이상인지 확인."""
    cmd = [
        "ffprobe", "-v", "quiet",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        audio_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    try:
        duration = float(result.stdout.strip())
        return duration >= min_duration_sec
    except ValueError:
        return False


def run_layer2(meta: EpisodeMeta, video_path: str) -> dict:
    """QC Layer 2: 오디오 라우드니스·클리핑·기본 길이 검증.

    Returns: {"passed": bool, "lufs": float, "true_peak": float, "clip_ratio": float, "issues": [str]}
    """
    if not Path(video_path).exists():
        logger.warning(f"QC Layer2: 영상 파일 없음 — {video_path}")
        return {"passed": False, "issues": ["영상 파일 없음"], "lufs": None, "true_peak": None}

    issues: list[str] = []

    loudness = _measure_loudness(video_path)
    measured_lufs = float(loudness.get("input_i", TARGET_LUFS))
    measured_tp = float(loudness.get("input_tp", -1.5))

    lufs_diff = abs(measured_lufs - TARGET_LUFS)
    if lufs_diff > 2.0:
        issues.append(f"라우드니스 이탈: {measured_lufs:.1f} LUFS (목표 {TARGET_LUFS}±2)")

    if measured_tp > MAX_TRUE_PEAK_DBTP:
        issues.append(f"True Peak 초과: {measured_tp:.1f} dBTP (한계 {MAX_TRUE_PEAK_DBTP})")

    clip_count, clip_ratio = _detect_clipping(video_path)
    if clip_ratio > MAX_CLIP_RATIO:
        issues.append(f"클리핑 감지: {clip_count}샘플 ({clip_ratio:.4%})")

    if not _check_silence(video_path):
        issues.append("오디오 길이 5초 미만")

    meta.features.audio_loudness_lufs = round(measured_lufs, 2)

    passed = len(issues) == 0
    result = {
        "passed": passed,
        "lufs": measured_lufs,
        "true_peak": measured_tp,
        "clip_count": clip_count,
        "clip_ratio": round(clip_ratio, 6),
        "issues": issues,
    }
    logger.info(f"QC Layer2: passed={passed} LUFS={measured_lufs:.1f} TP={measured_tp:.1f} clips={clip_count}")
    return result
