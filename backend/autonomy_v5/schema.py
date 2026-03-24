"""
v5-Step1: Goal & Constraint Definition 스키마

기능:
- GoalDefinitionV5 생성 함수
- UTC 시간 유틸리티
"""

from typing import Dict, Any, Optional, List
from datetime import datetime, timezone


def utc_now_iso() -> str:
    """UTC 현재 시간을 ISO8601 형식으로 반환 (끝은 'Z')"""
    dt = datetime.now(timezone.utc).replace(microsecond=0)
    return dt.isoformat().replace("+00:00", "Z")


def utc_now_compact() -> str:
    """UTC 현재 시간을 컴팩트 형식으로 반환 (백업 파일명용: 20251229T000000Z)"""
    dt = datetime.now(timezone.utc)
    return dt.strftime("%Y%m%dT%H%M%SZ")


def create_goal_definition_v5(
    run_id: str,
    checkpoint_hash: str,
    rollback_manifest_hash: str,
    created_at: Optional[str] = None
) -> Dict[str, Any]:
    """
    GoalDefinitionV5 생성
    
    Args:
        run_id: 실행 ID
        checkpoint_hash: v4 checkpoint sha256 해시
        rollback_manifest_hash: v4 rollback manifest sha256 해시
        created_at: 생성 시각 (None이면 현재 시각)
    
    Returns:
        Dict: GoalDefinitionV5 JSON 데이터
    """
    if created_at is None:
        created_at = utc_now_iso()
    
    goal_id = f"goal_v5_step1:{run_id}:{created_at}"
    
    return {
        "run_id": run_id,
        "goal_id": goal_id,
        "created_at": created_at,
        "primary_goal": {
            "description": "AI Animation Studio의 자율 실행을 통해 애니메이션 생성 품질과 효율성을 지속적으로 개선",
            "success_criteria": [
                "KPI 개선 (failure_count 감소, verify_pass 유지/향상)",
                "실행 안정성 향상 (retry 감소, silence_signal 감소)",
                "다양성 확보 (scene 구성, duration 분포)",
                "비용 효율성 유지"
            ]
        },
        "secondary_goals": [
            {
                "description": "실패 패턴 학습 및 회피 전략 수립"
            },
            {
                "description": "성공 패턴 강화 및 재현성 확보"
            }
        ],
        "absolute_constraints": [
            "LLM_CALL_WITHOUT_APPROVAL",
            "RENDER_WITHOUT_APPROVAL",
            "AUTO_PUBLISH",
            "MODIFY_EXISTING_PLAN",
            "DELETE_EXISTING_OUTPUT",
            "POLICY_AUTO_CHANGE"
        ],
        "operational_constraints": {
            "max_daily_runs": 10,
            "max_cost_usd": 100.0,
            "allowed_execution_scope": [
                "EVALUATION_ONLY",
                "SIMULATION_ONLY"
            ]
        },
        "human_in_the_loop": {
            "approval_required_for": [
                "EXECUTION",
                "RENDER",
                "PUBLISH",
                "POLICY_UPDATE"
            ],
            "manual_override_allowed": True
        },
        "evidence": {
            "checkpoint_hash": checkpoint_hash,
            "rollback_manifest_hash": rollback_manifest_hash
        },
        "version": "v5_step1",
        "state": "GOAL_FROZEN"
    }

