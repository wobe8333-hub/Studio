"""
v5-Step2: Plan Engine

기능:
- GoalDefinition과 Checkpoint를 참조하여 PlanDraftV5 생성
- 제약 평가 수행
- 실제 실행 금지
"""

import json
from pathlib import Path
from typing import Dict, Any, Optional, List

from backend.autonomy_v5.schema import utc_now_iso


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


def evaluate_constraints(
    goal_definition: Dict[str, Any],
    planned_steps: List[Dict[str, Any]],
    aggregates: Dict[str, Any]
) -> Dict[str, Any]:
    """
    제약 평가
    
    Args:
        goal_definition: GoalDefinitionV5 데이터
        planned_steps: 계획된 단계 리스트
        aggregates: 집계 값 (비용, 시간)
    
    Returns:
        Dict: 제약 평가 결과
    """
    violations = []
    
    # absolute_constraints 확인
    absolute_constraints = goal_definition.get("absolute_constraints", [])
    
    # planned_steps에서 제약 위반 확인
    for step in planned_steps:
        execution_type = step.get("execution_type", "")
        # SIMULATION_ONLY가 아니면 위반
        if execution_type != "SIMULATION_ONLY":
            violations.append(f"Step {step.get('step_no')}: execution_type is not SIMULATION_ONLY")
    
    # operational_constraints 확인
    operational_constraints = goal_definition.get("operational_constraints", {})
    max_cost_usd = operational_constraints.get("max_cost_usd", float("inf"))
    total_cost = aggregates.get("total_estimated_cost_usd", 0.0)
    
    if total_cost > max_cost_usd:
        violations.append(f"Total cost {total_cost} exceeds max_cost_usd {max_cost_usd}")
    
    # allowed_execution_scope 확인
    allowed_scope = operational_constraints.get("allowed_execution_scope", [])
    if "SIMULATION_ONLY" not in allowed_scope:
        violations.append("SIMULATION_ONLY not in allowed_execution_scope")
    
    is_safe = len(violations) == 0
    
    return {
        "violations": violations,
        "is_safe": is_safe
    }


def create_plan_draft(
    run_id: str,
    goal_definition: Dict[str, Any],
    checkpoint: Dict[str, Any]
) -> Dict[str, Any]:
    """
    PlanDraftV5 생성
    
    Args:
        run_id: 실행 ID
        goal_definition: GoalDefinitionV5 데이터
        checkpoint: CheckpointV4 데이터
    
    Returns:
        Dict: PlanDraftV5 JSON 데이터
    """
    created_at = utc_now_iso()
    plan_draft_id = f"plan_draft_v5_step2:{run_id}:{created_at}"
    
    goal_id = goal_definition.get("goal_id", "")
    absolute_constraints = goal_definition.get("absolute_constraints", [])
    operational_constraints = goal_definition.get("operational_constraints", {})
    
    # planned_steps 생성 (시뮬레이션 전용)
    planned_steps = [
        {
            "step_no": 1,
            "description": "KPI 평가 및 Baseline 비교 (SIMULATION)",
            "execution_type": "SIMULATION_ONLY",
            "estimated_cost_usd": 0.0,
            "estimated_time_sec": 5.0
        },
        {
            "step_no": 2,
            "description": "Policy 후보 생성 및 평가 (SIMULATION)",
            "execution_type": "SIMULATION_ONLY",
            "estimated_cost_usd": 0.0,
            "estimated_time_sec": 10.0
        },
        {
            "step_no": 3,
            "description": "제약 검증 및 안전성 확인 (SIMULATION)",
            "execution_type": "SIMULATION_ONLY",
            "estimated_cost_usd": 0.0,
            "estimated_time_sec": 3.0
        }
    ]
    
    # aggregates 계산
    total_estimated_cost_usd = sum(step.get("estimated_cost_usd", 0.0) for step in planned_steps)
    total_estimated_time_sec = sum(step.get("estimated_time_sec", 0.0) for step in planned_steps)
    
    aggregates = {
        "total_estimated_cost_usd": total_estimated_cost_usd,
        "total_estimated_time_sec": total_estimated_time_sec
    }
    
    # constraint_evaluation
    constraint_evaluation = evaluate_constraints(goal_definition, planned_steps, aggregates)
    
    return {
        "run_id": run_id,
        "plan_draft_id": plan_draft_id,
        "created_at": created_at,
        "goal_reference": goal_id,
        "constraints_reference": {
            "absolute": absolute_constraints,
            "operational": operational_constraints
        },
        "planned_steps": planned_steps,
        "aggregates": aggregates,
        "constraint_evaluation": constraint_evaluation,
        "version": "v5_step2",
        "state": "PLAN_DRAFT_SIMULATED"
    }


def generate_plan_draft(
    run_id: str,
    project_root: Optional[Path] = None
) -> tuple[Optional[Dict[str, Any]], Optional[str]]:
    """
    PlanDraftV5 생성 (전체 프로세스)
    
    Args:
        run_id: 실행 ID
        project_root: 프로젝트 루트 경로
    
    Returns:
        Tuple[Optional[Dict], Optional[str]]: (plan_draft, error_message)
    """
    if project_root is None:
        project_root = Path.cwd()
    
    # v5 GoalDefinition 검증
    goal_path = project_root / "backend" / "output" / "autonomy_v5" / "goals" / f"{run_id}.json"
    goal_lock_path = project_root / "backend" / "output" / "autonomy_v5" / "goals" / f"{run_id}.lock"
    
    if not goal_path.exists():
        return None, f"v5 GoalDefinition not found: {goal_path.resolve()}"
    
    if not goal_lock_path.exists():
        return None, f"v5 Goal lock not found: {goal_lock_path.resolve()}"
    
    goal_definition = load_json_safe(goal_path)
    if goal_definition is None:
        return None, f"Failed to load goal definition: {goal_path.resolve()}"
    
    # v4 Checkpoint 검증
    checkpoint_path = project_root / "backend" / "output" / "evolution_v4" / "checkpoints" / f"{run_id}.json"
    checkpoint_lock_path = project_root / "backend" / "output" / "evolution_v4" / "checkpoints" / f"{run_id}.lock"
    
    if not checkpoint_path.exists():
        return None, f"v4 Checkpoint not found: {checkpoint_path.resolve()}"
    
    if not checkpoint_lock_path.exists():
        return None, f"v4 Checkpoint lock not found: {checkpoint_lock_path.resolve()}"
    
    checkpoint = load_json_safe(checkpoint_path)
    if checkpoint is None:
        return None, f"Failed to load checkpoint: {checkpoint_path.resolve()}"
    
    # PlanDraft 생성
    plan_draft = create_plan_draft(run_id, goal_definition, checkpoint)
    
    # 제약 위반 확인
    if not plan_draft.get("constraint_evaluation", {}).get("is_safe", False):
        violations = plan_draft.get("constraint_evaluation", {}).get("violations", [])
        return None, f"Constraint violations detected: {violations}"
    
    return plan_draft, None

