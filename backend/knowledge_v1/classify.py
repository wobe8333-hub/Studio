"""
Knowledge v1 Classify - 사용 가능성 분류
"""

from backend.knowledge_v1.schema import KnowledgeAsset, Eligibility
from backend.knowledge_v1.store import append_jsonl
from backend.knowledge_v1.paths import get_store_root, ensure_dirs
from backend.knowledge_v1.audit import log_event


def classify(asset: KnowledgeAsset, depth: str = "normal") -> Eligibility:
    """
    사용 가능성 분류
    
    Args:
        asset: 자산
        depth: 수집 깊이 (normal|deep)
    
    Returns:
        Eligibility: 분류 결과
    """
    # lifecycle_state가 BLOCKED면 BLOCKED (reason_code 강제)
    if asset.lifecycle_state == "BLOCKED":
        eligibility = Eligibility.create(
            asset_id=asset.asset_id,
            eligible_for="BLOCKED",
            reason="lifecycle_state_blocked"  # reason_code (진단용)
        )
        # BLOCKED도 used_assets.jsonl에 기록하여 reason_code 추적 가능 (진단 가능 상태)
        used_path = get_store_root("approved") / "used" / "used_assets.jsonl"
        ensure_dirs("approved")
        used_entry = {
            "asset_id": asset.asset_id,
            "eligible_for": "BLOCKED",
            "reason": "lifecycle_state_blocked",  # reason_code
            "category": asset.category,
            "decided_at": eligibility.decided_at
        }
        append_jsonl(used_path, used_entry)
        
        log_event("CLASSIFY", {
            "asset_id": asset.asset_id,
            "eligible_for": "BLOCKED",
            "reason": "lifecycle_state_blocked"
        }, store="approved")
        return eligibility
    # fallback asset은 제한적 사용만 허용
    elif (hasattr(asset, 'license_source') and asset.license_source == "INTERNAL_SYNTHETIC") or asset.source_id == "fallback_synthetic":
        eligibility = Eligibility.create(
            asset_id=asset.asset_id,
            eligible_for="LIMITED_INJECTION",
            reason="fallback_minimum_viable_knowledge"
        )
    # 카테고리별 분류: science
    elif asset.category == "science":
        # 기본 REFERENCE_ONLY
        if asset.trust_level == "HIGH" and asset.usage_rights == "ALLOWED" and asset.impact_scope != "HIGH":
            # LIMITED_INJECTION 조건만 예외적으로 허용
            eligibility = Eligibility.create(
                asset_id=asset.asset_id,
                eligible_for="LIMITED_INJECTION",
                reason="science_high_trust_allowed_low_impact"
            )
        elif asset.trust_level in {"MEDIUM", "HIGH"} and asset.usage_rights == "ALLOWED":
            eligibility = Eligibility.create(
                asset_id=asset.asset_id,
                eligible_for="REFERENCE_ONLY",
                reason="science_reference_only"
            )
        else:
            eligibility = Eligibility.create(
                asset_id=asset.asset_id,
                eligible_for="REFERENCE_ONLY",
                reason="science_default_reference_only"
            )
    # 카테고리별 분류: common_sense
    elif asset.category == "common_sense":
        # 기본 LIMITED_INJECTION
        if asset.trust_level == "LOW" or asset.impact_scope == "HIGH":
            # trust_level이 LOW이거나 impact_scope가 HIGH면 REFERENCE_ONLY로 강등
            eligibility = Eligibility.create(
                asset_id=asset.asset_id,
                eligible_for="REFERENCE_ONLY",
                reason="common_sense_low_trust_or_high_impact"
            )
        elif asset.trust_level == "HIGH" and asset.usage_rights == "ALLOWED":
            # trust_level이 HIGH이고 usage_rights가 ALLOWED면 LIMITED_INJECTION 유지
            eligibility = Eligibility.create(
                asset_id=asset.asset_id,
                eligible_for="LIMITED_INJECTION",
                reason="common_sense_high_trust_allowed"
            )
        else:
            eligibility = Eligibility.create(
                asset_id=asset.asset_id,
                eligible_for="REFERENCE_ONLY",
                reason="common_sense_default_reference_only"
            )
    # 기존 카테고리 로직
    # trust_level=="HIGH" and usage_rights=="ALLOWED" and impact_scope!="HIGH" → LIMITED_INJECTION
    elif asset.trust_level == "HIGH" and asset.usage_rights == "ALLOWED" and asset.impact_scope != "HIGH":
        eligibility = Eligibility.create(
            asset_id=asset.asset_id,
            eligible_for="LIMITED_INJECTION",
            reason="high_trust_allowed_low_impact"
        )
    # trust_level in {"MEDIUM","HIGH"} and usage_rights=="ALLOWED" → REFERENCE_ONLY
    elif asset.trust_level in {"MEDIUM", "HIGH"} and asset.usage_rights == "ALLOWED":
        eligibility = Eligibility.create(
            asset_id=asset.asset_id,
            eligible_for="REFERENCE_ONLY",
            reason="medium_high_trust_allowed"
        )
    # depth=="deep" + trust_level=="HIGH" + impact_scope=="LOW" → FULLY_USABLE (science/common_sense 제외)
    elif depth == "deep" and asset.trust_level == "HIGH" and asset.impact_scope == "LOW":
        eligibility = Eligibility.create(
            asset_id=asset.asset_id,
            eligible_for="FULLY_USABLE",
            reason="deep_high_trust_low_impact"
        )
    # 그 외 → REFERENCE_ONLY
    else:
        eligibility = Eligibility.create(
            asset_id=asset.asset_id,
            eligible_for="REFERENCE_ONLY",
            reason="default_reference_only"
        )
    
    # 저장 (BLOCKED 제외한 자산을 used_assets.jsonl에 기록)
    # reason_code 강제: reason 필드에 항상 reason_code 저장 (진단 가능)
    if eligibility.eligible_for != "BLOCKED":
        used_path = get_store_root("approved") / "used" / "used_assets.jsonl"
        ensure_dirs("approved")
        used_entry = {
            "asset_id": asset.asset_id,
            "eligible_for": eligibility.eligible_for,
            "reason": eligibility.reason,  # reason_code (강제)
            "category": asset.category,  # 카테고리 추가 (reasons_by_category를 위해)
            "decided_at": eligibility.decided_at
        }
        append_jsonl(used_path, used_entry)
    
    # lifecycle_state 업데이트
    if eligibility.eligible_for != "BLOCKED":
        asset.lifecycle_state = "USED"
    
    log_event("CLASSIFY", {
        "asset_id": asset.asset_id,
        "eligible_for": eligibility.eligible_for,
        "reason": eligibility.reason
    }, store="approved")
    
    return eligibility

