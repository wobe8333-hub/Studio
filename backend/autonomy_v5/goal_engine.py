"""
v5-Step1: Goal Engine

기능:
- v4 Checkpoint와 Rollback Manifest를 참조하여 GoalDefinitionV5 생성
- 실제 실행/선택/추천 금지
- 목표와 제약만 정의
"""

import json
import hashlib
from pathlib import Path
from typing import Dict, Any, Optional

from backend.autonomy_v5.schema import create_goal_definition_v5


def sha256_file(path: Path) -> str:
    """
    파일의 SHA256 해시 계산
    
    Args:
        path: 파일 경로
    
    Returns:
        str: SHA256 해시 (hex)
    """
    sha256_hash = hashlib.sha256()
    with open(path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()


def load_json_safe(path: Path) -> Optional[Dict[str, Any]]:
    """
    JSON 파일 안전 로드
    
    Args:
        path: 파일 경로
    
    Returns:
        Optional[Dict]: JSON 데이터 (실패 시 None)
    """
    if not path.exists():
        return None
    
    try:
        encoding = "utf-8-sig" if path.suffix == ".json" else "utf-8"
        with open(path, "r", encoding=encoding) as f:
            return json.load(f)
    except Exception:
        return None


def generate_goal_definition(
    run_id: str,
    project_root: Optional[Path] = None
) -> tuple[Optional[Dict[str, Any]], Optional[str]]:
    """
    GoalDefinitionV5 생성 (전체 프로세스)
    
    Args:
        run_id: 실행 ID
        project_root: 프로젝트 루트 경로
    
    Returns:
        Tuple[Optional[Dict], Optional[str]]: (goal_definition, error_message)
    """
    if project_root is None:
        project_root = Path.cwd()
    
    # v4 Checkpoint 검증
    checkpoint_path = project_root / "backend" / "output" / "evolution_v4" / "checkpoints" / f"{run_id}.json"
    checkpoint_lock_path = project_root / "backend" / "output" / "evolution_v4" / "checkpoints" / f"{run_id}.lock"
    
    if not checkpoint_path.exists():
        return None, f"v4 Checkpoint not found: {checkpoint_path.resolve()}"
    
    if not checkpoint_lock_path.exists():
        return None, f"v4 Checkpoint lock not found: {checkpoint_lock_path.resolve()}"
    
    # v4 Rollback Manifest 검증
    rollback_path = project_root / "backend" / "output" / "evolution_v4" / "rollbacks" / f"{run_id}_rollback_manifest.json"
    
    if not rollback_path.exists():
        return None, f"v4 Rollback manifest not found: {rollback_path.resolve()}"
    
    # 해시 계산
    checkpoint_hash = sha256_file(checkpoint_path)
    rollback_manifest_hash = sha256_file(rollback_path)
    
    # GoalDefinition 생성
    goal_definition = create_goal_definition_v5(
        run_id, checkpoint_hash, rollback_manifest_hash
    )
    
    return goal_definition, None

