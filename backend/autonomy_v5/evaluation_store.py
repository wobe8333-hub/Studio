"""
v5-Step5: Post Execution Evaluation + Learning Snapshot 저장 + Lock 관리

저장 위치:
- evaluation: backend/output/autonomy_v5/evaluations/<run_id>_post_execution_evaluation.json
- learning: backend/output/autonomy_v5/learning/<run_id>_learning_snapshot.json
- lock: backend/output/autonomy_v5/evaluations/<run_id>_post_execution_evaluation.lock
"""

import json
from pathlib import Path
from typing import Dict, Any, Optional

from backend.autonomy_v5.schema import utc_now_compact


def ensure_directories(project_root: Path) -> tuple[Path, Path]:
    """
    출력 디렉토리 생성
    
    Args:
        project_root: 프로젝트 루트 경로
    
    Returns:
        Tuple[Path, Path]: (evaluations_dir, learning_dir)
    """
    evaluations_dir = project_root / "backend" / "output" / "autonomy_v5" / "evaluations"
    learning_dir = project_root / "backend" / "output" / "autonomy_v5" / "learning"
    
    evaluations_dir.mkdir(parents=True, exist_ok=True)
    learning_dir.mkdir(parents=True, exist_ok=True)
    
    return evaluations_dir, learning_dir


def save_post_execution_evaluation(
    evaluation: Dict[str, Any],
    project_root: Path,
    force: bool = False
) -> tuple[Optional[Path], Optional[str]]:
    """
    PostExecutionEvaluationV5 저장 + Lock 생성
    
    Args:
        evaluation: PostExecutionEvaluationV5 데이터
        project_root: 프로젝트 루트 경로
        force: 기존 lock이 있어도 덮어쓰기 허용
    
    Returns:
        Tuple[Optional[Path], Optional[str]]: (evaluation_path, error_message)
    """
    evaluations_dir, _ = ensure_directories(project_root)
    
    run_id = evaluation["run_id"]
    evaluation_path = evaluations_dir / f"{run_id}_post_execution_evaluation.json"
    lock_path = evaluations_dir / f"{run_id}_post_execution_evaluation.lock"
    
    # Lock 존재 확인
    if lock_path.exists() and not force:
        return None, "EVALUATION_ALREADY_FROZEN"
    
    # --force 시 백업
    if force and evaluation_path.exists():
        backup_path = evaluations_dir / f"{run_id}_post_execution_evaluation.json.bak.{utc_now_compact()}"
        try:
            evaluation_path.rename(backup_path)
        except Exception as e:
            return None, f"Failed to backup evaluation: {str(e)}"
    
    # Evaluation 저장 (utf-8-sig for PowerShell compatibility)
    try:
        with open(evaluation_path, "w", encoding="utf-8-sig") as f:
            json.dump(evaluation, f, ensure_ascii=False, indent=2)
    except Exception as e:
        return None, f"Failed to save evaluation: {str(e)}"
    
    # Lock 생성
    lock_data = {
        "run_id": run_id,
        "evaluation_path": str(evaluation_path.resolve()),
        "frozen_at": evaluation["created_at"]
    }
    
    try:
        with open(lock_path, "w", encoding="utf-8") as f:
            json.dump(lock_data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        return None, f"Failed to save lock: {str(e)}"
    
    return evaluation_path, None


def save_learning_snapshot(
    learning_snapshot: Dict[str, Any],
    project_root: Path,
    force: bool = False
) -> tuple[Optional[Path], Optional[str]]:
    """
    LearningSnapshotV5 저장
    
    Args:
        learning_snapshot: LearningSnapshotV5 데이터
        project_root: 프로젝트 루트 경로
        force: 기존 파일이 있어도 덮어쓰기 허용
    
    Returns:
        Tuple[Optional[Path], Optional[str]]: (learning_path, error_message)
    """
    _, learning_dir = ensure_directories(project_root)
    
    run_id = learning_snapshot["run_id"]
    learning_path = learning_dir / f"{run_id}_learning_snapshot.json"
    
    # --force 시 백업
    if force and learning_path.exists():
        backup_path = learning_dir / f"{run_id}_learning_snapshot.json.bak.{utc_now_compact()}"
        try:
            learning_path.rename(backup_path)
        except Exception as e:
            return None, f"Failed to backup learning snapshot: {str(e)}"
    
    # LearningSnapshot 저장 (utf-8-sig for PowerShell compatibility)
    try:
        with open(learning_path, "w", encoding="utf-8-sig") as f:
            json.dump(learning_snapshot, f, ensure_ascii=False, indent=2)
    except Exception as e:
        return None, f"Failed to save learning snapshot: {str(e)}"
    
    return learning_path, None

