"""STEP 05 — knowledge_store 통합 관리."""
import logging
from src.core.config import CHANNEL_CATEGORIES
from src.step05.trend_collector import (
    collect_trends, reinterpret_trend, save_knowledge,
    TRENDING_RATIO, EVERGREEN_RATIO,
)
from src.step05.evergreen_collector import get_evergreen_topics

logger = logging.getLogger(__name__)

def run_step05(channel_id: str, monthly_target: int = 10) -> list:
    """trending 60% / evergreen 25% / series 15% 비율로 topic 수집."""
    category = CHANNEL_CATEGORIES[channel_id]
    n_trend  = max(1, int(monthly_target * TRENDING_RATIO))
    n_ever   = max(1, int(monthly_target * EVERGREEN_RATIO))
    logger.info(f"[STEP05] {channel_id} trend={n_trend} evergreen={n_ever}")
    trends  = collect_trends(channel_id, category, limit=n_trend * 2)
    reint   = [reinterpret_trend(t, category, channel_id) for t in trends[:n_trend]]
    everg   = get_evergreen_topics(channel_id, category, count=n_ever)
    all_t   = reint + everg
    save_knowledge(channel_id, all_t)
    return all_t
