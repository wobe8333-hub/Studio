"""
Knowledge v1 Quota - 일일/카테고리별 상한 관리
"""

from typing import Dict, Tuple, Optional
from datetime import datetime
from pathlib import Path
from backend.knowledge_v1.paths import get_store_root
from backend.knowledge_v1.audit import log_event
import json


from datetime import datetime
from pathlib import Path
from backend.knowledge_v1.paths import get_store_root
from backend.knowledge_v1.audit import log_event
import json


# V7: 정책 기반 쿼터 설정
def _load_quota_from_policy() -> Tuple[int, Dict[str, int]]:
    """정책에서 쿼터 로드"""
    try:
        from backend.knowledge_v1.policy.validator import load_policy
        policy = load_policy()
        quota_config = policy.get("quota", {})
        daily_total = quota_config.get("daily_total_limit", 200)
        per_category = quota_config.get("per_category_limit", 20)
        
        # V7: 6개 카테고리
        categories = policy.get("categories", ["history", "mystery", "economy", "myth", "science", "war_history"])
        per_category_limit = {cat: per_category for cat in categories}
        
        return daily_total, per_category_limit
    except Exception:
        # 정책 로드 실패 시 기본값
        return 200, {
            "history": 20,
            "mystery": 20,
            "economy": 20,
            "myth": 20,
            "science": 20,
            "war_history": 20
        }

# 동적 로드 (정책 기반)
_daily_total, _per_category = _load_quota_from_policy()
DAILY_TOTAL_LIMIT = _daily_total
PER_CATEGORY_LIMIT = _per_category


def get_quota_state_path() -> Path:
    """쿼터 상태 파일 경로"""
    root = get_store_root("discovery")
    return root / "state" / "quota.json"


def load_quota_state() -> Dict:
    """쿼터 상태 로드"""
    path = get_quota_state_path()
    if path.exists():
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    today = datetime.now().date().isoformat()
    return {
        "date": today,
        "daily_total": 0,
        "per_category": {}
    }


def save_quota_state(state: Dict) -> None:
    """쿼터 상태 저장"""
    from backend.knowledge_v1.store import atomic_write_json
    path = get_quota_state_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    atomic_write_json(path, state)


def check_quota(category: str, count: int) -> tuple[bool, Optional[str]]:
    """
    쿼터 확인
    
    Args:
        category: 카테고리
        count: 추가하려는 개수
    
    Returns:
        (허용 여부, 거부 사유)
    """
    # V7: 정책 기반 카테고리 확인 (6개 카테고리 모두 허용)
    
    state = load_quota_state()
    today = datetime.now().date().isoformat()
    
    # 날짜가 바뀌면 리셋
    if state.get("date") != today:
        state = {
            "date": today,
            "daily_total": 0,
            "per_category": {}
        }
    
    # 일일 총합 확인
    if state["daily_total"] + count > DAILY_TOTAL_LIMIT:
        return False, f"daily_limit_exceeded ({state['daily_total']}/{DAILY_TOTAL_LIMIT})"
    
    # 카테고리별 확인
    category_limit = PER_CATEGORY_LIMIT.get(category, 0)
    if category_limit == 0:
        return False, f"category_not_allowed ({category})"
    
    current_category_count = state["per_category"].get(category, 0)
    if current_category_count + count > category_limit:
        return False, f"category_limit_exceeded ({current_category_count}/{category_limit})"
    
    return True, None


def apply_quota(category: str, count: int, extra: dict | None = None, **kwargs) -> bool:
    """
    쿼터 적용 (사용량 증가)
    
    Returns:
        성공 여부
    """
    if extra is None:
        extra = {}
    if not isinstance(extra, dict):
        extra = {"_extra": str(extra)}
    _ = kwargs  # compatibility: ignore unknown kwargs
    allowed, reason = check_quota(category, count)
    if not allowed:
        log_event("QUOTA_APPLIED", {
            "category": category,
            "count": count,
            "result": "REJECTED",
            "reason": reason
        })
        return False
    
    state = load_quota_state()
    today = datetime.now().date().isoformat()
    
    if state.get("date") != today:
        state = {
            "date": today,
            "daily_total": 0,
            "per_category": {}
        }
    
    state["daily_total"] += count
    state["per_category"][category] = state["per_category"].get(category, 0) + count
    save_quota_state(state)
    
    log_event("QUOTA_APPLIED", {
        "category": category,
        "count": count,
        "result": "ALLOWED",
        "daily_total": state["daily_total"],
        "category_total": state["per_category"].get(category, 0)
    })
    
    return True

