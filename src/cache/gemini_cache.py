"""
Gemini API 응답 캐시 (diskcache 기반)
TTL 24시간, 자동 만료, 크기 제한 500MB
"""

import hashlib
import time
from pathlib import Path
from typing import Optional

import diskcache

from src.core.config import CACHE_DIR
from src.quota.gemini_quota import record_cache_hit, record_cache_miss

# diskcache 저장 경로 및 설정
_CACHE_PATH = CACHE_DIR / "diskcache"
_CACHE = diskcache.Cache(
    directory=str(_CACHE_PATH),
    size_limit=500 * 1024 * 1024,  # 500MB
)

TTL_SECONDS = 24 * 3600  # 24시간
CACHEABLE_TYPES = ["system_prompt", "style_template", "affiliate_insert_template"]


def _make_key(prompt_type: str, content: str) -> str:
    """캐시 키 생성 (SHA-256 앞 16자)"""
    return hashlib.sha256(f"{prompt_type}::{content}".encode()).hexdigest()[:16]


def get(prompt_type: str, content: str) -> Optional[str]:
    """
    캐시에서 응답 조회

    Args:
        prompt_type: CACHEABLE_TYPES 중 하나
        content: 프롬프트 내용

    Returns:
        캐시 히트 시 응답 문자열, 미스 시 None
    """
    if prompt_type not in CACHEABLE_TYPES:
        return None

    key = _make_key(prompt_type, content)
    entry = _CACHE.get(key)

    if entry is None:
        record_cache_miss()
        return None

    record_cache_hit(cost_saved_krw=entry.get("cost_saved_krw", 0.0))
    return entry["response"]


def set(prompt_type: str, content: str, response: str, cost_krw: float = 0.0) -> None:
    """
    응답을 캐시에 저장 (TTL 24시간)

    Args:
        prompt_type: CACHEABLE_TYPES 중 하나
        content: 프롬프트 내용
        response: 저장할 응답 문자열
        cost_krw: 절감 비용 (원화, 통계용)
    """
    if prompt_type not in CACHEABLE_TYPES:
        return

    key = _make_key(prompt_type, content)
    entry = {
        "prompt_type": prompt_type,
        "created_at": time.time(),
        "response": response,
        "cost_saved_krw": cost_krw,
    }
    _CACHE.set(key, entry, expire=TTL_SECONDS)


def invalidate_expired() -> int:
    """
    만료된 캐시 항목 제거 (diskcache는 자동 처리하지만 수동 트리거도 지원)

    Returns:
        제거된 항목 수
    """
    expired = _CACHE.expire()
    return expired if isinstance(expired, int) else 0
