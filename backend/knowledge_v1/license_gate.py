"""
Knowledge v1 License Gate - 라이선스·권한 선차단 게이트
"""

from typing import Tuple
from backend.knowledge_v1.schema import KnowledgeAsset
from backend.knowledge_v1.store import append_jsonl
from backend.knowledge_v1.paths import get_store_root, ensure_dirs
from backend.knowledge_v1.audit import log_event


def apply_license_gate(asset: KnowledgeAsset) -> Tuple[bool, str]:
    """
    라이선스 게이트 적용
    
    Returns:
        Tuple[bool, str]: (통과 여부, 이유)
    """
    # 내부 생성 지식은 항상 통과 (최우선)
    license_source = getattr(asset, 'license_source', None)
    if license_source == "INTERNAL_SYNTHETIC":
        return True, "internal_synthetic"
    
    # fallback_synthetic source_id도 확인 (하위 호환)
    if asset.source_id == "fallback_synthetic":
        return True, "fallback_synthetic"
    
    # 하드 룰: UNKNOWN이면 BLOCKED (단, INTERNAL_SYNTHETIC은 제외)
    # reason_code 강제: 모든 BLOCKED에 reason_code 부여
    if asset.usage_rights == "UNKNOWN":
        asset.lifecycle_state = "BLOCKED"
        blocked_path = get_store_root("approved") / "blocked" / "blocked_assets.jsonl"
        ensure_dirs("approved")
        blocked_entry = asset.to_dict()
        blocked_entry["block_reason"] = "usage_rights_unknown"  # reason_code (진단용)
        append_jsonl(blocked_path, blocked_entry)
        log_event("LICENSE_BLOCK", {
            "asset_id": asset.asset_id,
            "reason": "usage_rights_unknown"  # reason_code
        }, store="approved")
        return False, "usage_rights_unknown"
    
    # license_status가 UNKNOWN이어도 INTERNAL_SYNTHETIC이면 통과
    if asset.license_status == "UNKNOWN" and license_source != "INTERNAL_SYNTHETIC":
        asset.lifecycle_state = "BLOCKED"
        blocked_path = get_store_root("approved") / "blocked" / "blocked_assets.jsonl"
        ensure_dirs("approved")
        blocked_entry = asset.to_dict()
        blocked_entry["block_reason"] = "license_unknown"  # reason_code (진단용)
        append_jsonl(blocked_path, blocked_entry)
        log_event("LICENSE_BLOCK", {
            "asset_id": asset.asset_id,
            "reason": "license_unknown"  # reason_code
        }, store="approved")
        return False, "license_unknown"
    
    return True, "passed"

