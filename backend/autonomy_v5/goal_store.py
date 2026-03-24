"""
v5-Step1: Goal 저장 + Lock 관리

저장 위치:
- goal: backend/output/autonomy_v5/goals/<run_id>.json
- lock: backend/output/autonomy_v5/goals/<run_id>.lock
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
        Path: goals_dir
    """
    goals_dir = project_root / "backend" / "output" / "autonomy_v5" / "goals"
    goals_dir.mkdir(parents=True, exist_ok=True)
    
    return goals_dir


def save_goal_definition(
    goal_definition: Dict[str, Any],
    project_root: Path,
    force: bool = False
) -> tuple[Optional[Path], Optional[str]]:
    """
    GoalDefinitionV5 저장 + Lock 생성
    
    Args:
        goal_definition: GoalDefinitionV5 데이터
        project_root: 프로젝트 루트 경로
        force: 기존 lock이 있어도 덮어쓰기 허용
    
    Returns:
        Tuple[Optional[Path], Optional[str]]: (goal_path, error_message)
    """
    goals_dir = ensure_directories(project_root)
    
    run_id = goal_definition["run_id"]
    goal_path = goals_dir / f"{run_id}.json"
    lock_path = goals_dir / f"{run_id}.lock"
    
    # Lock 존재 확인
    if lock_path.exists() and not force:
        return None, "GOAL_ALREADY_FROZEN"
    
    # --force 시 백업
    if force and goal_path.exists():
        backup_path = goals_dir / f"{run_id}.json.bak.{utc_now_compact()}"
        try:
            goal_path.rename(backup_path)
        except Exception as e:
            return None, f"Failed to backup goal: {str(e)}"
    
    # Goal 저장 (utf-8-sig for PowerShell compatibility)
    try:
        with open(goal_path, "w", encoding="utf-8-sig") as f:
            json.dump(goal_definition, f, ensure_ascii=False, indent=2)
    except Exception as e:
        return None, f"Failed to save goal: {str(e)}"
    
    # Lock 생성
    lock_data = {
        "run_id": run_id,
        "goal_path": str(goal_path.resolve()),
        "frozen_at": goal_definition["created_at"]
    }
    
    try:
        with open(lock_path, "w", encoding="utf-8") as f:
            json.dump(lock_data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        return None, f"Failed to save lock: {str(e)}"
    
    return goal_path, None

