"""
VERSIONED POLICY ENGINE - 정책 버전화 및 충돌 탐지
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple


def load_policy_version(repo_root: Path) -> Dict[str, Any]:
    """
    정책 버전 로드
    
    Returns:
        Dict: policy_version.json 내용
    """
    policy_path = repo_root / "data" / "knowledge_v1_store" / "governance" / "policy_version.json"
    
    if not policy_path.exists():
        # 기본 정책 버전 생성
        default_policy = {
            "version": "v1.0.0",
            "allow_rules": [],
            "deny_rules": [],
            "budget_rules": {},
            "cost_rules": {},
        }
        save_policy_version(default_policy, repo_root)
        return default_policy
    
    with open(policy_path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_policy_version(policy: Dict[str, Any], repo_root: Path) -> Path:
    """정책 버전 저장"""
    governance_dir = repo_root / "data" / "knowledge_v1_store" / "governance"
    governance_dir.mkdir(parents=True, exist_ok=True)
    
    policy_path = governance_dir / "policy_version.json"
    with open(policy_path, "w", encoding="utf-8") as f:
        json.dump(policy, f, ensure_ascii=False, indent=2)
    
    return policy_path


def detect_policy_conflicts(policy: Dict[str, Any], context: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    정책 충돌 탐지
    
    Args:
        policy: 정책 버전
        context: 실행 컨텍스트 (카테고리, 소스 등)
        
    Returns:
        Tuple[bool, List[str]]: (충돌 여부, 충돌 목록)
    """
    conflicts = []
    
    allow_rules = policy.get("allow_rules", [])
    deny_rules = policy.get("deny_rules", [])
    
    # allow & deny 동시 매칭 확인
    for allow_rule in allow_rules:
        if _matches_rule(allow_rule, context):
            for deny_rule in deny_rules:
                if _matches_rule(deny_rule, context):
                    conflicts.append(
                        f"CONFLICT: allow_rule={allow_rule} and deny_rule={deny_rule} both match context={context}"
                    )
    
    # budget > threshold & override 없음 확인
    budget_rules = policy.get("budget_rules", {})
    cost_rules = policy.get("cost_rules", {})
    
    estimated_cost = context.get("estimated_cost", 0)
    cost_limit = budget_rules.get("cost_limit_per_run", 5.0)
    override_allowed = budget_rules.get("allow_override", False)
    
    if estimated_cost > cost_limit and not override_allowed:
        conflicts.append(
            f"BUDGET_EXCEEDED: estimated_cost={estimated_cost} > cost_limit={cost_limit} and override not allowed"
        )
    
    return (len(conflicts) > 0, conflicts)


def _matches_rule(rule: Dict[str, Any], context: Dict[str, Any]) -> bool:
    """규칙이 컨텍스트와 매칭되는지 확인"""
    # 간단한 구현: rule의 모든 키가 context에 있고 값이 일치하는지 확인
    for key, value in rule.items():
        if key == "type":  # 규칙 타입은 무시
            continue
        if key not in context:
            return False
        if context[key] != value:
            return False
    return True


def get_policy_version_string(policy: Dict[str, Any]) -> str:
    """정책 버전 문자열 반환"""
    return policy.get("version", "v1.0.0")

