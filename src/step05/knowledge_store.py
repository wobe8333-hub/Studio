"""STEP 05 — knowledge_store 통합 관리.

trend_collector + evergreen_collector를 오케스트레이션하여
월간 콘텐츠 주제 목록을 생성하고 저장합니다.

Phase 4 추가:
  collect_knowledge(topic, category, channel_id) — 3단계 지식 수집 파이프라인
  (Stage1: AI 초벌 → Stage2: 구조화 보강 → Stage3: 팩트체크)
"""

from loguru import logger

from src.core.config import CHANNEL_CATEGORIES
from src.step05.evergreen_collector import EVERGREEN_RATIO, get_evergreen_topics
from src.step05.trend_collector import collect_trends, reinterpret_trend, save_knowledge

TRENDING_RATIO = 0.60   # 60% 트렌딩
# EVERGREEN_RATIO = 0.25 (evergreen_collector에서 가져옴)
# 나머지 15%는 시리즈 (Step15에서 관리)


def collect_knowledge(topic: str, category: str, channel_id: str) -> dict:
    """
    Phase 4 — 3단계 지식 수집 파이프라인

    Stage 1: Tavily + Perplexity + Gemini Deep Research
    Stage 2: Wikipedia + Semantic Scholar + Naver
    Stage 3: 팩트체크 + 카테고리 보강

    Args:
        topic: 영상 주제 (예: "금리 인하의 경제적 영향")
        category: 카테고리 (예: "economy")
        channel_id: 채널 ID (예: "CH1")

    Returns:
        KnowledgePackage를 dict로 직렬화한 결과
    """
    from src.step05.knowledge.category_enricher import enrich_by_category
    from src.step05.knowledge.knowledge_package import (
        build_empty_package,
        package_to_dict,
        save_package,
    )
    from src.step05.knowledge.stage1_research import stage1_research
    from src.step05.knowledge.stage2_enrich import stage2_enrich
    from src.step05.knowledge.stage3_factcheck import stage3_factcheck

    logger.info(f"[KnowledgeStore] '{topic}' ({category}) 3단계 수집 시작")

    pkg = build_empty_package(topic, category, channel_id)

    # Stage 1: AI 초벌 리서치
    pkg = stage1_research(pkg)

    # Stage 2: 구조화 보강
    pkg = stage2_enrich(pkg)

    # Stage 3: 팩트체크 + 카테고리 전문 보강
    pkg = stage3_factcheck(pkg)
    pkg = enrich_by_category(pkg)

    # 저장
    out_path = save_package(pkg)
    logger.info(f"[KnowledgeStore] '{topic}' 저장 완료: {out_path}")

    return package_to_dict(pkg)


def run_step05(channel_id: str, monthly_target: int = 10) -> list:
    """
    trending 60% / evergreen 25% / series 15% 비율로 topic 수집.

    Args:
        channel_id: CH1~CH7
        monthly_target: 월간 목표 편수 (기본 10편)

    Returns:
        주제 dict 리스트
    """
    category = CHANNEL_CATEGORIES[channel_id]
    n_trend = max(1, int(monthly_target * TRENDING_RATIO))
    n_ever = max(1, int(monthly_target * EVERGREEN_RATIO))
    logger.info(f"[STEP05] {channel_id} ({category}) trend={n_trend} evergreen={n_ever}")

    trends = collect_trends(channel_id, category, limit=n_trend * 2)
    reint = [reinterpret_trend(t, category, channel_id) for t in trends[:n_trend]]
    everg = get_evergreen_topics(channel_id, category, count=n_ever)

    all_t = reint + everg
    save_knowledge(channel_id, all_t)
    logger.info(f"[STEP05] {channel_id} 총 {len(all_t)}개 주제 저장 완료")
    return all_t
