"""
Policy Validator - 정책 충돌 검사 및 검증
"""

import json
from pathlib import Path
from typing import Dict, Any, List, Tuple


def _find_repo_root() -> Path:
    """repo root 탐색"""
    p = Path(__file__).resolve()
    for parent in [p.parent] + list(p.parents):
        if (parent / "backend").is_dir() and (parent / "config").is_dir():
            return parent
    raise RuntimeError(f"repo root not found. Searched from: {__file__}")


def load_policy() -> Dict[str, Any]:
    """정책 파일 로드"""
    repo_root = _find_repo_root()
    policy_path = repo_root / "config" / "policy" / "knowledge_policy.json"
    
    if not policy_path.exists():
        raise FileNotFoundError(f"Policy file not found: {policy_path}")
    
    with open(policy_path, "r", encoding="utf-8") as f:
        return json.load(f)


def validate_policy(policy: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    정책 검증
    
    Returns:
        (is_valid, conflict_list)
    """
    conflicts = []
    
    # 1. categories 길이 == 6
    categories = policy.get("categories", [])
    if len(categories) != 6:
        conflicts.append(f"categories length must be 6, got {len(categories)}")
    
    # 2. per_category_target_keywords == 5
    target_kw = policy.get("per_category_target_keywords", 0)
    if target_kw != 5:
        conflicts.append(f"per_category_target_keywords must be 5, got {target_kw}")
    
    # 3. min_keywords_step_e >= 30
    min_kw = policy.get("min_keywords_step_e", 0)
    if min_kw < 30:
        conflicts.append(f"min_keywords_step_e must be >= 30, got {min_kw}")
    
    # 4. quota.per_category_limit >= 5
    quota = policy.get("quota", {})
    per_cat_limit = quota.get("per_category_limit", 0)
    if per_cat_limit < 5:
        conflicts.append(f"quota.per_category_limit must be >= 5, got {per_cat_limit}")
    
    # 5. threshold_auto_promote 0~100
    source_scoring = policy.get("source_scoring", {})
    threshold = source_scoring.get("threshold_auto_promote", -1)
    if not (0 <= threshold <= 100):
        conflicts.append(f"source_scoring.threshold_auto_promote must be 0~100, got {threshold}")
    
    # 6. verify_thresholds 값 > 0 (SSOT)
    verify = policy.get("verify_thresholds", {})
    required_keys = [
        "assets_min",
        "chunks_min",
        "ready_min",
        "avg_chunks_per_asset_min",
    ]
    missing = [k for k in required_keys if k not in verify]
    if missing:
        conflicts.append(f"verify_thresholds missing keys: {','.join(missing)}")
    for key, value in verify.items():
        if not isinstance(value, (int, float)) or value <= 0:
            conflicts.append(f"verify_thresholds.{key} must be > 0, got {value}")
    
    return len(conflicts) == 0, conflicts


def validate_and_load_policy() -> Tuple[Dict[str, Any], bool, List[str]]:
    """
    정책 로드 및 검증
    
    Returns:
        (policy, is_valid, conflict_list)
    """
    policy = load_policy()
    is_valid, conflicts = validate_policy(policy)
    return policy, is_valid, conflicts

