"""
v5 Stop Condition Gate (P2)

기능:
- 자율 실행 모드: APPROVAL / CONDITIONAL / AUTO
- 중단 조건 평가 결과를 manifest.stop_conditions[]에 누적 기록
"""

from typing import Dict, Any, Optional, List
from datetime import datetime
from pathlib import Path

from backend.utils.run_manager import load_run_manifest, _atomic_write_json, get_run_dir


class ExecutionMode(str):
    """자율 실행 모드"""
    APPROVAL = "APPROVAL"  # 수동 승인 필요
    CONDITIONAL = "CONDITIONAL"  # 조건부 자동 실행
    AUTO = "AUTO"  # 완전 자동 실행


def evaluate_stop_conditions(
    run_id: str,
    execution_result: Dict[str, Any],
    goal_definition: Dict[str, Any],
    base_dir: Optional[Path] = None
) -> List[Dict[str, Any]]:
    """
    중단 조건 평가
    
    Args:
        run_id: 실행 ID
        execution_result: ExecutionResultV5 데이터
        goal_definition: GoalDefinitionV5 데이터
        base_dir: 기본 디렉토리
    
    Returns:
        List[Dict]: 중단 조건 평가 결과 리스트
    """
    stop_conditions = []
    
    # GoalDefinition에서 중단 조건 가져오기
    operational_constraints = goal_definition.get("operational_constraints", {})
    max_cost = operational_constraints.get("max_cost_usd", 0.0)
    max_time = operational_constraints.get("max_time_sec", 0.0)
    max_failures = operational_constraints.get("max_failures", 0)
    max_retries = operational_constraints.get("max_retries", 0)
    
    # ExecutionResult에서 실제 값 가져오기
    execution_summary = execution_result.get("execution_summary", {})
    constraint_monitoring = execution_result.get("constraint_monitoring", {})
    
    actual_cost = execution_summary.get("total_cost_usd", 0.0)
    actual_time = execution_summary.get("total_time_sec", 0.0)
    executed_steps = execution_summary.get("steps_executed", 0)
    violations = constraint_monitoring.get("violations", [])
    aborted = constraint_monitoring.get("aborted", False)
    
    # 비용 초과 확인
    if max_cost > 0 and actual_cost > max_cost:
        stop_conditions.append({
            "condition_type": "COST_EXCEEDED",
            "threshold": max_cost,
            "actual": actual_cost,
            "evaluated_at": datetime.now().isoformat()
        })
    
    # 시간 초과 확인
    if max_time > 0 and actual_time > max_time:
        stop_conditions.append({
            "condition_type": "TIME_EXCEEDED",
            "threshold": max_time,
            "actual": actual_time,
            "evaluated_at": datetime.now().isoformat()
        })
    
    # 실패 횟수 초과 확인
    if max_failures > 0 and len(violations) > max_failures:
        stop_conditions.append({
            "condition_type": "FAILURES_EXCEEDED",
            "threshold": max_failures,
            "actual": len(violations),
            "evaluated_at": datetime.now().isoformat()
        })
    
    # 중단됨 확인
    if aborted:
        stop_conditions.append({
            "condition_type": "ABORTED",
            "reason": "Execution was aborted due to constraint violation",
            "evaluated_at": datetime.now().isoformat()
        })
    
    return stop_conditions


def record_stop_conditions(
    run_id: str,
    stop_conditions: List[Dict[str, Any]],
    base_dir: Optional[Path] = None
) -> None:
    """
    manifest.stop_conditions[]에 중단 조건 평가 결과 누적 기록
    
    Args:
        run_id: 실행 ID
        stop_conditions: 중단 조건 평가 결과 리스트
        base_dir: 기본 디렉토리
    """
    manifest = load_run_manifest(run_id, base_dir)
    if manifest is None:
        return
    
    # stop_conditions 필드 초기화 (없으면)
    if "stop_conditions" not in manifest:
        manifest["stop_conditions"] = []
    
    # 기존 stop_conditions에 추가
    manifest["stop_conditions"].extend(stop_conditions)
    
    manifest["last_updated"] = datetime.now().isoformat()
    
    run_dir = get_run_dir(run_id, base_dir)
    manifest_path = run_dir / "manifest.json"
    _atomic_write_json(manifest_path, manifest)

