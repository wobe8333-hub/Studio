"""
v5-Step4: Execution Engine

기능:
- 승인된 PlanDraft를 기반으로 실제 실행 수행
- 제약 하에서만 실행
- 실행 결과 기록
"""

import json
import hashlib
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone

from backend.autonomy_v5.schema import utc_now_iso
from backend.autonomy_v5.constraint_guard import check_constraints


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


def execute_plan_draft(
    run_id: str,
    goal_definition: Dict[str, Any],
    plan_draft: Dict[str, Any],
    execution_log_path: Path
) -> tuple[Dict[str, Any], List[str]]:
    """
    PlanDraft 실행
    
    Args:
        run_id: 실행 ID
        goal_definition: GoalDefinitionV5 데이터
        plan_draft: PlanDraftV5 데이터
        execution_log_path: 실행 로그 파일 경로
    
    Returns:
        Tuple[Dict, List[str]]: (execution_summary, generated_outputs, log_lines)
    """
    log_lines = []
    log_lines.append(f"[{utc_now_iso()}] Execution started for run_id={run_id}")
    
    planned_steps = plan_draft.get("planned_steps", [])
    total_cost_usd = 0.0
    total_time_sec = 0.0
    executed_steps = 0
    generated_outputs = []
    violations = []
    aborted = False
    
    # 각 단계 실행
    for step in planned_steps:
        step_no = step.get("step_no", 0)
        description = step.get("description", "")
        execution_type = step.get("execution_type", "")
        estimated_cost = step.get("estimated_cost_usd", 0.0)
        estimated_time = step.get("estimated_time_sec", 0.0)
        
        log_lines.append(f"[{utc_now_iso()}] Executing step {step_no}: {description}")
        
        # 제약 확인
        is_safe, step_violations = check_constraints(
            goal_definition, total_cost_usd, total_time_sec, executed_steps
        )
        
        if not is_safe:
            violations.extend(step_violations)
            aborted = True
            log_lines.append(f"[{utc_now_iso()}] ABORTED: Constraint violations detected: {step_violations}")
            break
        
        # 실행 타입 확인 (SIMULATION_ONLY는 실제 실행하지 않음)
        if execution_type == "SIMULATION_ONLY":
            log_lines.append(f"[{utc_now_iso()}] Step {step_no} is SIMULATION_ONLY, skipping actual execution")
            # 시뮬레이션 단계는 실제 실행하지 않음
            total_cost_usd += 0.0  # 시뮬레이션은 비용 없음
            total_time_sec += estimated_time  # 시간은 시뮬레이션 값 사용
        else:
            # 실제 실행 단계 (현재는 구현하지 않음, 제약 하에서만 허용)
            log_lines.append(f"[{utc_now_iso()}] Step {step_no} execution type: {execution_type}")
            log_lines.append(f"[{utc_now_iso()}] WARNING: Actual execution not implemented in this version")
            total_cost_usd += estimated_cost
            total_time_sec += estimated_time
        
        executed_steps += 1
        log_lines.append(f"[{utc_now_iso()}] Step {step_no} completed")
    
    # 실행 상태 결정
    if aborted:
        status = "FAILED"
    elif executed_steps == len(planned_steps):
        status = "SUCCESS"
    elif executed_steps > 0:
        status = "PARTIAL_SUCCESS"
    else:
        status = "FAILED"
    
    execution_summary = {
        "steps_executed": executed_steps,
        "total_cost_usd": total_cost_usd,
        "total_time_sec": total_time_sec,
        "status": status
    }
    
    log_lines.append(f"[{utc_now_iso()}] Execution completed: status={status}, steps={executed_steps}/{len(planned_steps)}")
    
    # 로그 파일 저장
    try:
        with open(execution_log_path, "w", encoding="utf-8") as f:
            f.write("\n".join(log_lines))
    except Exception as e:
        log_lines.append(f"[{utc_now_iso()}] ERROR: Failed to write log file: {str(e)}")
    
    constraint_monitoring = {
        "violations": violations,
        "aborted": aborted
    }
    
    return execution_summary, constraint_monitoring, generated_outputs, log_lines


