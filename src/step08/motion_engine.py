"""
STEP 08 — 모션 엔진.

정적 이미지 시퀀스에 Ken Burns 팬/줌 효과와 전환 애니메이션을 적용해
MP4 클립을 생성한다.

GPU 필요 없음 — FFmpeg 기반 순수 소프트웨어 렌더링.
"""

import subprocess
from pathlib import Path
from typing import List, Optional

from loguru import logger

from src.core.config import FFMPEG_PATH

# 지원 전환 효과 (FFmpeg xfade filter)
TRANSITION_TYPES = ["fade", "slideleft", "slideright", "slideup", "wipeleft", "wiperight"]

# Ken Burns 프리셋 (zoom-in/out + 팬 방향)
_KB_PRESETS = [
    # zoom-in center
    "scale=2*iw:2*ih,zoompan=z='min(zoom+0.002,1.5)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=125:s=1920x1080",
    # zoom-out center
    "scale=2*iw:2*ih,zoompan=z='if(lte(zoom,1.0),1.5,max(1.0,zoom-0.003))':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=125:s=1920x1080",
    # pan right + zoom-in
    "scale=2*iw:2*ih,zoompan=z='min(zoom+0.001,1.3)':x='if(lte(on,1),0,x+1)':y='ih/2-(ih/zoom/2)':d=125:s=1920x1080",
    # pan left + zoom-in
    "scale=2*iw:2*ih,zoompan=z='min(zoom+0.001,1.3)':x='if(lte(on,1),iw/2,max(0,x-1))':y='ih/2-(ih/zoom/2)':d=125:s=1920x1080",
]


def apply_ken_burns(
    image_path: Path,
    output_path: Path,
    duration_sec: float = 6.0,
    preset_index: int = 0,
) -> bool:
    """
    단일 이미지에 Ken Burns 팬/줌 효과를 적용하여 MP4 클립 생성.

    Args:
        image_path: 입력 PNG/JPG 이미지
        output_path: 출력 MP4 경로
        duration_sec: 클립 길이 (초)
        preset_index: Ken Burns 프리셋 인덱스 (0~3 순환)

    Returns:
        성공 여부
    """
    preset = _KB_PRESETS[preset_index % len(_KB_PRESETS)]
    fps = 25
    frame_count = int(duration_sec * fps)

    # zoompan d 파라미터를 실제 프레임 수로 교체
    vf = preset.replace("d=125", f"d={frame_count}")

    cmd = [
        FFMPEG_PATH, "-y",
        "-loop", "1",
        "-i", str(image_path),
        "-vf", vf,
        "-t", str(duration_sec),
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-r", str(fps),
        str(output_path),
    ]

    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if r.returncode != 0:
            logger.warning(f"[MOTION] Ken Burns 실패 ({image_path.name}): {r.stderr[:200]}")
            return False
        return True
    except subprocess.TimeoutExpired:
        logger.warning(f"[MOTION] Ken Burns 타임아웃: {image_path.name}")
        return False
    except Exception as e:
        logger.error(f"[MOTION] Ken Burns 오류: {e}")
        return False


def apply_static_clip(
    image_path: Path,
    output_path: Path,
    duration_sec: float = 6.0,
) -> bool:
    """Ken Burns 실패 시 정적 클립 폴백 (기존 image_to_clip과 동일)."""
    cmd = [
        FFMPEG_PATH, "-y",
        "-loop", "1",
        "-i", str(image_path),
        "-t", str(duration_sec),
        "-vf", "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2",
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        str(output_path),
    ]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    if r.returncode != 0:
        logger.error(f"[MOTION] static clip 실패: {r.stderr[:200]}")
        return False
    return True


def create_motion_clip(
    image_path: Path,
    output_path: Path,
    duration_sec: float = 6.0,
    preset_index: int = 0,
    use_ken_burns: bool = True,
) -> bool:
    """
    이미지 → 모션 클립 변환 (Ken Burns 시도 → 정적 폴백).

    Args:
        image_path: 입력 이미지
        output_path: 출력 MP4
        duration_sec: 클립 길이
        preset_index: Ken Burns 프리셋 인덱스 (섹션마다 순환하여 변화 주기)
        use_ken_burns: False면 정적 클립만 생성

    Returns:
        성공 여부
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if use_ken_burns:
        ok = apply_ken_burns(image_path, output_path, duration_sec, preset_index)
        if ok:
            return True
        logger.debug(f"[MOTION] Ken Burns → 정적 폴백: {image_path.name}")

    return apply_static_clip(image_path, output_path, duration_sec)


def batch_create_motion_clips(
    image_paths: List[Path],
    output_dir: Path,
    duration_sec: float = 6.0,
    use_ken_burns: bool = True,
) -> List[Optional[Path]]:
    """
    이미지 리스트 → 모션 클립 리스트 일괄 변환.

    Args:
        image_paths: 섹션 순서대로 정렬된 이미지 파일 리스트
        output_dir: 클립 출력 디렉토리
        duration_sec: 각 클립 길이
        use_ken_burns: Ken Burns 효과 사용 여부

    Returns:
        생성된 클립 경로 리스트 (실패 시 None)
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    results: List[Optional[Path]] = []

    for i, img_path in enumerate(image_paths):
        clip_path = output_dir / f"motion_{i:03d}.mp4"
        ok = create_motion_clip(
            image_path=img_path,
            output_path=clip_path,
            duration_sec=duration_sec,
            preset_index=i,  # 섹션마다 다른 프리셋으로 시각적 변화
            use_ken_burns=use_ken_burns,
        )
        results.append(clip_path if ok else None)

    success_count = sum(1 for r in results if r is not None)
    logger.info(f"[MOTION] 모션 클립 생성 완료: {success_count}/{len(image_paths)}")
    return results
