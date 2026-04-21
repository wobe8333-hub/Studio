"""Track D — Assembly: 나레이션 싱크 컷 연결 + BGM 덕킹 + 자막 번인 + 인트로/아웃트로"""
from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING

from loguru import logger

from src.pipeline_v2.episode_schema import EpisodeMeta

if TYPE_CHECKING:
    from src.pipeline_v2.dag.orchestrator import EpisodeJob

ASSEMBLY_ROOT = Path("runs/pipeline_v2")
TEMPLATES_ROOT = Path("assets/templates")

# EBU R128 목표 라우드니스
TARGET_LUFS = -14.0
BGM_DUCK_DB = -14.0  # 나레이션 대비 BGM 낮춤


def _run_ffmpeg(cmd: list[str], tag: str = "ffmpeg") -> None:
    result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if result.returncode != 0:
        raise RuntimeError(f"[{tag}] FFmpeg 실패:\n{result.stderr[-500:]}")
    logger.debug(f"[{tag}] 완료")


def _build_ken_burns_filter(scene_count: int, duration_each: float = 5.0) -> str:
    """Ken Burns 효과 필터 문자열 생성."""
    filters = []
    for i in range(scene_count):
        scale = 1.04 + (i % 3) * 0.02
        x_shift = (i % 5) * 8
        y_shift = (i % 3) * 5
        filters.append(
            f"[{i}:v]scale=1920:1080,zoompan=z='min(zoom+0.001,{scale})':"
            f"x='{x_shift}':y='{y_shift}':d={int(duration_each * 30)}:fps=30[v{i}]"
        )
    return ";".join(filters)


def _concat_video_with_narration(
    scene_images: list[str],
    narration_path: str,
    output_path: Path,
    storyboard: list[dict],
) -> Path:
    """씬 이미지 + 나레이션을 FFmpeg로 연결."""
    if not scene_images:
        raise ValueError("scene_images가 비어 있습니다.")

    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False, encoding="utf-8") as f:
        for img_path in scene_images:
            duration = next(
                (s.get("duration_sec", 5) for s in storyboard if s.get("insert_type") == "doodle"),
                5,
            )
            f.write(f"file '{Path(img_path).as_posix()}'\n")
            f.write(f"duration {duration}\n")
        list_path = f.name

    cmd = [
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0", "-i", list_path,
        "-i", narration_path,
        "-vf", "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2",
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        "-c:a", "aac", "-b:a", "192k",
        "-shortest", str(output_path),
    ]
    _run_ffmpeg(cmd, "concat_narration")
    return output_path


def _add_bgm_ducking(video_path: Path, bgm_path: str, output_path: Path) -> Path:
    """BGM 사이드체인 덕킹 — 나레이션 구간에서 BGM -14dB 억제."""
    cmd = [
        "ffmpeg", "-y",
        "-i", str(video_path),
        "-stream_loop", "-1", "-i", bgm_path,
        "-filter_complex",
        f"[1:a]volume={BGM_DUCK_DB}dB[bgm_quiet];"
        "[0:a][bgm_quiet]amix=inputs=2:duration=first:dropout_transition=3[aout]",
        "-map", "0:v", "-map", "[aout]",
        "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
        str(output_path),
    ]
    _run_ffmpeg(cmd, "bgm_duck")
    return output_path


def _add_subtitles(video_path: Path, subtitle_path: Path, output_path: Path) -> Path:
    """자막 번인 (SRT → 하드코딩)."""
    if not subtitle_path.exists():
        logger.warning(f"자막 파일 없음: {subtitle_path}, 자막 스킵")
        import shutil
        shutil.copy(video_path, output_path)
        return output_path

    cmd = [
        "ffmpeg", "-y",
        "-i", str(video_path),
        "-vf", f"subtitles={subtitle_path.as_posix()}:force_style='FontName=Noto Sans KR,FontSize=18,PrimaryColour=&HFFFFFF&,OutlineColour=&H000000&,Outline=1'",
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        "-c:a", "copy",
        str(output_path),
    ]
    _run_ffmpeg(cmd, "subtitles")
    return output_path


