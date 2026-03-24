"""
Quality Circuit Breaker - 품질 임계값 기반 중단 제어
"""

from typing import Dict, Any, Tuple
from backend.knowledge_v1.gate_stats import compute_gate_stats


def check_circuit_breaker(
    store: str = "discovery",
    policy: Dict[str, Any] = None
) -> Tuple[bool, str, Dict[str, Any]]:
    """
    Circuit Breaker 검사
    
    Args:
        store: "discovery" | "approved"
        policy: 정책 딕셔너리 (없으면 로드)
    
    Returns:
        (should_stop, reason, stats)
    """
    if policy is None:
        from backend.knowledge_v1.policy.validator import load_policy
        policy = load_policy()
    
    circuit_config = policy.get("quality_circuit_breaker", {})
    blocked_ratio_max = circuit_config.get("blocked_ratio_max", 0.60)
    unknown_ratio_max = circuit_config.get("unknown_ratio_max", 0.40)
    ready_min = circuit_config.get("ready_min", 1)
    
    # 게이트 통계 계산
    try:
        gate_stats = compute_gate_stats(store)
    except Exception:
        # 통계 계산 실패 시 중단하지 않음 (로깅만)
        return False, "stats_compute_failed", {}
    
    totals = gate_stats.get("totals", {})
    eligibility_stats = gate_stats.get("eligibility_stats", {})
    
    total_assets = totals.get("total_assets", 0)
    blocked_count = eligibility_stats.get("BLOCKED", 0)
    unknown_count = eligibility_stats.get("UNKNOWN", 0)
    ready_count = eligibility_stats.get("READY", 0) + eligibility_stats.get("FULLY_USABLE", 0)
    
    # blocked_ratio > 0.60 → STOP
    if total_assets > 0:
        blocked_ratio = blocked_count / total_assets
        if blocked_ratio > blocked_ratio_max:
            return True, f"blocked_ratio_exceeded ({blocked_ratio:.2f} > {blocked_ratio_max})", gate_stats
    
    # unknown_ratio > 0.40 → STOP
    if total_assets > 0:
        unknown_ratio = unknown_count / total_assets
        if unknown_ratio > unknown_ratio_max:
            return True, f"unknown_ratio_exceeded ({unknown_ratio:.2f} > {unknown_ratio_max})", gate_stats
    
    # ready_count < 1 → STOP
    if ready_count < ready_min:
        return True, f"ready_count_below_min ({ready_count} < {ready_min})", gate_stats
    
    return False, "ok", gate_stats

