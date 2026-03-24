import subprocess, logging, shutil
from pathlib import Path
from src.core.config import FFMPEG_PATH

logger = logging.getLogger(__name__)

def image_to_clip(image_path: Path, output_path: Path, duration_sec: float = 5.0) -> bool:
    cmd = [FFMPEG_PATH,"-y","-loop","1","-i",str(image_path),"-t",str(duration_sec),
           "-vf","scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2",
           "-c:v","libx264","-pix_fmt","yuv420p",str(output_path)]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    if r.returncode != 0: logger.error(f"FFMPEG_IMAGE_TO_CLIP: {r.stderr[:300]}"); return False
    return True

def concat_clips(clip_paths: list, output_path: Path) -> bool:
    lf = output_path.parent / "concat_list.txt"
    with open(lf,"w",encoding="utf-8") as f:
        for p in clip_paths: f.write(f"file '{p.as_posix()}'\n")
    cmd = [FFMPEG_PATH,"-y","-f","concat","-safe","0","-i",str(lf),"-c","copy",str(output_path)]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    lf.unlink(missing_ok=True)
    if r.returncode != 0: logger.error(f"FFMPEG_CONCAT: {r.stderr[:300]}"); return False
    return True

def add_narration(video_path: Path, narration_path: Path, output_path: Path) -> bool:
    cmd = [FFMPEG_PATH,"-y","-i",str(video_path),"-i",str(narration_path),
           "-c:v","copy","-c:a","aac","-b:a","192k","-shortest",str(output_path)]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    if r.returncode != 0: logger.error(f"FFMPEG_ADD_NARRATION: {r.stderr[:300]}"); return False
    return True

def add_subtitles(video_path: Path, srt_path: Path, output_path: Path) -> bool:
    srt = srt_path.as_posix().replace(":","\\:")
    cmd = [FFMPEG_PATH,"-y","-i",str(video_path),"-vf",f"subtitles='{srt}'","-c:a","copy",str(output_path)]
    r   = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    if r.returncode != 0:
        logger.warning(f"FFMPEG_SUBTITLES fallback: {r.stderr[:200]}")
        shutil.copy2(video_path, output_path)
    return True

def overlay_bgm(video_path: Path, bgm_path: Path, output_path: Path, bgm_volume: float = 0.08) -> bool:
    cmd = [FFMPEG_PATH,"-y","-i",str(video_path),"-i",str(bgm_path),
           "-filter_complex",
           f"[1:a]volume={bgm_volume},aloop=loop=-1:size=2e+09[bgm];"
           "[0:a][bgm]amix=inputs=2:duration=first:dropout_transition=3[aout]",
           "-map","0:v","-map","[aout]","-c:v","copy","-c:a","aac","-b:a","192k",str(output_path)]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    if r.returncode != 0: logger.error(f"FFMPEG_BGM_OVERLAY: {r.stderr[:300]}"); return False
    return True
