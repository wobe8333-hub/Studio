"""
ADAPTIVE EXPLORATION PROBABILITY - 확률적 진화형 탐색
각 source별 확률 weight 계산 및 가중 선택
"""

from __future__ import annotations

import random
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple


def calculate_source_probabilities(
    source_scores: Dict[str, float],
    drift_rates: Dict[str, float],
    moving_average_window: int = 3
) -> Dict[str, float]:
    """
    각 source별 확률 weight 계산
    
    weight_i = (score_i / Σscore) * (1 - drift_rate_i)
    
    Args:
        source_scores: 소스별 점수
        drift_rates: 소스별 drift rate
        moving_average_window: 이동 평균 윈도우 크기
        
    Returns:
        Dict[str, float]: 소스별 확률 weight
    """
    # 3-run moving average 적용 (간단히 현재 점수 사용)
    normalized_scores = {}
    total_score = sum(source_scores.values())
    
    if total_score == 0:
        # 모든 점수가 0이면 균등 분배
        num_sources = len(source_scores)
        for source in source_scores:
            normalized_scores[source] = 1.0 / num_sources if num_sources > 0 else 0.0
    else:
        for source, score in source_scores.items():
            drift_rate = drift_rates.get(source, 0.0)
            # weight = (score / total) * (1 - drift_rate)
            normalized_scores[source] = (score / total_score) * (1 - drift_rate)
    
    # 정규화 (합이 1이 되도록)
    total_weight = sum(normalized_scores.values())
    if total_weight > 0:
        for source in normalized_scores:
            normalized_scores[source] /= total_weight
    
    return normalized_scores


def weighted_choice(sources: List[str], probabilities: Dict[str, float]) -> str:
    """
    확률 가중 선택 (random.choice 대신 사용)
    
    Args:
        sources: 소스 리스트
        probabilities: 소스별 확률
        
    Returns:
        str: 선택된 소스
    """
    if not sources:
        raise ValueError("sources list is empty")
    
    # 누적 확률 계산
    cumulative = []
    total = 0.0
    for source in sources:
        prob = probabilities.get(source, 0.0)
        total += prob
        cumulative.append((source, total))
    
    # 랜덤 값 생성 (0.0 ~ total)
    r = random.uniform(0.0, total)
    
    # 누적 확률에서 선택
    for source, cum_prob in cumulative:
        if r <= cum_prob:
            return source
    
    # fallback: 마지막 소스
    return sources[-1]


def compute_source_probabilities(categories_result: Dict[str, Any]) -> Dict[str, Any]:
    """
    현재 런의 docs_by_source 기반으로 확률 산출
    
    Args:
        categories_result: report["categories"] 딕셔너리
        
    Returns:
        Dict: source_probabilities payload
    """
    from datetime import datetime
    
    # 모든 카테고리의 docs_by_source 합산
    docs_by_source_agg = {}
    for cat, cat_data in categories_result.items():
        if isinstance(cat_data, dict):
            docs_by_source = cat_data.get("docs_by_source", {})
            if isinstance(docs_by_source, dict):
                for source, count in docs_by_source.items():
                    docs_by_source_agg[source] = docs_by_source_agg.get(source, 0) + count
    
    # sources가 비어있으면 기본값
    if not docs_by_source_agg:
        docs_by_source_agg = {"rss": 1.0}
    
    # base_weight 구성 (count 기반)
    total_count = sum(docs_by_source_agg.values())
    weights = {}
    probabilities = {}
    
    if total_count > 0:
        for source, count in docs_by_source_agg.items():
            weights[source] = float(count)
            probabilities[source] = float(count) / total_count
    else:
        # 모든 count가 0이면 균등 분배
        num_sources = len(docs_by_source_agg)
        for source in docs_by_source_agg:
            weights[source] = 1.0 / num_sources if num_sources > 0 else 0.0
            probabilities[source] = 1.0 / num_sources if num_sources > 0 else 0.0
    
    return {
        "version": 1,
        "computed_at": datetime.utcnow().isoformat() + "Z",
        "weights": weights,
        "probabilities": probabilities,
        "inputs": {"docs_by_source_agg": docs_by_source_agg}
    }


def write_source_probabilities(repo_root: Path, payload: Dict[str, Any]) -> str:
    """
    SSOT 경로에 source_probabilities.json 저장
    
    Args:
        repo_root: 레포 루트
        payload: compute_source_probabilities 결과
        
    Returns:
        str: 저장된 경로
    """
    from backend.knowledge_v1.paths import get_source_probabilities_path, ensure_governance_dir
    from backend.knowledge_v1.io.json_io import dump_json
    
    ensure_governance_dir(repo_root)
    prob_path = get_source_probabilities_path(repo_root)
    
    # UTF-8 강제 저장 (ensure_ascii=False)
    dump_json(prob_path, payload)
    
    return str(prob_path)


def save_source_probabilities(probabilities: Dict[str, float], repo_root: Path) -> Path:
    """소스 확률 저장 (레거시 호환)"""
    from backend.knowledge_v1.paths import get_source_probabilities_path, ensure_governance_dir
    from backend.knowledge_v1.io.json_io import dump_json
    
    ensure_governance_dir(repo_root)
    prob_path = get_source_probabilities_path(repo_root)
    
    # UTF-8 강제 저장 (ensure_ascii=False)
    dump_json(prob_path, probabilities)
    
    return prob_path


def load_source_probabilities(repo_root: Path) -> Optional[Dict[str, Any]]:
    """소스 확률 로드"""
    from backend.knowledge_v1.paths import get_source_probabilities_path
    from backend.knowledge_v1.io.json_io import load_json
    
    prob_path = get_source_probabilities_path(repo_root)
    if not prob_path.exists():
        return None
    
    # UTF-8 강제 로드
    return load_json(prob_path)

