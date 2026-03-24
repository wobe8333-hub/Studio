"""
v5-Step3: Decision Engine

기능:
- 인간의 실행 승인/거부 결정을 기록
- 모든 입력 파일의 해시 기록
- 실제 실행 금지
"""

import json
import hashlib
from pathlib import Path
from typing import Dict, Any, Optional, Literal

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


def create_execution_decision(
    run_id: str,
    decision: Literal["EXECUTION_APPROVED", "EXECUTION_REJECTED"],
    operator_id: str,
    reason: str,
    goal_path: Path,
    plan_draft_path: Path,
    simulation_report_path: Path,
    checkpoint_path: Path
) -> Dict[str, Any]:
    """
    ExecutionDecisionV5 생성
    
    Args:
        run_id: 실행 ID
        decision: 결정 (EXECUTION_APPROVED 또는 EXECUTION_REJECTED)
        operator_id: 운영자 식별자
        reason: 결정 사유
        goal_path: goal 파일 경로
        plan_draft_path: plan_draft 파일 경로
        simulation_report_path: simulation_report 파일 경로
        checkpoint_path: checkpoint 파일 경로
    
    Returns:
        Dict: ExecutionDecisionV5 JSON 데이터
    """
    created_at = utc_now_iso()
    decision_id = f"execution_decision_v5_step3:{run_id}:{created_at}"
    
    # inputs
    inputs = {
        "goal_path": str(goal_path.resolve().as_posix()),
        "plan_draft_path": str(plan_draft_path.resolve().as_posix()),
        "simulation_report_path": str(simulation_report_path.resolve().as_posix()),
        "checkpoint_path": str(checkpoint_path.resolve().as_posix())
    }
    
    # hashes
    hashes = {
        "goal_sha256": sha256_file(goal_path),
        "plan_draft_sha256": sha256_file(plan_draft_path),
        "simulation_report_sha256": sha256_file(simulation_report_path),
        "checkpoint_sha256": sha256_file(checkpoint_path)
    }
    
    # gate_result
    if decision == "EXECUTION_APPROVED":
        allowed_next_step = "EXECUTION"
        gate_reason = "Human approval granted. Execution can proceed to Step4."
    else:
        allowed_next_step = "STOP"
        gate_reason = "Human rejection. Execution must not proceed."
    
    gate_result = {
        "allowed_next_step": allowed_next_step,
        "reason": gate_reason
    }
    
    return {
        "run_id": run_id,
        "decision_id": decision_id,
        "created_at": created_at,
        "decision": decision,
        "decision_maker": {
            "type": "HUMAN",
            "identifier": operator_id
        },
        "decision_reason": reason,
        "inputs": inputs,
        "hashes": hashes,
        "gate_result": gate_result,
        "version": "v5_step3",
        "state": "DECISION_FROZEN"
    }


def generate_execution_decision(
    run_id: str,
    decision: Literal["EXECUTION_APPROVED", "EXECUTION_REJECTED"],
    operator_id: str,
    reason: str,
    project_root: Optional[Path] = None
) -> tuple[Optional[Dict[str, Any]], Optional[str]]:
    """
    ExecutionDecisionV5 생성 (전체 프로세스)
    
    Args:
        run_id: 실행 ID
        decision: 결정 (EXECUTION_APPROVED 또는 EXECUTION_REJECTED)
        operator_id: 운영자 식별자
        reason: 결정 사유
        project_root: 프로젝트 루트 경로
    
    Returns:
        Tuple[Optional[Dict], Optional[str]]: (execution_decision, error_message)
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
    
    # v5 PlanDraft 검증
    plan_draft_path = project_root / "backend" / "output" / "autonomy_v5" / "plans" / f"{run_id}_plan_draft.json"
    plan_draft_lock_path = project_root / "backend" / "output" / "autonomy_v5" / "plans" / f"{run_id}_plan_draft.lock"
    
    if not plan_draft_path.exists():
        return None, f"v5 PlanDraft not found: {plan_draft_path.resolve()}"
    
    if not plan_draft_lock_path.exists():
        return None, f"v5 PlanDraft lock not found: {plan_draft_lock_path.resolve()}"
    
    # v5 Simulation Report 검증
    simulation_report_path = project_root / "backend" / "output" / "autonomy_v5" / "reports" / f"{run_id}_simulation_report.json"
    
    if not simulation_report_path.exists():
        return None, f"v5 Simulation Report not found: {simulation_report_path.resolve()}"
    
    # v4 Checkpoint 검증
    checkpoint_path = project_root / "backend" / "output" / "evolution_v4" / "checkpoints" / f"{run_id}.json"
    checkpoint_lock_path = project_root / "backend" / "output" / "evolution_v4" / "checkpoints" / f"{run_id}.lock"
    
    if not checkpoint_path.exists():
        return None, f"v4 Checkpoint not found: {checkpoint_path.resolve()}"
    
    if not checkpoint_lock_path.exists():
        return None, f"v4 Checkpoint lock not found: {checkpoint_lock_path.resolve()}"
    
    # ExecutionDecision 생성
    execution_decision = create_execution_decision(
        run_id, decision, operator_id, reason,
        goal_path, plan_draft_path, simulation_report_path, checkpoint_path
    )
    
    return execution_decision, None

