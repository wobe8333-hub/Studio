"""
v4-Step5: Checkpoint + Rollback Manifest 저장 + Lock 관리

저장 위치:
- checkpoint: backend/output/evolution_v4/checkpoints/<run_id>.json
- rollback: backend/output/evolution_v4/rollbacks/<run_id>_rollback_manifest.json
- lock: backend/output/evolution_v4/checkpoints/<run_id>.lock
"""

import json
from pathlib import Path
from typing import Dict, Any, Optional

from backend.evolution_v4.schema import utc_now_iso, utc_now_compact


def ensure_directories(project_root: Path) -> tuple[Path, Path]:
    """
    출력 디렉토리 생성
    
    Args:
        project_root: 프로젝트 루트 경로
    
    Returns:
        Tuple[Path, Path]: (checkpoints_dir, rollbacks_dir)
    """
    checkpoints_dir = project_root / "backend" / "output" / "evolution_v4" / "checkpoints"
    rollbacks_dir = project_root / "backend" / "output" / "evolution_v4" / "rollbacks"
    
    checkpoints_dir.mkdir(parents=True, exist_ok=True)
    rollbacks_dir.mkdir(parents=True, exist_ok=True)
    
    return checkpoints_dir, rollbacks_dir


def save_checkpoint(
    checkpoint: Dict[str, Any],
    project_root: Path,
    force: bool = False
) -> tuple[Optional[Path], Optional[str]]:
    """
    CheckpointV4 저장 + Lock 생성
    
    Args:
        checkpoint: CheckpointV4 데이터
        project_root: 프로젝트 루트 경로
        force: 기존 lock이 있어도 덮어쓰기 허용
    
    Returns:
        Tuple[Optional[Path], Optional[str]]: (checkpoint_path, error_message)
    """
    checkpoints_dir, _ = ensure_directories(project_root)
    
    run_id = checkpoint["run_id"]
    checkpoint_path = checkpoints_dir / f"{run_id}.json"
    lock_path = checkpoints_dir / f"{run_id}.lock"
    
    # Lock 존재 확인
    if lock_path.exists() and not force:
        return None, "CHECKPOINT_ALREADY_FROZEN"
    
    # --force 시 백업
    if force and checkpoint_path.exists():
        backup_path = checkpoints_dir / f"{run_id}.json.bak.{utc_now_compact()}"
        try:
            checkpoint_path.rename(backup_path)
        except Exception as e:
            return None, f"Failed to backup checkpoint: {str(e)}"
    
    # Checkpoint 저장 (utf-8-sig for PowerShell compatibility)
    try:
        with open(checkpoint_path, "w", encoding="utf-8-sig") as f:
            json.dump(checkpoint, f, ensure_ascii=False, indent=2)
    except Exception as e:
        return None, f"Failed to save checkpoint: {str(e)}"
    
    # Lock 생성
    lock_data = {
        "run_id": run_id,
        "checkpoint_path": str(checkpoint_path.resolve()),
        "frozen_at": checkpoint["created_at"]
    }
    
    try:
        with open(lock_path, "w", encoding="utf-8") as f:
            json.dump(lock_data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        return None, f"Failed to save lock: {str(e)}"
    
    return checkpoint_path, None


def save_rollback_manifest(
    rollback_manifest: Dict[str, Any],
    project_root: Path,
    force: bool = False
) -> tuple[Optional[Path], Optional[str]]:
    """
    Rollback Manifest 저장
    
    Args:
        rollback_manifest: Rollback Manifest 데이터
        project_root: 프로젝트 루트 경로
        force: 기존 파일이 있어도 덮어쓰기 허용
    
    Returns:
        Tuple[Optional[Path], Optional[str]]: (rollback_path, error_message)
    """
    _, rollbacks_dir = ensure_directories(project_root)
    
    run_id = rollback_manifest["run_id"]
    rollback_path = rollbacks_dir / f"{run_id}_rollback_manifest.json"
    
    # --force 시 백업
    if force and rollback_path.exists():
        backup_path = rollbacks_dir / f"{run_id}_rollback_manifest.json.bak.{utc_now_compact()}"
        try:
            rollback_path.rename(backup_path)
        except Exception as e:
            return None, f"Failed to backup rollback manifest: {str(e)}"
    
    # Rollback Manifest 저장 (utf-8-sig for PowerShell compatibility)
    try:
        with open(rollback_path, "w", encoding="utf-8-sig") as f:
            json.dump(rollback_manifest, f, ensure_ascii=False, indent=2)
    except Exception as e:
        return None, f"Failed to save rollback manifest: {str(e)}"
    
    return rollback_path, None

