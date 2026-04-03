"""STEP 08 — 자막 생성기.

Phase 6 전환:
  1차 시도: Faster-Whisper로 word-level 타임스탬프 SRT 생성 (정확한 음성 동기화)
  폴백: pydub 기반 균등분배 SRT (Whisper 불가 시)
"""

from pathlib import Path
from loguru import logger


def _srt_timestamp(seconds: float) -> str:
    """초 → SRT 타임스탬프 포맷 변환"""
    total_ms = int(seconds * 1000)
    h = total_ms // 3_600_000
    m = (total_ms % 3_600_000) // 60_000
    s = (total_ms % 60_000) // 1_000
    ms = total_ms % 1_000
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def _generate_whisper_srt(narration_path: Path, output_path: Path) -> bool:
    """
    Faster-Whisper로 word-level 타임스탬프 SRT 생성.
    GPU 없어도 CPU 모드로 동작.
    """
    try:
        from faster_whisper import WhisperModel

        # tiny 또는 base 모델 (CPU용, 속도 우선)
        model = WhisperModel("base", device="cpu", compute_type="int8")
        segments, info = model.transcribe(
            str(narration_path),
            language="ko",
            word_timestamps=True,
        )

        srt_lines = []
        idx = 1
        current_words = []
        current_start = None
        current_end = None
        MAX_CHARS = 40  # 자막 한 줄 최대 글자수

        for segment in segments:
            if not hasattr(segment, "words") or not segment.words:
                # 단어 단위 타임스탬프 없으면 세그먼트 단위로
                srt_lines.append(str(idx))
                srt_lines.append(
                    f"{_srt_timestamp(segment.start)} --> {_srt_timestamp(segment.end)}"
                )
                srt_lines.append(segment.text.strip())
                srt_lines.append("")
                idx += 1
                continue

            for word in segment.words:
                text = word.word.strip()
                if not text:
                    continue

                if current_start is None:
                    current_start = word.start

                current_words.append(text)
                current_end = word.end

                # 최대 글자수 초과 시 자막 확정
                if len("".join(current_words)) >= MAX_CHARS:
                    srt_lines.append(str(idx))
                    srt_lines.append(
                        f"{_srt_timestamp(current_start)} --> {_srt_timestamp(current_end)}"
                    )
                    srt_lines.append(" ".join(current_words))
                    srt_lines.append("")
                    idx += 1
                    current_words = []
                    current_start = None
                    current_end = None

        # 마지막 남은 단어 처리
        if current_words and current_start is not None:
            srt_lines.append(str(idx))
            srt_lines.append(
                f"{_srt_timestamp(current_start)} --> {_srt_timestamp(current_end)}"
            )
            srt_lines.append(" ".join(current_words))
            srt_lines.append("")

        if not srt_lines:
            return False

        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text("\n".join(srt_lines), encoding="utf-8")
        logger.info(f"[Subtitle] Faster-Whisper SRT 완료: {output_path.name} ({idx-1}개 자막)")
        return True

    except Exception as e:
        logger.warning(f"[Subtitle] Faster-Whisper 실패: {e} — pydub 균등분배 폴백")
        return False


def _generate_uniform_srt(script: dict, narration_path: Path, output_path: Path) -> bool:
    """pydub 기반 균등분배 SRT (폴백)"""
    try:
        from pydub import AudioSegment
        total_ms = len(AudioSegment.from_file(str(narration_path)))
    except Exception:
        total_ms = script.get("target_duration_sec", 720) * 1000

    texts = []
    hook = script.get("hook", {})
    if hook.get("text"):
        texts.append(("Hook", hook["text"]))
    for s in script.get("sections", []):
        if s.get("narration_text"):
            texts.append((s.get("heading", ""), s["narration_text"]))

    if not texts:
        return False

    per_ms = total_ms // len(texts)
    srt_lines = []

    def ms2srt(ms: int) -> str:
        h = ms // 3_600_000
        m = (ms % 3_600_000) // 60_000
        s = (ms % 60_000) // 1_000
        r = ms % 1_000
        return f"{h:02d}:{m:02d}:{s:02d},{r:03d}"

    for i, (heading, text) in enumerate(texts):
        srt_lines += [
            str(i + 1),
            f"{ms2srt(i * per_ms)} --> {ms2srt(min((i + 1) * per_ms, total_ms))}",
            text[:80] + ("..." if len(text) > 80 else ""),
            "",
        ]

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(srt_lines), encoding="utf-8")
    logger.info(f"[Subtitle] 균등분배 SRT 완료: {output_path.name} ({len(texts)}개 자막)")
    return True


def generate_subtitles(script: dict, narration_path: Path, output_path: Path) -> bool:
    """
    자막 생성.

    Faster-Whisper(word-level) → pydub 균등분배 폴백 순서.

    Args:
        script: step08 스크립트 dict
        narration_path: 나레이션 오디오 파일 경로
        output_path: 출력 SRT 파일 경로

    Returns:
        True: 성공, False: 실패
    """
    if narration_path.exists() and narration_path.stat().st_size > 0:
        if _generate_whisper_srt(narration_path, output_path):
            return True

    return _generate_uniform_srt(script, narration_path, output_path)
