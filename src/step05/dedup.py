"""
주제 중복 검사 모듈
knowledge_store에 이미 제작된 주제와 신규 후보 주제를 비교하여 중복 제거
"""

import re
from typing import List, Set

from loguru import logger

from src.core.config import DATA_DIR
from src.core.ssot import read_json


def _normalize(text: str) -> str:
    """비교용 문자열 정규화: 소문자, 공백/특수문자 제거"""
    text = text.lower()
    text = re.sub(r"[^\w가-힣]", "", text)
    return text


def _load_existing_topics(channel_id: str) -> Set[str]:
    """knowledge_store에서 기존 주제 목록 로드"""
    store_dir = DATA_DIR / "knowledge_store" / channel_id
    if not store_dir.exists():
        return set()

    existing: Set[str] = set()
    # glob("*.json") → glob("**/*.json") : packages/ 하위 재귀 탐색
    for json_file in store_dir.glob("**/*.json"):
        try:
            data = read_json(json_file)
            # 단일 주제 파일
            if "topic" in data:
                existing.add(_normalize(data["topic"]))
            # 주제 목록 파일
            if "topics" in data:
                for t in data["topics"]:
                    if isinstance(t, str):
                        existing.add(_normalize(t))
                    elif isinstance(t, dict) and "reinterpreted_title" in t:
                        existing.add(_normalize(t["reinterpreted_title"]))
            # knowledge_package.py 형식: 루트에 reinterpreted_title
            if "reinterpreted_title" in data:
                existing.add(_normalize(data["reinterpreted_title"]))
        except Exception:
            pass

    return existing


def _similarity(a: str, b: str) -> float:
    """간단한 문자 n-gram 유사도 (2-gram)"""
    def ngrams(s: str, n: int = 2) -> Set[str]:
        return {s[i:i+n] for i in range(len(s) - n + 1)} if len(s) >= n else {s}

    na, nb = ngrams(a), ngrams(b)
    if not na or not nb:
        return 0.0
    intersection = na & nb
    union = na | nb
    return len(intersection) / len(union)


def deduplicate_topics(
    channel_id: str,
    candidates: List[str],
    similarity_threshold: float = 0.75,
) -> List[str]:
    """
    기존 knowledge_store 주제와 중복되는 후보 주제 필터링

    Args:
        channel_id: 채널 ID (CH1~CH7)
        candidates: 신규 주제 후보 목록
        similarity_threshold: 이 값 이상이면 중복으로 판단 (기본 0.75)

    Returns:
        중복 제거된 주제 목록
    """
    existing = _load_existing_topics(channel_id)
    if not existing:
        return candidates

    result: List[str] = []
    removed = 0

    for candidate in candidates:
        norm_candidate = _normalize(candidate)
        is_dup = False

        for existing_topic in existing:
            if _similarity(norm_candidate, existing_topic) >= similarity_threshold:
                is_dup = True
                break

        if not is_dup:
            result.append(candidate)
        else:
            removed += 1

    if removed:
        logger.debug(f"[DEDUP] {channel_id}: {removed}개 중복 제거 → {len(result)}개 통과")

    return result


def is_duplicate(
    channel_id: str,
    topic: str,
    similarity_threshold: float = 0.75,
) -> bool:
    """단일 주제 중복 여부 확인"""
    existing = _load_existing_topics(channel_id)
    norm = _normalize(topic)
    for existing_topic in existing:
        if _similarity(norm, existing_topic) >= similarity_threshold:
            return True
    return False
