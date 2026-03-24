"""
Environment Snapshot - 환경 스냅샷

처음문서_v1.2 기준:
"environment 필드는 run의 실행 환경을 기록한다."
"""

import sys
import platform
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional


def get_ffmpeg_version() -> Optional[str]:
    """
    ffmpeg 버전 확인
    
    Returns:
        Optional[str]: ffmpeg 버전 (없으면 None)
    """
    try:
        result = subprocess.run(
            ["ffmpeg", "-version"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            # 첫 줄에서 버전 추출
            first_line = result.stdout.split('\n')[0]
            if 'ffmpeg version' in first_line:
                parts = first_line.split()
                if len(parts) >= 3:
                    return parts[2]
        return None
    except Exception:
        return None


def get_project_root() -> Path:
    """
    프로젝트 루트 경로 반환
    
    Returns:
        Path: 프로젝트 루트
    """
    # backend/utils/env_snapshot.py -> backend -> 프로젝트 루트
    return Path(__file__).resolve().parents[2]


def capture_environment() -> Dict[str, Any]:
    """
    현재 환경 스냅샷 캡처
    
    Returns:
        Dict: environment 데이터
    """
    return {
        "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        "os_name": platform.system(),
        "platform": platform.platform(),
        "ffmpeg_version": get_ffmpeg_version(),
        "project_root": str(get_project_root())
    }


def ensure_environment(manifest: Dict[str, Any]) -> Dict[str, Any]:
    """
    manifest에 environment 필드 백필
    
    Args:
        manifest: run manifest
    
    Returns:
        Dict: environment 데이터
    """
    # 기존 environment가 있으면 유지
    existing_env = manifest.get("environment", {})
    if existing_env and existing_env.get("python_version"):
        return existing_env
    
    # 새로 캡처
    return capture_environment()

