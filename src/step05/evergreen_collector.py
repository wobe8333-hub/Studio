"""STEP 05 — 에버그린 topic 수집."""
import logging
from src.core.ssot import now_iso

logger = logging.getLogger(__name__)

EVERGREEN_POOL = {
    "경제_재테크":["복리의 원리","인플레이션이란 무엇인가","달러와 원화의 관계",
                   "주식 시장이 작동하는 방법","금리가 경제에 미치는 영향",
                   "ETF와 펀드의 차이","채권이란 무엇인가","중앙은행의 역할"],
    "건강_의학":  ["수면이 뇌에 미치는 영향","면역 시스템 작동 원리",
                   "당분이 몸에서 처리되는 과정","스트레스가 신체에 미치는 영향",
                   "장 건강과 뇌의 연결","운동이 뇌를 바꾸는 방법"],
    "심리_행동":  ["확증 편향이란 무엇인가","도파민과 동기부여의 관계",
                   "손실 회피 심리","사회적 증거 효과","습관 형성의 원리",
                   "인지 부조화란 무엇인가"],
    "부동산_경매":["경매 낙찰 과정 전체","전세 제도의 원리","아파트 가격 결정 요인",
                   "임차인 권리 보호 방법","부동산 등기부등본 읽는 법"],
    "AI_테크":    ["트랜스포머 아키텍처 원리","GPT가 텍스트를 생성하는 방법",
                   "머신러닝과 딥러닝의 차이","AI 학습 데이터의 역할",
                   "강화학습이란 무엇인가"],
}

def get_evergreen_topics(channel_id: str, category: str, count: int = 3) -> list:
    pool   = EVERGREEN_POOL.get(category, [])
    topics = [{"reinterpreted_title": title, "category": category,
                "channel_id": channel_id, "is_trending": False,
                "topic_type": "evergreen", "created_at": now_iso()}
               for title in pool[:count]]
    logger.info(f"[STEP05] {channel_id} evergreen {len(topics)}개")
    return topics
