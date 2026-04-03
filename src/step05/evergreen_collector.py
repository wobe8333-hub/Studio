"""STEP 05 — 에버그린 topic 수집.

Layer 5 (상시): 카테고리별 큐레이션된 영구 주제 풀에서 수집.
실시간 소스에서 주제가 부족할 때 폴백으로 활용.
"""

from loguru import logger
from src.core.ssot import now_iso
from src.step05.sources.curated import fetch_curated_topics
from src.step05.dedup import deduplicate_topics

# 카테고리 → 에버그린 수집 비율 (월간 편수 기준)
EVERGREEN_RATIO = 0.25  # 25%


def get_evergreen_topics(channel_id: str, category: str, count: int = 3) -> list:
    """
    에버그린 주제 수집 (Layer 5 큐레이션 풀 기반)

    Args:
        channel_id: 채널 ID (CH1~CH7)
        category: economy / realestate / psychology / mystery / war_history / science / history
        count: 반환할 주제 수

    Returns:
        주제 dict 리스트 (reinterpreted_title, category, channel_id, is_trending, topic_type, created_at)
    """
    result = fetch_curated_topics(category, limit=count * 3, shuffle=True)
    pool_topics = result.get("topics", [])

    # 중복 제거
    unique_topics = deduplicate_topics(channel_id, pool_topics)

    topics = [
        {
            "reinterpreted_title": title,
            "category": category,
            "channel_id": channel_id,
            "is_trending": False,
            "topic_type": "evergreen",
            "source": "curated",
            "created_at": now_iso(),
        }
        for title in unique_topics[:count]
    ]

    logger.info(f"[STEP05] {channel_id} evergreen {len(topics)}개 (풀={result.get('total_pool', 0)})")
    return topics