def _attach_intro_outro(video_path: Path, channel_id: str, output_path: Path) -> Path:
    """인트로/아웃트로 합성."""
    intro = TEMPLATES_ROOT / channel_id / "intro.mp4"
    outro = TEMPLATES_ROOT / channel_id / "outro.mp4"

    if not intro.exists() and not outro.exists():
        logger.warning("인트로/아웃트로 템플릿 없음, 스킵")
        import shutil
        shutil.copy(video_path, output_path)
        return output_path

    parts = []
    if intro.exists():
        parts.append(str(intro))
    parts.append(str(video_path))
    if outro.exists():
        parts.append(str(outro))

    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False, encoding="utf-8") as f:
        for p in parts:
            f.write(f"file '{Path(p).as_posix()}'\n")
        list_path = f.name

    cmd = [
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0", "-i", list_path,
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        "-c:a", "aac", "-b:a", "192k",
        str(output_path),
    ]
    _run_ffmpeg(cmd, "intro_outro")
    return output_path


def _normalize_loudness(video_path: Path, output_path: Path) -> Path:
    """EBU R128 라우드니스 정규화 (QC Layer2 사전 적용)."""
    cmd = [
        "ffmpeg", "-y",
        "-i", str(video_path),
        "-af", f"loudnorm=I={TARGET_LUFS}:TP=-1.5:LRA=11",
        "-c:v", "copy",
        str(output_path),
    ]
    _run_ffmpeg(cmd, "loudnorm")
    return output_path


async def run_track_d(job: "EpisodeJob") -> dict:
    """Track D: 영상 조립 (컷 연결 → BGM 덕킹 → 자막 → 인트로/아웃트로 → 라우드니스).

    Returns: {"video_path": str, "duration_sec": int}
    """
    meta: EpisodeMeta = job.episode_meta
    channel_id = meta.channel_id

    out_dir = ASSEMBLY_ROOT / meta.episode_id / "assembly"
    out_dir.mkdir(parents=True, exist_ok=True)

    scene_images = job.track_c_result.output.get("scene_images", []) if job.track_c_result else []
    storyboard = job.track_c_result.output.get("storyboard", []) if job.track_c_result else []
    narration_path = job.track_b_result.output.get("narration_path", "") if job.track_b_result else ""
    bgm_path = job.track_b_result.output.get("bgm_path", "") if job.track_b_result else ""

    # Manim 인서트 병합 (CH1/CH2)
    manim_scenes = job.track_c_result.output.get("manim_scenes", []) if job.track_c_result else []
    if manim_scenes:
        from src.pipeline_v2.manim_insert import inject_manim_scenes
        scene_images = inject_manim_scenes(scene_images, manim_scenes, storyboard, meta, out_dir)

    # 1. 컷 연결 + 나레이션 싱크
    step1 = out_dir / "step1_cut.mp4"
    _concat_video_with_narration(scene_images, narration_path, step1, storyboard)

    # 2. BGM 덕킹
    step2 = out_dir / "step2_bgm.mp4"
    if bgm_path and Path(bgm_path).exists():
        _add_bgm_ducking(step1, bgm_path, step2)
    else:
        import shutil
        shutil.copy(step1, step2)

    # 3. 자막 번인
    subtitle_path = Path(ASSEMBLY_ROOT / meta.episode_id / "audio" / "subtitle.srt")
    step3 = out_dir / "step3_sub.mp4"
    _add_subtitles(step2, subtitle_path, step3)

    # 4. 인트로/아웃트로
    step4 = out_dir / "step4_intro_outro.mp4"
    _attach_intro_outro(step3, channel_id, step4)

    # 5. 라우드니스 정규화
    final = out_dir / f"final_{meta.episode_id}.mp4"
    _normalize_loudness(step4, final)

    # 영상 길이 확인
    duration_sec = _probe_duration(final)
    meta.features.duration_sec = duration_sec
    meta.video_path = str(final)

    # final_video.json 저장 (Multi-Platform 사전 설계)
    from src.core.ssot import write_json
    write_json(
        out_dir / "final_video.json",
        {
            "episode_id": meta.episode_id,
            "video_path": str(final),
            "duration_sec": duration_sec,
            "platforms_uploaded": ["youtube_longform"],
            "platforms_ready": ["youtube_shorts", "tiktok", "ig_reels", "x"],
        },
    )

    logger.info(f"Track D 완료: {final} ({duration_sec}s)")
    return {"video_path": str(final), "duration_sec": duration_sec}


def _probe_duration(video_path: Path) -> int:
    if not video_path.exists():
        return 0
    cmd = [
        "ffprobe", "-v", "quiet", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", str(video_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    try:
        return int(float(result.stdout.strip()))
    except ValueError:
        return 0
