"""
Knowledge v1 Fallback - 0건 시 fallback asset 생성
"""

from datetime import datetime
from typing import List
from backend.knowledge_v1.schema import KnowledgeAsset
from backend.knowledge_v1.store import compute_raw_hash


def create_fallback_asset(category: str, keywords: List[str]) -> KnowledgeAsset:
    """
    Fallback asset 생성 (0건 시 1건 보장)
    
    Args:
        category: 카테고리
        keywords: 키워드 리스트
    
    Returns:
        KnowledgeAsset: Fallback asset
    """
    # payload 생성
    first_keyword = keywords[0] if keywords else category
    joined_keywords = ", ".join(keywords) if keywords else category
    
    payload = {
        "title": f"{first_keyword} (fallback)",
        "summary": "Fallback synthetic asset generated because no sources matched.",
        "text": f"This is a synthetic knowledge stub for the keyword(s): {joined_keywords}. It is generated to keep the pipeline non-empty. It must be verified and enriched by real sources before high-impact use."
    }
    
    # KnowledgeAsset 생성 (내부 생성 지식으로 명시)
    asset = KnowledgeAsset.create(
        category=category,
        keywords=keywords,
        source_id="fallback_synthetic",
        source_ref="internal://fallback_synthetic",
        payload=payload,
        license_status="KNOWN",  # 내부 생성물이므로 KNOWN
        usage_rights="ALLOWED",  # fallback은 내부 생성 텍스트
        trust_level="LOW",
        impact_scope="LOW",
        license_source="INTERNAL_SYNTHETIC"  # 내부 생성 표시
    )
    
    # raw_hash 계산
    asset.raw_hash = compute_raw_hash(payload)
    
    return asset

