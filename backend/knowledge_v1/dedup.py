"""
Knowledge v1 Dedup - 2단계 중복/유사 키워드 병합
"""

from typing import List, Set, Tuple
from backend.knowledge_v1.audit import log_event


def _normalize_keyword(kw: str) -> str:
    """키워드 정규화 (정확 중복 검사용)"""
    return kw.strip().lower()


def jaccard_similarity(set1: Set[str], set2: Set[str]) -> float:
    """Jaccard 유사도 계산"""
    intersection = len(set1 & set2)
    union = len(set1 | set2)
    if union == 0:
        return 0.0
    return intersection / union


def dedup_keywords(keywords: List[str], threshold: float = 0.8) -> Tuple[List[str], int, int]:
    """
    2단계 중복 제거
    
    1단계: normalize exact 중복 제거
    2단계: 유사도 기반 병합 (Jaccard ≥ threshold)
    
    Args:
        keywords: 키워드 리스트
        threshold: 유사도 임계값 (기본 0.8)
    
    Returns:
        (병합된 키워드 리스트, exact_removed_count, similar_removed_count)
    """
    if not keywords:
        return [], 0, 0
    
    # 1단계: normalize exact 중복 제거
    seen_exact = set()
    after_exact = []
    exact_removed = 0
    
    for kw in keywords:
        kw_norm = _normalize_keyword(kw)
        if kw_norm not in seen_exact:
            seen_exact.add(kw_norm)
            after_exact.append(kw)
        else:
            exact_removed += 1
    
    # 2단계: 유사도 기반 병합
    keyword_sets = {}
    for kw in after_exact:
        words = set(kw.lower().split())
        keyword_sets[kw] = words
    
    merged = []
    used = set()
    similar_removed = 0
    
    for kw in after_exact:
        if kw in used:
            continue
        
        kw_set = keyword_sets[kw]
        
        for other_kw in after_exact:
            if other_kw == kw or other_kw in used:
                continue
            
            other_set = keyword_sets[other_kw]
            similarity = jaccard_similarity(kw_set, other_set)
            
            if similarity >= threshold:
                used.add(other_kw)
                similar_removed += 1
        
        merged.append(kw)
        used.add(kw)
    
    if exact_removed > 0 or similar_removed > 0:
        log_event("DEDUP_APPLIED", {
            "original_count": len(keywords),
            "merged_count": len(merged),
            "exact_removed": exact_removed,
            "similar_removed": similar_removed,
            "threshold": threshold
        })
    
    return merged, exact_removed, similar_removed

