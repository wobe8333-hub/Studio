"""
Keyword Signals Schema - 외부 신호 데이터 스키마 정의 및 검증
"""

from typing import Dict, List, Any, Optional
from datetime import datetime


def create_empty_signals_json(cycle_id: str) -> Dict[str, Any]:
    """빈 신호 JSON 생성 (기본 구조)"""
    return {
        "cycle_id": cycle_id,
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "scope": "KR",
        "sources": []
    }


def create_source_entry(
    name: str,
    enabled: bool,
    status: str,
    skipped_reason: Optional[str] = None,
    meta: Optional[Dict[str, Any]] = None,
    items: Optional[List[Dict[str, Any]]] = None
) -> Dict[str, Any]:
    """소스 엔트리 생성"""
    entry = {
        "name": name,
        "enabled": enabled,
        "status": status,
        "skipped_reason": skipped_reason,
        "meta": meta or {},
        "items": items or []
    }
    return entry


def create_signal_item(
    term: str,
    score: float = 0.0,
    rank: int = 1,
    evidence: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """신호 아이템 생성"""
    return {
        "term": term,
        "score": score,
        "rank": rank,
        "evidence": evidence or {}
    }


def validate_signals_json(data: Dict[str, Any]) -> tuple[bool, Optional[str]]:
    """신호 JSON 검증"""
    if not isinstance(data, dict):
        return False, "data is not a dict"
    
    required_keys = ["cycle_id", "generated_at", "scope", "sources"]
    for key in required_keys:
        if key not in data:
            return False, f"missing required key: {key}"
    
    if data.get("scope") != "KR":
        return False, f"scope must be 'KR', got: {data.get('scope')}"
    
    if not isinstance(data.get("sources"), list):
        return False, "sources must be a list"
    
    # 각 source 검증
    for source in data.get("sources", []):
        if not isinstance(source, dict):
            return False, "source entry must be a dict"
        
        source_required = ["name", "enabled", "status"]
        for key in source_required:
            if key not in source:
                return False, f"source missing required key: {key}"
        
        if source.get("status") not in ["skipped", "ok", "error"]:
            return False, f"source status must be one of ['skipped', 'ok', 'error'], got: {source.get('status')}"
        
        if not isinstance(source.get("items", []), list):
            return False, "source items must be a list"
    
    return True, None

