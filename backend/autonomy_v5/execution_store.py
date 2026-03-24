"""
v5-Step4: Execution Result 저장 + Lock 관리

저장 위치:
- execution_result: backend/output/autonomy_v5/executions/<run_id>_execution_result.json
- execution_log: backend/output/autonomy_v5/executions/<run_id>_execution_log.txt
- lock: backend/output/autonomy_v5/executions/<run_id>_execution_result.lock
"""

import json
from pathlib import Path
from typing import Dict, Any, Optional


def ensure_directories(project_root: Path) -> Path:
    """
    출력 디렉토리 생성
    
    Args:
        project_root: 프로젝트 루트 경로
    
    Returns:
        Path: executions_dir
    """
    executions_dir = project_root / "backend" / "output" / "autonomy_v5" / "executions"
    executions_dir.mkdir(parents=True, exist_ok=True)
    
    return executions_dir


def save_execution_result(
    execution_result: Dict[str, Any],
    project_root: Path
) -> tuple[Optional[Path], Optional[str]]:
    """
    ExecutionResultV5 저장 + Lock 생성
    
    Args:
        execution_result: ExecutionResultV5 데이터
        project_root: 프로젝트 루트 경로
    
    Returns:
        Tuple[Optional[Path], Optional[str]]: (execution_result_path, error_message)
    
    Note:
        --force 옵션 없음 (실행은 재현 불가하므로 재실행 차단)
    """
    executions_dir = ensure_directories(project_root)
    
    run_id = execution_result["run_id"]
    execution_result_path = executions_dir / f"{run_id}_execution_result.json"
    lock_path = executions_dir / f"{run_id}_execution_result.lock"
    
    # Lock 존재 확인 (--force 없음)
    if lock_path.exists():
        return None, "EXECUTION_ALREADY_COMPLETED"
    
    # ExecutionResult 저장 (utf-8-sig for PowerShell compatibility)
    try:
        with open(execution_result_path, "w", encoding="utf-8-sig") as f:
            json.dump(execution_result, f, ensure_ascii=False, indent=2)
    except Exception as e:
        return None, f"Failed to save execution result: {str(e)}"
    
    # Lock 생성
    lock_data = {
        "run_id": run_id,
        "execution_result_path": str(execution_result_path.resolve()),
        "completed_at": execution_result["finished_at"]
    }
    
    try:
        with open(lock_path, "w", encoding="utf-8") as f:
            json.dump(lock_data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        return None, f"Failed to save lock: {str(e)}"
    
    return execution_result_path, None

