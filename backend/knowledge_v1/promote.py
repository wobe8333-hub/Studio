"""
Knowledge v1 Promote - Discovery → Approved 승격
"""

from typing import List, Dict
from datetime import datetime
from pathlib import Path
from backend.knowledge_v1.paths import get_assets_path, get_chunks_path, get_audit_path, ensure_dirs
from backend.knowledge_v1.store import load_jsonl, append_asset, append_chunk, append_audit, get_existing_raw_hashes
from backend.knowledge_v1.audit import AuditEvent
from backend.knowledge_v1.classify import classify
from backend.knowledge_v1.derive import derive
from backend.knowledge_v1.schema import KnowledgeAsset, DerivedChunk


def P(x) -> Path:
    """Path 강제 캐스팅 전역 방어 함수"""
    if isinstance(x, Path):
        return x
    if x is None:
        raise ValueError("Path cannot be None")
    return Path(x)


# V7: 자동 승격 대상 카테고리 (6개)
AUTO_PROMOTE_CATEGORIES = {
    "history",
    "mystery",
    "economy",
    "myth",
    "science",
    "war_history"
}


def promote_to_approved_v2(category: str, approve_fallback: bool = False) -> Dict:
    """
    Discovery → Approved 승격 (v7.3)
    
    Args:
        category: 카테고리
        approve_fallback: Fallback asset 승격 허용 여부
    
    Returns:
        Dict: 승격 결과 통계
    """
    # 자동 승격 대상 카테고리 확인
    if category not in AUTO_PROMOTE_CATEGORIES:
        return {
            "promoted_count": 0,
            "reason": "category_not_promotable"
        }
    
    # Discovery assets 로드
    discovery_assets_path = P(get_assets_path("discovery"))
    if not discovery_assets_path.exists():
        return {
            "promoted_count": 0,
            "reason": "no_discovery_assets"
        }
    
    # Approved에 이미 존재하는 raw_hash
    approved_hashes = get_existing_raw_hashes("approved")
    
    # 승격 조건 확인 및 승격
    promoted_count = 0
    promoted_assets = []
    
    for asset_dict in load_jsonl(discovery_assets_path):
        if asset_dict.get("category") != category:
            continue
        
        # Fallback asset 체크
        source_id = asset_dict.get("source_id", "")
        is_fallback = source_id == "fallback_synthetic"
        if is_fallback and not approve_fallback:
            continue
        
        # 승격 조건 확인
        usage_rights = asset_dict.get("usage_rights", "")
        license_status = asset_dict.get("license_status", "")
        trust_level = asset_dict.get("trust_level", "")
        impact_scope = asset_dict.get("impact_scope", "")
        raw_hash = asset_dict.get("raw_hash", "")
        
        # PATCH-13: 뉴스/RSS 기반 asset 판별
        payload = asset_dict.get("payload", {})
        real_fetch = payload.get("real_fetch", {}) if isinstance(payload, dict) else {}
        provider = real_fetch.get("provider", "") if isinstance(real_fetch, dict) else ""
        is_news_rss = (provider == "rss" or source_id == "google_news_rss")
        
        # 조건 1: usage_rights == "ALLOWED"
        if usage_rights != "ALLOWED":
            continue
        
        # 조건 2: license_status == "KNOWN"
        if license_status != "KNOWN":
            continue
        
        # 조건 3: trust_level (뉴스/RSS는 MEDIUM 이상, 일반은 HIGH/MEDIUM)
        if is_news_rss:
            if trust_level not in {"HIGH", "MEDIUM"}:
                continue
        else:
            if trust_level not in {"HIGH", "MEDIUM"}:
                continue
        
        # 조건 4: impact_scope (뉴스/RSS는 LOW도 허용, 일반은 LOW/MEDIUM)
        if is_news_rss:
            # 뉴스/RSS는 LOW도 허용
            if impact_scope not in {"LOW", "MEDIUM", "HIGH"}:
                continue
        else:
            if impact_scope not in {"LOW", "MEDIUM"}:
                continue
        
        # 조건 5: raw_hash 기준 중복 없음
        if not raw_hash or raw_hash in approved_hashes:
            continue
        
        # KnowledgeAsset 객체로 복원
        try:
            asset = KnowledgeAsset.from_dict(asset_dict)
        except Exception:
            continue
        
        # V7: Source Score 확인 (정책 기반)
        try:
            from backend.knowledge_v1.policy.validator import load_policy
            policy = load_policy()
            source_scoring = policy.get("source_scoring", {})
            threshold = source_scoring.get("threshold_auto_promote", 60)
            
            # source_score가 없으면 계산
            if asset.source_score is None:
                from backend.knowledge_v1.source_scoring import compute_source_score
                asset.source_score = compute_source_score(asset, policy)
            
            # source_score >= threshold만 승격
            if asset.source_score < threshold:
                # quarantine 폴더로 저장
                from backend.knowledge_v1.paths import get_store_root
                store_root = get_store_root("discovery")
                quarantine_dir = store_root / "quarantine"
                quarantine_dir.mkdir(parents=True, exist_ok=True)
                quarantine_file = quarantine_dir / "quarantined_assets.jsonl"
                from backend.knowledge_v1.store import append_jsonl
                append_jsonl(quarantine_file, asset.to_dict())
                continue
        except Exception:
            # source scoring 실패 시 기존 로직 사용
            pass
        
        # Classify로 eligible_for 확인
        try:
            eligibility = classify(asset, depth="normal")
            eligible_for = eligibility.eligible_for
            
            # 조건 6: eligible_for in {"LIMITED_INJECTION","APPROVED_READY"}
            if eligible_for not in {"LIMITED_INJECTION", "APPROVED_READY"}:
                continue
        except Exception:
            continue
        
        # 승격: Approved에 복사
        if append_asset(asset, "approved", skip_duplicate=True):
            promoted_count += 1
            promoted_assets.append(asset)
            
            # Derived chunks도 복사
            discovery_chunks_path = P(get_chunks_path("discovery"))
            if discovery_chunks_path.exists():
                for chunk_dict in load_jsonl(discovery_chunks_path):
                    if chunk_dict.get("asset_id") == asset.asset_id:
                        chunk = DerivedChunk.from_dict(chunk_dict)
                        append_chunk(chunk, "approved")
            
            # Audit 기록
            append_audit(AuditEvent.create("PROMOTE", {
                "asset_id": asset.asset_id,
                "category": category,
                "raw_hash": raw_hash,
                "source_id": source_id,
                "eligible_for": eligible_for
            }), "approved")
            
            # Approved hashes 업데이트
            approved_hashes.add(raw_hash)
    
    return {
        "promoted_count": promoted_count,
        "category": category
    }


# 하위 호환을 위한 별칭
def promote_to_approved(category: str, limit: int = 10) -> Dict:
    """하위 호환 함수 (v7.3에서는 promote_to_approved_v2 사용 권장)"""
    return promote_to_approved_v2(category, approve_fallback=False)

