"""
v5-Step5: Evaluation Engine

기능:
- 실행 결과를 평가
- 성공/실패 원인 분석
- 학습 데이터 생성
"""

import json
import hashlib
from pathlib import Path
from typing import Dict, Any, Optional, List

from backend.autonomy_v5.schema import utc_now_iso


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


def create_post_execution_evaluation(
    run_id: str,
    execution_result: Dict[str, Any],
    plan_draft: Dict[str, Any],
    simulation_report: Dict[str, Any],
    execution_result_path: Path,
    execution_log_path: Path,
    plan_draft_path: Path,
    simulation_report_path: Path,
    goal_path: Path,
    checkpoint_path: Path
) -> Dict[str, Any]:
    """
    PostExecutionEvaluationV5 생성
    
    Args:
        run_id: 실행 ID
        execution_result: ExecutionResultV5 데이터
        plan_draft: PlanDraftV5 데이터
        simulation_report: Simulation Report 데이터
        execution_result_path: execution_result 파일 경로
        execution_log_path: execution_log 파일 경로
        plan_draft_path: plan_draft 파일 경로
        simulation_report_path: simulation_report 파일 경로
        goal_path: goal 파일 경로
        checkpoint_path: checkpoint 파일 경로
    
    Returns:
        Dict: PostExecutionEvaluationV5 JSON 데이터
    """
    created_at = utc_now_iso()
    evaluation_id = f"evaluation_v5_step5:{run_id}:{created_at}"
    
    # inputs
    inputs = {
        "execution_result_path": str(execution_result_path.resolve().as_posix()),
        "execution_log_path": str(execution_log_path.resolve().as_posix()),
        "plan_draft_path": str(plan_draft_path.resolve().as_posix()),
        "simulation_report_path": str(simulation_report_path.resolve().as_posix()),
        "goal_path": str(goal_path.resolve().as_posix()),
        "checkpoint_path": str(checkpoint_path.resolve().as_posix())
    }
    
    # evaluation_summary
    planned_steps = plan_draft.get("planned_steps", [])
    execution_summary = execution_result.get("execution_summary", {})
    constraint_monitoring = execution_result.get("constraint_monitoring", {})
    
    expected_steps = len(planned_steps)
    executed_steps = execution_summary.get("steps_executed", 0)
    execution_status = execution_summary.get("status", "UNKNOWN")
    constraint_violations = constraint_monitoring.get("violations", [])
    
    evaluation_summary = {
        "expected_steps": expected_steps,
        "executed_steps": executed_steps,
        "execution_status": execution_status,
        "constraint_violations": constraint_violations
    }
    
    # delta_analysis
    aggregates = plan_draft.get("aggregates", {})
    estimated_cost = aggregates.get("total_estimated_cost_usd", 0.0)
    estimated_time = aggregates.get("total_estimated_time_sec", 0.0)
    
    actual_cost = execution_summary.get("total_cost_usd", 0.0)
    actual_time = execution_summary.get("total_time_sec", 0.0)
    
    delta_analysis = {
        "estimated_cost_usd": estimated_cost,
        "actual_cost_usd": actual_cost,
        "estimated_time_sec": estimated_time,
        "actual_time_sec": actual_time
    }
    
    # insights
    what_worked = []
    what_failed = []
    risk_factors = []
    
    if execution_status == "SUCCESS":
        what_worked.append("All planned steps executed successfully")
        if not constraint_violations:
            what_worked.append("No constraint violations")
    elif execution_status == "PARTIAL_SUCCESS":
        what_worked.append(f"Partial execution: {executed_steps}/{expected_steps} steps completed")
        what_failed.append(f"Incomplete execution: {expected_steps - executed_steps} steps not executed")
    else:
        what_failed.append("Execution failed or aborted")
    
    if constraint_violations:
        risk_factors.extend(constraint_violations)
    
    if abs(actual_cost - estimated_cost) > estimated_cost * 0.1:  # 10% 이상 차이
        risk_factors.append(f"Cost estimation deviation: estimated={estimated_cost}, actual={actual_cost}")
    
    if abs(actual_time - estimated_time) > estimated_time * 0.1:  # 10% 이상 차이
        risk_factors.append(f"Time estimation deviation: estimated={estimated_time}, actual={actual_time}")
    
    insights = {
        "what_worked": what_worked,
        "what_failed": what_failed,
        "risk_factors": risk_factors
    }
    
    # learning_tags
    learning_tags = []
    
    if abs(actual_cost - estimated_cost) <= estimated_cost * 0.05:  # 5% 이내
        learning_tags.append("COST_ESTIMATION_ACCURATE")
    
    if abs(actual_time - estimated_time) > estimated_time * 0.1:
        learning_tags.append("TIME_ESTIMATION_DEVIATION")
    
    # 모든 단계가 SIMULATION_ONLY인지 확인
    all_simulation = all(
        step.get("execution_type") == "SIMULATION_ONLY"
        for step in planned_steps
    )
    if all_simulation:
        learning_tags.append("SIMULATION_ONLY_EXECUTION")
    
    if not constraint_violations:
        learning_tags.append("CONSTRAINT_RESPECTED")
    
    return {
        "run_id": run_id,
        "evaluation_id": evaluation_id,
        "created_at": created_at,
        "inputs": inputs,
        "evaluation_summary": evaluation_summary,
        "delta_analysis": delta_analysis,
        "insights": insights,
        "learning_tags": learning_tags,
        "version": "v5_step5",
        "state": "EVALUATION_FROZEN"
    }


