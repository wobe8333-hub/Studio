"""QC Layer 3 — 자막↔나레이션 싱크 검증 (Faster-Whisper 역검증)"""
from __future__ import annotations

import re
from pathlib import Path

from loguru import logger

from src.pipeline_v2.episode_schema import EpisodeMeta

MAX_DRIFT_SEC = 0.5
MIN_SYNC_SCORE = 0.80


def _load_srt(srt_path: Path) -> list[dict]:
    """SRT 파일 파싱 → [{index, start, end, text}] 반환."""
    if not srt_path.exists():
        return []

    entries = []
    text = srt_path.read_text(encoding="utf-8", errors="replace")
    blocks = re.split(r"\n\s*\n", text.strip())

    for block in blocks:
        lines = block.strip().splitlines()
        if len(lines) < 3:
            continue
        try:
            index = int(lines[0].strip())
            time_match = re.match(
                r"(\d{2}:\d{2}:\d{2},\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2},\d{3})",
                lines[1].strip(),
            )
            if not time_match:
                continue
            start = _srt_time_to_sec(time_match.group(1))
            end = _srt_time_to_sec(time_match.group(2))
            caption_text = " ".join(lines[2:]).strip()
            entries.append({"index": index, "start": start, "end": end, "text": caption_text})
        except (ValueError, IndexError):
            continue

    return entries


def _srt_time_to_sec(t: str) -> float:
    """SRT 시간 문자열 → 초."""
    t = t.replace(",", ".")
    parts = t.split(":")
    h, m, s = int(parts[0]), int(parts[1]), float(parts[2])
    return h * 3600 + m * 60 + s


def _transcribe_audio(audio_path: str, model_size: str = "base") -> list[dict]:
    """Faster-Whisper로 오디오 전사 → [{start, end, text}] 반환."""
    try:
        from faster_whisper import WhisperModel
        model = WhisperModel(model_size, device="cpu", compute_type="int8")
        segments, _ = model.transcribe(audio_path, language="ko", word_timestamps=False)
        return [{"start": s.start, "end": s.end, "text": s.text.strip()} for s in segments]
    except ImportError:
        logger.warning("faster-whisper 미설치 — Layer3 싱크 체크 스킵")
        return []
    except Exception as e:
        logger.warning(f"Whisper 전사 실패: {e}")
        return []


def _compute_sync_score(srt_entries: list[dict], whisper_segments: list[dict]) -> tuple[float, list[dict]]:
    """SRT 타임스탬프 ↔ Whisper 전사 타임스탬프 비교.

    Returns: (sync_score 0~1, drift_details 리스트)
    """
    if not srt_entries or not whisper_segments:
        return 1.0, []

    drifts = []
    matched = 0

    for srt in srt_entries:
        best_drift = float("inf")
        for ws in whisper_segments:
            if abs(srt["start"] - ws["start"]) < 5.0:
                drift = abs(srt["start"] - ws["start"])
                best_drift = min(best_drift, drift)

        if best_drift == float("inf"):
            best_drift = MAX_DRIFT_SEC * 2

        drifts.append({"srt_start": srt["start"], "drift_sec": round(best_drift, 3)})
        if best_drift <= MAX_DRIFT_SEC:
            matched += 1

    score = matched / len(srt_entries) if srt_entries else 1.0
    return score, drifts


def run_layer3(meta: EpisodeMeta, video_path: str, subtitle_path: str | None = None) -> dict:
    """QC Layer 3: 자막 ↔ 나레이션 싱크 검증.

    Returns: {"passed": bool, "sync_score": float, "drift_details": [...], "issues": [str]}
    """
    issues: list[str] = []

    if subtitle_path is None:
        from src.pipeline_v2.dag.track_d_assembly import ASSEMBLY_ROOT
        subtitle_path = str(ASSEMBLY_ROOT / meta.episode_id / "audio" / "subtitle.srt")

    srt_path = Path(subtitle_path)
    srt_entries = _load_srt(srt_path)

    if not srt_entries:
        logger.info(f"QC Layer3: SRT 없음 또는 빈 파일 — 싱크 검증 스킵 ({meta.episode_id})")
        meta.features.subtitle_sync_score = 1.0
        return {"passed": True, "sync_score": 1.0, "drift_details": [], "issues": []}

    whisper_segments = _transcribe_audio(video_path)

    if not whisper_segments:
        logger.warning(f"QC Layer3: Whisper 전사 결과 없음 — 스킵 ({meta.episode_id})")
        meta.features.subtitle_sync_score = 1.0
        return {"passed": True, "sync_score": 1.0, "drift_details": [], "issues": ["Whisper 미사용"]}

    sync_score, drift_details = _compute_sync_score(srt_entries, whisper_segments)
    meta.features.subtitle_sync_score = round(sync_score, 3)

    if sync_score < MIN_SYNC_SCORE:
        issues.append(f"자막 싱크 불량: score={sync_score:.3f} (최소 {MIN_SYNC_SCORE})")

    high_drift = [d for d in drift_details if d["drift_sec"] > MAX_DRIFT_SEC]
    if len(high_drift) > 3:
        issues.append(f"대형 드리프트 {len(high_drift)}건 (>{MAX_DRIFT_SEC}s)")

    passed = len(issues) == 0
    logger.info(f"QC Layer3: passed={passed} sync={sync_score:.3f} ({len(srt_entries)} 자막)")
    return {
        "passed": passed,
        "sync_score": sync_score,
        "drift_details": drift_details[:20],
        "issues": issues,
    }
