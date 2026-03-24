"""
Source Scoring - 소스별 품질 점수 계산 (0~100)
"""

from typing import Dict, Any, List
from backend.knowledge_v1.schema import KnowledgeAsset


def compute_source_score(
    asset: KnowledgeAsset,
    policy: Dict[str, Any] = None
) -> int:
    """
    소스별 점수 계산 (결정론적 산식)
    
    Args:
        asset: KnowledgeAsset
        policy: 정책 딕셔너리 (없으면 로드)
    
    Returns:
        점수 (0~100, clamp)
    """
    if policy is None:
        from backend.knowledge_v1.policy.validator import load_policy
        policy = load_policy()
    
    source_scoring = policy.get("source_scoring", {})
    weights = source_scoring.get("weights", {})
    
    source_id = asset.source_id
    score = 0
    
    # 소스별 가중치 적용
    if "yt_api" in source_id or "youtube_data_api" in source_id:
        score += weights.get("yt_api", 30)
    elif "ytdlp" in source_id or "yt_dlp" in source_id:
        score += weights.get("yt_dlp", 20)
    elif "dataset" in source_id or "trending_dataset" in source_id:
        score += weights.get("dataset", 15)
    elif "wiki" in source_id or "wikipedia" in source_id:
        score += weights.get("wiki", 20)
    elif "news" in source_id or "rss" in source_id:
        score += weights.get("news", 15)
    
    # trust_level 보너스
    trust_level = asset.trust_level
    if trust_level == "HIGH":
        score += 20
    elif trust_level == "MEDIUM":
        score += 10
    
    # usage_rights 보너스
    usage_rights = asset.usage_rights
    if usage_rights == "ALLOWED":
        score += 10
    
    # Clamp 0~100
    score = max(0, min(100, score))
    
    return score