def create_execution_result(
    run_id: str,
    goal_path: Path,
    plan_draft_path: Path,
    decision_path: Path,
    checkpoint_path: Path,
    execution_summary: Dict[str, Any],
    constraint_monitoring: Dict[str, Any],
    generated_outputs: List[str],
    started_at: str,
    finished_at: str
) -> Dict[str, Any]:
    """
    ExecutionResultV5 생성
    
    Args:
        run_id: 실행 ID
        goal_path: goal 파일 경로
        plan_draft_path: plan_draft 파일 경로
        decision_path: decision 파일 경로
        checkpoint_path: checkpoint 파일 경로
        execution_summary: 실행 요약
        constraint_monitoring: 제약 모니터링 결과
        generated_outputs: 생성된 출력 파일 목록
        started_at: 시작 시각
        finished_at: 종료 시각
    
    Returns:
        Dict: ExecutionResultV5 JSON 데이터
    """
    execution_id = f"execution_v5_step4:{run_id}:{started_at}"
    
    # inputs
    inputs = {
        "goal_path": str(goal_path.resolve().as_posix()),
        "plan_draft_path": str(plan_draft_path.resolve().as_posix()),
        "decision_path": str(decision_path.resolve().as_posix()),
        "checkpoint_path": str(checkpoint_path.resolve().as_posix())
    }
    
    # hashes
    hashes = {
        "goal_sha256": sha256_file(goal_path),
        "plan_draft_sha256": sha256_file(plan_draft_path),
        "decision_sha256": sha256_file(decision_path),
        "checkpoint_sha256": sha256_file(checkpoint_path)
    }
    
    # artifacts
    artifacts = {
        "generated_outputs": generated_outputs
    }
    
    return {
        "run_id": run_id,
        "execution_id": execution_id,
        "started_at": started_at,
        "finished_at": finished_at,
        "inputs": inputs,
        "execution_summary": execution_summary,
        "constraint_monitoring": constraint_monitoring,
        "artifacts": artifacts,
        "hashes": hashes,
        "version": "v5_step4",
        "state": "EXECUTION_COMPLETED"
    }


def generate_execution_result(
    run_id: str,
    project_root: Optional[Path] = None
) -> tuple[Optional[Dict[str, Any]], Optional[str]]:
    """
    ExecutionResultV5 생성 (전체 프로세스)
    
    Args:
        run_id: 실행 ID
        project_root: 프로젝트 루트 경로
    
    Returns:
        Tuple[Optional[Dict], Optional[str]]: (execution_result, error_message)
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
    
    # v5 PlanDraft 검증
    plan_draft_path = project_root / "backend" / "output" / "autonomy_v5" / "plans" / f"{run_id}_plan_draft.json"
    plan_draft_lock_path = project_root / "backend" / "output" / "autonomy_v5" / "plans" / f"{run_id}_plan_draft.lock"
    
    if not plan_draft_path.exists():
        return None, f"v5 PlanDraft not found: {plan_draft_path.resolve()}"
    
    if not plan_draft_lock_path.exists():
        return None, f"v5 PlanDraft lock not found: {plan_draft_lock_path.resolve()}"
    
    plan_draft = load_json_safe(plan_draft_path)
    if plan_draft is None:
        return None, f"Failed to load plan draft: {plan_draft_path.resolve()}"
    
    # v5 Execution Decision 검증
    decision_path = project_root / "backend" / "output" / "autonomy_v5" / "decisions" / f"{run_id}_execution_decision.json"
    decision_lock_path = project_root / "backend" / "output" / "autonomy_v5" / "decisions" / f"{run_id}_execution_decision.lock"
    
    if not decision_path.exists():
        return None, f"v5 Execution Decision not found: {decision_path.resolve()}"
    
    if not decision_lock_path.exists():
        return None, f"v5 Decision lock not found: {decision_lock_path.resolve()}"
    
    execution_decision = load_json_safe(decision_path)
    if execution_decision is None:
        return None, f"Failed to load execution decision: {decision_path.resolve()}"
    
    # Decision이 EXECUTION_APPROVED인지 확인
    decision = execution_decision.get("decision")
    if decision != "EXECUTION_APPROVED":
        return None, f"Execution not approved: decision={decision} (expected: EXECUTION_APPROVED)"
    
    # v4 Checkpoint 검증
    checkpoint_path = project_root / "backend" / "output" / "evolution_v4" / "checkpoints" / f"{run_id}.json"
    checkpoint_lock_path = project_root / "backend" / "output" / "evolution_v4" / "checkpoints" / f"{run_id}.lock"
    
    if not checkpoint_path.exists():
        return None, f"v4 Checkpoint not found: {checkpoint_path.resolve()}"
    
    if not checkpoint_lock_path.exists():
        return None, f"v4 Checkpoint lock not found: {checkpoint_lock_path.resolve()}"
    
    # 실행 로그 경로
    executions_dir = project_root / "backend" / "output" / "autonomy_v5" / "executions"
    executions_dir.mkdir(parents=True, exist_ok=True)
    execution_log_path = executions_dir / f"{run_id}_execution_log.txt"
    
    # 실행 시작
    started_at = utc_now_iso()
    
    # PlanDraft 실행
    execution_summary, constraint_monitoring, generated_outputs, log_lines = execute_plan_draft(
        run_id, goal_definition, plan_draft, execution_log_path
    )
    
    # 실행 종료
    finished_at = utc_now_iso()
    
    # ExecutionResult 생성
    execution_result = create_execution_result(
        run_id, goal_path, plan_draft_path, decision_path, checkpoint_path,
        execution_summary, constraint_monitoring, generated_outputs,
        started_at, finished_at
    )
    
    return execution_result, None

