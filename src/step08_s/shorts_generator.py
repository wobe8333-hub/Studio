"""
STEP 08-S — Shorts 영상 자동 생성기.

Phase 7 추가:
  Long-form 영상에서 핵심 60초 구간 자동 추출 → 세로 9:16 크롭 → Shorts 생성
  구조: hook(0~25초) + 핵심팩트(30초) + CTA(5초) = 60초
"""

import subprocess
from pathlib import Path

from loguru import logger

from src.core.config import FFMPEG_PATH
from src.core.ssot import get_run_dir, now_iso, write_json


def _run_ffmpeg(cmd: list, timeout: int = 120) -> bool:
    """FFmpeg 명령 실행"""
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            timeout=timeout,
        )
        return result.returncode == 0
    except Exception as e:
        logger.error(f"[Shorts] FFmpeg 실패: {e}")
        return False


def _crop_to_vertical(input_path: Path, output_path: Path, start_sec: float, duration: float) -> bool:
    """
    Long-form 영상에서 구간 추출 후 9:16 세로 크롭.
    1920x1080 → 중앙 크롭 → 608x1080 → 스케일 → 1080x1920 (Shorts 규격)
    """
    cmd = [
        FFMPEG_PATH, "-y",
        "-ss", str(start_sec),
        "-i", str(input_path),
        "-t", str(duration),
        "-vf", (
            "crop=608:1080:(iw-608)/2:0,"  # 중앙 16:9→9:16 크롭
            "scale=1080:1920,"              # Shorts 규격으로 확대
            "setsar=1"
        ),
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        "-c:a", "aac", "-b:a", "128k",
        str(output_path),
    ]
    return _run_ffmpeg(cmd)


def _add_subtitle_overlay(input_path: Path, srt_path: Path, output_path: Path) -> bool:
    """Shorts용 자막 오버레이 (글자 크기 확대)"""
    # srt 경로의 역슬래시를 이스케이프 처리 (Windows)
    srt_safe = str(srt_path).replace("\\", "/").replace(":", "\\:")
    cmd = [
        FFMPEG_PATH, "-y",
        "-i", str(input_path),
        "-vf", (
            f"subtitles='{srt_safe}':"
            "force_style='FontSize=22,PrimaryColour=&HFFFFFF&,"
            "OutlineColour=&H000000&,Outline=2,Bold=1'"
        ),
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        "-c:a", "copy",
        str(output_path),
    ]
    return _run_ffmpeg(cmd)


def generate_shorts(
    longform_path: Path,
    srt_path: Path,
    script: dict,
    output_dir: Path,
    channel_id: str,
    count: int = 3,
) -> list:
    """
    Long-form 영상에서 Shorts 생성.

    hook 구간 + 핵심 섹션 구간 × count개 생성.

    Args:
        longform_path: Long-form video.mp4
        srt_path: 자막 .srt 파일
        script: step08 스크립트 dict
        output_dir: Shorts 출력 디렉토리
        channel_id: CH1~CH7
        count: 생성할 Shorts 수 (기본 3)

    Returns:
        생성된 Shorts 파일 경로 리스트
    """
    if not longform_path.exists():
        logger.error(f"[Shorts] Long-form 영상 없음: {longform_path}")
        return []

    output_dir.mkdir(parents=True, exist_ok=True)
    target_duration = script.get("target_duration_sec", 720)
    sections = script.get("sections", [])
    hook_sec = script.get("hook", {}).get("duration_estimate_sec", 25)

    # Shorts 구간 계획
    clips = []

    # 1) Hook 기반 Shorts (항상 첫 번째)
    clips.append({
        "label": "hook",
        "start": 0,
        "duration": min(60, hook_sec + 35),  # hook + 35초 내용
    })

    # 2) 핵심 섹션 기반 Shorts
    if sections and count > 1:
        section_count = len(sections)
        for i in range(1, count):
            # 각 Shorts는 영상의 다른 구간에서 추출
            section_idx = min(i * (section_count // max(count, 1)), section_count - 1)
            # 섹션 시작 시간 추정 (균등 분배)
            section_start = (target_duration * section_idx) // max(section_count, 1)
            clips.append({
                "label": f"section_{section_idx}",
                "start": max(0, section_start),
                "duration": 60,
            })

    # Shorts 생성
    generated = []
    for i, clip in enumerate(clips[:count]):
        raw_out = output_dir / f"shorts_{i+1:02d}_raw.mp4"
        final_out = output_dir / f"shorts_{i+1:02d}.mp4"

        # 세로 크롭
        ok = _crop_to_vertical(longform_path, raw_out, clip["start"], clip["duration"])
        if not ok:
            logger.warning(f"[Shorts] 크롭 실패: {clip['label']}")
            continue

        # 자막 오버레이 (SRT 있을 때만)
        if srt_path and srt_path.exists():
            ok2 = _add_subtitle_overlay(raw_out, srt_path, final_out)
            if ok2:
                raw_out.unlink(missing_ok=True)
            else:
                final_out = raw_out  # 자막 실패 시 raw 사용
        else:
            final_out = raw_out

        generated.append(final_out)
        logger.info(f"[Shorts] 생성 완료: {final_out.name} ({clip['label']})")

    return generated


def run_step08s(channel_id: str, run_id: str, shorts_count: int = 3) -> dict:
    """
    Step 08-S 실행 (pipeline.py에서 호출).

    Returns:
        {"generated_count": int, "paths": [str], "ok": bool}
    """
    run_dir = get_run_dir(channel_id, run_id)
    s08 = run_dir / "step08"
    shorts_dir = run_dir / "step08s"

    longform = s08 / "video.mp4"
    srt_path = s08 / "subtitles.srt"

    from src.core.ssot import json_exists, read_json
    script = read_json(s08 / "script.json") if json_exists(s08 / "script.json") else {}

    generated = generate_shorts(
        longform_path=longform,
        srt_path=srt_path,
        script=script,
        output_dir=shorts_dir,
        channel_id=channel_id,
        count=shorts_count,
    )

    result = {
        "channel_id": channel_id,
        "run_id": run_id,
        "generated_at": now_iso(),
        "generated_count": len(generated),
        "paths": [str(p) for p in generated],
        "ok": len(generated) > 0,
    }

    write_json(shorts_dir / "shorts_report.json", result)
    logger.info(f"[STEP08S] {channel_id}/{run_id}: {len(generated)}개 Shorts 생성")
    return result
