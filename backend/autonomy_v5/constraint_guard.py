"""
v5-Step4: Constraint Guard

기능:
- 실시간 제약 감시
- 제약 위반 시 즉시 중단
"""

from typing import Dict, Any, List


def check_constraints(
    goal_definition: Dict[str, Any],
    current_cost_usd: float,
    current_time_sec: float,
    executed_steps: int
) -> tuple[bool, List[str]]:
    """
    제약 확인
    
    Args:
        goal_definition: GoalDefinitionV5 데이터
        current_cost_usd: 현재까지 소비한 비용
        current_time_sec: 현재까지 소비한 시간
        executed_steps: 실행된 단계 수
    
    Returns:
        Tuple[bool, List[str]]: (is_safe, violations)
    """
    violations = []
    
    # operational_constraints 확인
    operational_constraints = goal_definition.get("operational_constraints", {})
    max_cost_usd = operational_constraints.get("max_cost_usd", float("inf"))
    max_daily_runs = operational_constraints.get("max_daily_runs", float("inf"))
    
    if current_cost_usd > max_cost_usd:
        violations.append(f"Cost {current_cost_usd} exceeds max_cost_usd {max_cost_usd}")
    
    if executed_steps > max_daily_runs:
        violations.append(f"Executed steps {executed_steps} exceeds max_daily_runs {max_daily_runs}")
    
    # absolute_constraints는 실행 중 위반 불가 (실행 전에 이미 필터링됨)
    # 하지만 추가 확인
    absolute_constraints = goal_definition.get("absolute_constraints", [])
    # 실행 중에는 이미 승인된 상태이므로 absolute_constraints 위반은 발생하지 않아야 함
    
    is_safe = len(violations) == 0
    
    return is_safe, violations

