"""
Replay Manifest - 결정론적 재현을 위한 메타데이터 저장
"""

import json
import hashlib
import sys
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime


def _find_repo_root() -> Path:
    """repo root 탐색"""
    p = Path(__file__).resolve()
    for parent in [p.parent] + list(p.parents):
        if (parent / "backend").is_dir() and (parent / "config").is_dir():
            return parent
    raise RuntimeError(f"repo root not found. Searched from: {__file__}")


def _sha256_file(path: Path) -> str:
    """파일 SHA256 해시 계산"""
    if not path.exists():
        return ""
    sha256 = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            sha256.update(chunk)
    return sha256.hexdigest()


def _get_python_version() -> str:
    """Python 버전"""
    return f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"


def _get_git_commit() -> str:
    """Git commit hash"""
    try:
        repo_root = _find_repo_root()
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return "unknown"


def _get_pip_freeze_sha256() -> str:
    """pip freeze 출력의 SHA256"""
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "freeze"],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0:
            content = result.stdout
            return hashlib.sha256(content.encode("utf-8")).hexdigest()
    except Exception:
        pass
    return "unknown"


def create_manifest(
    cycle_id: str,
    policy_sha256: str,
    snapshots_sha256: str
) -> Dict[str, Any]:
    """
    Replay Manifest 생성
    
    Args:
        cycle_id: cycle_id
        policy_sha256: 정책 파일 SHA256
        snapshots_sha256: 스냅샷 디렉토리 SHA256 (전체 파일 해시 결합)
    
    Returns:
        Manifest 딕셔너리
    """
    return {
        "cycle_id": cycle_id,
        "created_at": datetime.utcnow().isoformat() + "Z",
        "policy_sha256": policy_sha256,
        "snapshots_sha256": snapshots_sha256,
        "python_version": _get_python_version(),
        "git_commit": _get_git_commit(),
        "pip_freeze_sha256": _get_pip_freeze_sha256()
    }


def save_manifest(cycle_id: str, manifest: Dict[str, Any]) -> Path:
    """
    Manifest 저장
    
    Returns:
        저장된 파일 경로
    """
    repo_root = _find_repo_root()
    kd_root = repo_root / "keyword_discovery"
    snapshots_dir = kd_root / "snapshots" / cycle_id
    snapshots_dir.mkdir(parents=True, exist_ok=True)
    
    manifest_path = snapshots_dir / f"manifest_{cycle_id}.json"
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
    
    return manifest_path


def load_manifest(cycle_id: str) -> Optional[Dict[str, Any]]:
    """Manifest 로드"""
    repo_root = _find_repo_root()
    kd_root = repo_root / "keyword_discovery"
    snapshots_dir = kd_root / "snapshots" / cycle_id
    manifest_path = snapshots_dir / f"manifest_{cycle_id}.json"
    
    if not manifest_path.exists():
        return None
    
    try:
        with open(manifest_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def compute_snapshots_sha256(cycle_id: str) -> str:
    """스냅샷 디렉토리 전체 SHA256 계산 (모든 파일 해시 결합)"""
    repo_root = _find_repo_root()
    kd_root = repo_root / "keyword_discovery"
    snapshots_dir = kd_root / "snapshots" / cycle_id
    
    if not snapshots_dir.exists():
        return ""
    
    file_hashes = []
    for file_path in sorted(snapshots_dir.rglob("*")):
        if file_path.is_file():
            file_hash = _sha256_file(file_path)
            if file_hash:
                file_hashes.append(f"{file_path.name}:{file_hash}")
    
    combined = "\n".join(file_hashes)
    return hashlib.sha256(combined.encode("utf-8")).hexdigest()

