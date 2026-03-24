"""
Knowledge v1 Audit - 감사 로그 기록
"""

from pathlib import Path
from typing import Dict, Any
from backend.knowledge_v1.store import append_jsonl
from backend.knowledge_v1.paths import get_audit_path, ensure_dirs
from backend.knowledge_v1.schema import AuditEvent


def log_event(event_type: str, details: Dict[str, Any], store: str = "approved") -> None:
    """
    감사 이벤트 기록
    
    Args:
        event_type: 이벤트 타입
        details: 이벤트 상세 정보
        store: "discovery" | "approved" (기본값: "approved")
    """
    try:
        event = AuditEvent.create(event_type, details)
        audit_path = get_audit_path(store)
        ensure_dirs(store)
        append_jsonl(audit_path, event.to_dict())
    except Exception:
        # audit 기록 실패는 무시 (무한 루프 방지)
        pass


def log_event_both(event_type: str, details: Dict[str, Any]) -> None:
    """
    감사 이벤트를 discovery와 approved 둘 다 기록 (v7-run 오케스트레이션용)
    
    Args:
        event_type: 이벤트 타입
        details: 이벤트 상세 정보 (layer 필드 추가됨)
    """
    # discovery에 기록
    try:
        discovery_details = {**details, "layer": "discovery"}
        log_event(f"{event_type}_DISCOVERY", discovery_details, store="discovery")
    except Exception:
        pass
    
    # approved에 기록
    try:
        approved_details = {**details, "layer": "approved"}
        log_event(f"{event_type}_APPROVED", approved_details, store="approved")
    except Exception:
        pass

