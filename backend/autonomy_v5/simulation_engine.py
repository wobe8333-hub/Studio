"""
v5-Step2: Simulation Engine

기능:
- PlanDraftV5를 기반으로 Simulation Report 생성
- 비용/시간/제약 시뮬레이션
- 실제 실행 금지
"""

from pathlib import Path
from typing import Dict, Any

from backend.autonomy_v5.schema import utc_now_iso


def create_simulation_report(
    run_id: str,
    plan_draft: Dict[str, Any],
    goal_path: Path,
    checkpoint_path: Path
) -> Dict[str, Any]:
    """
    Simulation Report 생성
    
    Args:
        run_id: 실행 ID
        plan_draft: PlanDraftV5 데이터
        goal_path: goal 파일 경로
        checkpoint_path: checkpoint 파일 경로
    
    Returns:
        Dict: Simulation Report JSON 데이터
    """
    created_at = utc_now_iso()
    simulation_id = f"simulation_v5_step2:{run_id}:{created_at}"
    
    # inputs
    inputs = {
        "goal_path": str(goal_path.resolve().as_posix()),
        "checkpoint_path": str(checkpoint_path.resolve().as_posix())
    }
    
    # simulation_summary
    planned_steps = plan_draft.get("planned_steps", [])
    aggregates = plan_draft.get("aggregates", {})
    constraint_evaluation = plan_draft.get("constraint_evaluation", {})
    
    simulation_summary = {
        "steps_simulated": len(planned_steps),
        "total_estimated_cost_usd": aggregates.get("total_estimated_cost_usd", 0.0),
        "total_estimated_time_sec": aggregates.get("total_estimated_time_sec", 0.0),
        "constraint_passed": constraint_evaluation.get("is_safe", False)
    }
    
    # notes
    notes = {
        "warnings": []
    }
    
    if not constraint_evaluation.get("is_safe", False):
        violations = constraint_evaluation.get("violations", [])
        notes["warnings"].extend([f"Constraint violation: {v}" for v in violations])
    
    return {
        "run_id": run_id,
        "simulation_id": simulation_id,
        "created_at": created_at,
        "inputs": inputs,
        "simulation_summary": simulation_summary,
        "notes": notes,
        "version": "v5_step2"
    }

