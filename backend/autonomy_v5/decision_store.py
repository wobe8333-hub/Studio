"""
v5-Step3: Execution Decision 저장 + Lock 관리

저장 위치:
- decision: backend/output/autonomy_v5/decisions/<run_id>_execution_decision.json
- lock: backend/output/autonomy_v5/decisions/<run_id>_execution_decision.lock
"""

import json
from pathlib import Path
from typing import Dict, Any, Optional

from backend.autonomy_v5.schema import utc_now_compact


def ensure_directories(project_root: Path) -> Path:
    """
    출력 디렉토리 생성
    
    Args:
        project_root: 프로젝트 루트 경로
    
    Returns:
        Path: decisions_dir
    """
    decisions_dir = project_root / "backend" / "output" / "autonomy_v5" / "decisions"
    decisions_dir.mkdir(parents=True, exist_ok=True)
    
    return decisions_dir


def save_execution_decision(
    execution_decision: Dict[str, Any],
    project_root: Path,
    force: bool = False
) -> tuple[Optional[Path], Optional[str]]:
    """
    ExecutionDecisionV5 저장 + Lock 생성
    
    Args:
        execution_decision: ExecutionDecisionV5 데이터
        project_root: 프로젝트 루트 경로
        force: 기존 lock이 있어도 덮어쓰기 허용
    
    Returns:
        Tuple[Optional[Path], Optional[str]]: (decision_path, error_message)
    """
    decisions_dir = ensure_directories(project_root)
    
    run_id = execution_decision["run_id"]
    decision_path = decisions_dir / f"{run_id}_execution_decision.json"
    lock_path = decisions_dir / f"{run_id}_execution_decision.lock"
    
    # Lock 존재 확인
    if lock_path.exists() and not force:
        return None, "DECISION_ALREADY_FROZEN"
    
    # --force 시 백업
    if force and decision_path.exists():
        backup_path = decisions_dir / f"{run_id}_execution_decision.json.bak.{utc_now_compact()}"
        try:
            decision_path.rename(backup_path)
        except Exception as e:
            return None, f"Failed to backup decision: {str(e)}"
    
    # ExecutionDecision 저장 (utf-8-sig for PowerShell compatibility)
    try:
        with open(decision_path, "w", encoding="utf-8-sig") as f:
            json.dump(execution_decision, f, ensure_ascii=False, indent=2)
    except Exception as e:
        return None, f"Failed to save decision: {str(e)}"
    
    # Lock 생성
    lock_data = {
        "run_id": run_id,
        "decision_path": str(decision_path.resolve()),
        "frozen_at": execution_decision["created_at"]
    }
    
    try:
        with open(lock_path, "w", encoding="utf-8") as f:
            json.dump(lock_data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        return None, f"Failed to save lock: {str(e)}"
    
    return decision_path, None

