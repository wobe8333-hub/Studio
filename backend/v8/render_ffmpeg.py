import os
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional

from backend.v8 import V8FFmpegNotFound
from backend.video.utils import probe_video_metadata


def _now_utc_iso() -> str:
    return datetime.utcnow().isoformat() + "Z"


def _find_ffmpeg() -> str:
    """
    FFMPEG_PATH 우선, 없으면 PATH 검색.
    없으면 V8FFmpegNotFound (exit 71).
    """
    env_path = os.getenv("FFMPEG_PATH")
    if env_path:
        exe = Path(env_path)
        if exe.exists():
            return str(exe)
    found = shutil.which("ffmpeg")
    if found:
        return found
    raise V8FFmpegNotFound("ffmpeg not found (FFMPEG_PATH and PATH both missing)")


def build_images_concat_list(images: List[Path], duration_sec: float, list_path: Path) -> None:
    """
    concat 데먹서용 리스트 파일 생성.
    각 이미지 duration = total / count.
    """
    n = len(images)
    if n == 0:
        raise ValueError("images must be non-empty")

    per = duration_sec / float(n)
    list_lines: List[str] = []
    for idx, img in enumerate(images):
        img_abs = img.resolve()
        img_norm = str(img_abs).replace("\\", "/")
        list_lines.append(f"file '{img_norm}'")
        list_lines.append(f"duration {per:.3f}")
        if idx == n - 1:
            # 마지막 이미지는 한 번 더 명시하여 duration 유지
            list_lines.append(f"file '{img_norm}'")

    list_path.write_text("\n".join(list_lines) + "\n", encoding="utf-8")


def render_video(
    images: List[Path],
    narration_wav: Path,
    target_duration_sec: float,
    output_path: Path,
    report_path: Path,
    bgm_wav: Optional[Path] = None,
) -> None:
    """
    FFmpeg를 이용해 정적인 섹션 이미지를 타임라인에 올리고
    narration.wav를 주 오디오로 사용하며,
    선택적으로 bgm.wav를 낮은 볼륨으로 믹스하여 1920x1080@30 H.264 + AAC 비디오 생성.
    """
    ffmpeg = _find_ffmpeg()

    output_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)

    images = list(images)
    for p in images:
        if not p.is_file():
            raise FileNotFoundError(f"missing image for render: {p}")
    if not narration_wav.is_file():
        raise FileNotFoundError(f"missing narration.wav: {narration_wav}")

    concat_list = output_path.parent / "v8_images_concat.txt"
    build_images_concat_list(images, target_duration_sec, concat_list)

    use_bgm = bgm_wav is not None and bgm_wav.is_file()

    if use_bgm:
        # 입력 스트림 인덱스:
        # 0: concat된 이미지 시퀀스 (비디오)
        # 1: narration.wav (오디오)
        # 2: bgm.wav (오디오, 낮은 볼륨으로 mix)
        cmd: List[str] = [
            ffmpeg,
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(concat_list),
            "-i",
            str(narration_wav),
            "-i",
            str(bgm_wav),
            "-filter_complex",
            # narration(1:a)은 그대로, bgm(2:a)은 0.12 배로 줄인 뒤 amix
            "[2:a]volume=0.12[bgm];[1:a][bgm]amix=inputs=2:duration=first:dropout_transition=0[aout]",
            "-map",
            "0:v",
            "-map",
            "[aout]",
            "-r",
            "30",
            "-vf",
            "scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-shortest",
            "-movflags",
            "+faststart",
            str(output_path),
        ]
    else:
        # 기존과 동일: narration only
        cmd = [
            ffmpeg,
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(concat_list),
            "-i",
            str(narration_wav),
            "-r",
            "30",
            "-vf",
            "scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-shortest",
            "-movflags",
            "+faststart",
            str(output_path),
        ]

    started_at = _now_utc_iso()
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
    )
    finished_at = _now_utc_iso()

    actual_duration_sec = None
    if output_path.exists() and output_path.is_file():
        meta = probe_video_metadata(output_path)
        try:
            d = meta.get("duration")
            if isinstance(d, str):
                actual_duration_sec = float(d)
        except Exception:
            actual_duration_sec = None

    report: Dict[str, Any] = {
        "renderer": "ffmpeg",
        "ffmpeg_path": ffmpeg,
        "command": " ".join(cmd),
        "target_duration_sec": target_duration_sec,
        "started_at_utc": started_at,
        "finished_at_utc": finished_at,
        "exit_code": result.returncode,
        "stdout_tail": (result.stdout or "")[-500:],
        "stderr_tail": (result.stderr or "")[-500:],
    }
    if actual_duration_sec is not None:
        report["actual_duration_sec"] = actual_duration_sec

    if result.returncode != 0:
        report["missing_reason"] = "ffmpeg_failed"

    import json

    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg render failed with code {result.returncode}")