def create_learning_snapshot(
    evaluation: Dict[str, Any]
) -> Dict[str, Any]:
    """
    LearningSnapshotV5 생성
    
    Args:
        evaluation: PostExecutionEvaluationV5 데이터
    
    Returns:
        Dict: LearningSnapshotV5 JSON 데이터
    """
    run_id = evaluation["run_id"]
    evaluation_id = evaluation["evaluation_id"]
    created_at = evaluation["created_at"]
    
    # abstracted_learnings
    learning_tags = evaluation.get("learning_tags", [])
    insights = evaluation.get("insights", {})
    
    abstracted_learnings = []
    
    # learning_tags 기반 학습 항목
    for tag in learning_tags:
        if tag == "COST_ESTIMATION_ACCURATE":
            abstracted_learnings.append({
                "tag": tag,
                "description": "Cost estimation was accurate within 5% margin"
            })
        elif tag == "TIME_ESTIMATION_DEVIATION":
            abstracted_learnings.append({
                "tag": tag,
                "description": "Time estimation showed significant deviation (>10%)"
            })
        elif tag == "SIMULATION_ONLY_EXECUTION":
            abstracted_learnings.append({
                "tag": tag,
                "description": "All execution steps were simulation-only (no actual LLM/Render calls)"
            })
        elif tag == "CONSTRAINT_RESPECTED":
            abstracted_learnings.append({
                "tag": tag,
                "description": "All operational constraints were respected during execution"
            })
    
    # insights 기반 학습 항목
    what_worked = insights.get("what_worked", [])
    what_failed = insights.get("what_failed", [])
    risk_factors = insights.get("risk_factors", [])
    
    for item in what_worked:
        abstracted_learnings.append({
            "tag": "SUCCESS_PATTERN",
            "description": item
        })
    
    for item in what_failed:
        abstracted_learnings.append({
            "tag": "FAILURE_PATTERN",
            "description": item
        })
    
    for item in risk_factors:
        abstracted_learnings.append({
            "tag": "RISK_FACTOR",
            "description": item
        })
    
    return {
        "run_id": run_id,
        "source_evaluation_id": evaluation_id,
        "created_at": created_at,
        "abstracted_learnings": abstracted_learnings,
        "reference_only": True,
        "version": "v5_step5"
    }


def generate_post_execution_evaluation(
    run_id: str,
    project_root: Optional[Path] = None
) -> tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]], Optional[str]]:
    """
    PostExecutionEvaluationV5 + LearningSnapshotV5 생성 (전체 프로세스)
    
    Args:
        run_id: 실행 ID
        project_root: 프로젝트 루트 경로
    
    Returns:
        Tuple[Optional[Dict], Optional[Dict], Optional[str]]: (evaluation, learning_snapshot, error_message)
    """
    if project_root is None:
        project_root = Path.cwd()
    
    # v5 Execution Result 검증
    execution_result_path = project_root / "backend" / "output" / "autonomy_v5" / "executions" / f"{run_id}_execution_result.json"
    execution_result_lock_path = project_root / "backend" / "output" / "autonomy_v5" / "executions" / f"{run_id}_execution_result.lock"
    
    if not execution_result_path.exists():
        return None, None, f"v5 Execution Result not found: {execution_result_path.resolve()}"
    
    if not execution_result_lock_path.exists():
        return None, None, f"v5 Execution Result lock not found: {execution_result_lock_path.resolve()}"
    
    execution_result = load_json_safe(execution_result_path)
    if execution_result is None:
        return None, None, f"Failed to load execution result: {execution_result_path.resolve()}"
    
    # v5 Execution Log 검증
    execution_log_path = project_root / "backend" / "output" / "autonomy_v5" / "executions" / f"{run_id}_execution_log.txt"
    
    if not execution_log_path.exists():
        return None, None, f"v5 Execution Log not found: {execution_log_path.resolve()}"
    
    # v5 PlanDraft 검증
    plan_draft_path = project_root / "backend" / "output" / "autonomy_v5" / "plans" / f"{run_id}_plan_draft.json"
    
    if not plan_draft_path.exists():
        return None, None, f"v5 PlanDraft not found: {plan_draft_path.resolve()}"
    
    plan_draft = load_json_safe(plan_draft_path)
    if plan_draft is None:
        return None, None, f"Failed to load plan draft: {plan_draft_path.resolve()}"
    
    # v5 Simulation Report 검증
    simulation_report_path = project_root / "backend" / "output" / "autonomy_v5" / "reports" / f"{run_id}_simulation_report.json"
    
    if not simulation_report_path.exists():
        return None, None, f"v5 Simulation Report not found: {simulation_report_path.resolve()}"
    
    simulation_report = load_json_safe(simulation_report_path)
    if simulation_report is None:
        return None, None, f"Failed to load simulation report: {simulation_report_path.resolve()}"
    
    # v5 GoalDefinition 검증
    goal_path = project_root / "backend" / "output" / "autonomy_v5" / "goals" / f"{run_id}.json"
    
    if not goal_path.exists():
        return None, None, f"v5 GoalDefinition not found: {goal_path.resolve()}"
    
    # v4 Checkpoint 검증
    checkpoint_path = project_root / "backend" / "output" / "evolution_v4" / "checkpoints" / f"{run_id}.json"
    
    if not checkpoint_path.exists():
        return None, None, f"v4 Checkpoint not found: {checkpoint_path.resolve()}"
    
    # PostExecutionEvaluation 생성
    evaluation = create_post_execution_evaluation(
        run_id, execution_result, plan_draft, simulation_report,
        execution_result_path, execution_log_path, plan_draft_path,
        simulation_report_path, goal_path, checkpoint_path
    )
    
    # LearningSnapshot 생성
    learning_snapshot = create_learning_snapshot(evaluation)
    
    return evaluation, learning_snapshot, None


