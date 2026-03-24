"""
MEMORY DRIFT ENGINE - 지식 드리프트 감지 및 자동 격리
동일 topic embedding cosine similarity < 0.7이 3회 연속 발생 시 drift_flag=1
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple


DRIFT_THRESHOLD = 0.7  # cosine similarity 임계값
DRIFT_CONSECUTIVE_COUNT = 3  # 연속 발생 횟수
DRIFT_RATE_THRESHOLD = 0.3  # drift_rate > 0.3이면 weight 감소 70%


def detect_drift(
    topic: str,
    current_embedding: List[float],
    historical_embeddings: List[List[float]],
    drift_history: Optional[Dict[str, Any]] = None
) -> Tuple[bool, float, Dict[str, Any]]:
    """
    드리프트 감지
    
    Args:
        topic: 토픽
        current_embedding: 현재 임베딩 벡터
        historical_embeddings: 과거 임베딩 벡터 리스트
        drift_history: 드리프트 이력
        
    Returns:
        Tuple[bool, float, Dict[str, Any]]: (드리프트 여부, drift_rate, 드리프트 정보)
    """
    if not historical_embeddings:
        return False, 0.0, {}
    
    # cosine similarity 계산 (간단한 구현)
    similarities = []
    for hist_emb in historical_embeddings:
        sim = _cosine_similarity(current_embedding, hist_emb)
        similarities.append(sim)
    
    # 평균 similarity
    avg_similarity = sum(similarities) / len(similarities) if similarities else 0.0
    
    # drift_rate 계산 (1 - similarity)
    drift_rate = 1.0 - avg_similarity
    
    # 연속 발생 횟수 확인
    drift_history = drift_history or {}
    topic_history = drift_history.get(topic, {"consecutive_low": 0, "total_checks": 0})
    
    is_drift = avg_similarity < DRIFT_THRESHOLD
    if is_drift:
        topic_history["consecutive_low"] += 1
    else:
        topic_history["consecutive_low"] = 0
    
    topic_history["total_checks"] += 1
    topic_history["last_similarity"] = avg_similarity
    topic_history["last_drift_rate"] = drift_rate
    
    drift_flag = topic_history["consecutive_low"] >= DRIFT_CONSECUTIVE_COUNT
    
    drift_info = {
        "topic": topic,
        "drift_flag": drift_flag,
        "drift_rate": drift_rate,
        "avg_similarity": avg_similarity,
        "consecutive_low": topic_history["consecutive_low"],
        "total_checks": topic_history["total_checks"],
    }
    
    drift_history[topic] = topic_history
    
    return drift_flag, drift_rate, drift_info


def _cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    """Cosine similarity 계산"""
    if len(vec1) != len(vec2):
        return 0.0
    
    dot_product = sum(a * b for a, b in zip(vec1, vec2))
    magnitude1 = sum(a * a for a in vec1) ** 0.5
    magnitude2 = sum(b * b for b in vec2) ** 0.5
    
    if magnitude1 == 0 or magnitude2 == 0:
        return 0.0
    
    return dot_product / (magnitude1 * magnitude2)


def apply_drift_mitigation(
    source: str,
    drift_rate: float,
    current_weight: float
) -> float:
    """
    드리프트 완화 (drift_rate > 0.3이면 weight 감소 70%)
    
    Args:
        source: 소스
        drift_rate: 드리프트 비율
        current_weight: 현재 weight
        
    Returns:
        float: 조정된 weight
    """
    if drift_rate > DRIFT_RATE_THRESHOLD:
        return current_weight * 0.3  # 70% 감소
    return current_weight


def save_drift_index(drift_index: Dict[str, Any], repo_root: Path) -> Path:
    """드리프트 인덱스 저장"""
    governance_dir = repo_root / "data" / "knowledge_v1_store" / "governance"
    governance_dir.mkdir(parents=True, exist_ok=True)
    
    drift_path = governance_dir / "drift_index.json"
    with open(drift_path, "w", encoding="utf-8") as f:
        json.dump(drift_index, f, ensure_ascii=False, indent=2)
    
    return drift_path


def load_drift_index(repo_root: Path) -> Optional[Dict[str, Any]]:
    """드리프트 인덱스 로드"""
    drift_path = repo_root / "data" / "knowledge_v1_store" / "governance" / "drift_index.json"
    if not drift_path.exists():
        return {}
    
    with open(drift_path, "r", encoding="utf-8") as f:
        return json.load(f)

