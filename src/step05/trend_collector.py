"""
STEP 05 — 5계층 트렌드 수집 오케스트레이터

Layer 1 (실시간 6h):  Google Trends + Naver
Layer 2 (일간 24h):   YouTube Trending + RSS
Layer 3 (주간 7d):    Reddit + Korean Community
Layer 4 (월간 30d):   arXiv + Semantic Scholar + NASA
Layer 5 (에버그린):   Wikipedia + Curated Pool

수집 → 점수화 → 자동승격(80+) / 리뷰대기(60~79) / 폐기(<60)
"""

import json
from typing import Dict, Any, List
from loguru import logger

from src.core.ssot import write_json, now_iso, sha256_dict
from src.core.config import KNOWLEDGE_DIR, CHANNEL_CATEGORIES
from src.step05.scorer import score_topic
from src.step05.dedup import deduplicate_topics

# 수집 비율 상수
TRENDING_RATIO = 0.60
EVERGREEN_RATIO = 0.25
SERIES_RATIO = 0.15
TREND_VALIDITY_DAYS = 7

# 카테고리별 주제 재해석 템플릿
_REINTERPRET_TEMPLATES: Dict[str, str] = {
    "economy":     "{keyword}의 작동 원리와 내 돈에 미치는 영향",
    "realestate":  "{keyword}가 부동산 시장에 미치는 영향",
    "psychology":  "{keyword}이 뇌에서 작동하는 방식",
    "mystery":     "{keyword}의 미스터리와 진실",
    "war_history": "{keyword}의 역사적 전개와 영향",
    "science":     "{keyword}의 과학적 원리",
    "history":     "{keyword}의 역사적 의미와 배경",
}


# ──────────────────────────────────────────────
# 내부 수집 함수 (계층별)
# ──────────────────────────────────────────────

def _collect_layer1(category: str) -> Dict[str, Any]:
    """Layer 1: Google Trends + Naver (실시간)"""
    topics: List[str] = []
    trends_scores: Dict[str, float] = {}

    # 카테고리별 검색 키워드 (config/trend_sources.json 기반)
    _GOOGLE_KW: Dict[str, List[str]] = {
        "economy": ["금리", "인플레이션", "주식", "달러", "재테크"],
        "realestate": ["아파트 가격", "청약", "전세", "부동산"],
        "psychology": ["번아웃", "자존감", "MBTI", "공황장애"],
        "mystery": ["미스터리", "음모론", "UFO", "미해결 사건"],
        "war_history": ["세계대전", "나폴레옹", "전쟁", "군사"],
        "science": ["우주", "AI", "양자컴퓨터", "블랙홀", "CRISPR"],
        "history": ["조선", "역사", "세종대왕", "로마", "고대"],
    }
    keywords = _GOOGLE_KW.get(category, [category])

    try:
        from src.step05.sources.google_trends import fetch_trends_scores
        result = fetch_trends_scores(keywords, category)
        demand = result.get("demand_score", {})
        if demand:
            trends_scores.update(demand)
            topics.extend(list(demand.keys())[:5])
    except Exception as e:
        logger.debug(f"[STEP05-L1] google_trends 수집 실패: {e}")

    try:
        from src.step05.sources.naver import fetch_naver_trends
        result = fetch_naver_trends(keywords, category)
        for t in result.get("topics", [])[:5]:
            topics.append(t)
    except Exception as e:
        logger.debug(f"[STEP05-L1] naver 수집 실패: {e}")

    return {"topics": topics, "trends_scores": trends_scores, "layer": 1}


def _collect_layer2(category: str) -> Dict[str, Any]:
    """Layer 2: YouTube Trending + RSS (일간)"""
    topics: List[str] = []
    news_scores: Dict[str, float] = {}

    try:
        from src.step05.sources.youtube_trending import fetch_youtube_trending
        result = fetch_youtube_trending(category)
        if result.get("configured"):
            # raw 영상 제목(topics) 대신 정제된 키워드(keywords) 사용
            topics.extend(result.get("keywords", [])[:8])
            # YouTube 빈도 점수를 news_scores에 연결 → interest_score 계산에 반영
            news_scores.update(result.get("scores", {}))
    except Exception as e:
        logger.debug(f"[STEP05-L2] youtube_trending 수집 실패: {e}")

    try:
        from src.step05.sources.rss import fetch_news_context
        _RSS_KW: Dict[str, List[str]] = {
            "economy": ["금리", "주식", "경제", "재테크"],
            "realestate": ["아파트", "부동산", "청약", "전세"],
            "psychology": ["심리학", "번아웃", "자존감", "스트레스"],
            "mystery": ["미스터리", "미해결사건", "음모론"],
            "war_history": ["전쟁", "세계대전", "군사역사"],
            "science": ["우주", "과학", "AI", "양자역학"],
            "history": ["역사", "조선", "세계사"],
        }
        rss_keywords = _RSS_KW.get(category, [category])
        kw_scores, _ = fetch_news_context(rss_keywords)
        news_scores.update(kw_scores)
        topics.extend(list(kw_scores.keys())[:5])
    except Exception as e:
        logger.debug(f"[STEP05-L2] rss 수집 실패: {e}")

    return {"topics": topics, "news_scores": news_scores, "layer": 2}


def _collect_layer3(category: str) -> Dict[str, Any]:
    """Layer 3: Reddit + Korean Community (주간)"""
    topics: List[str] = []
    community_scores: Dict[str, float] = {}

    try:
        from src.step05.sources.reddit import fetch_reddit_topics
        result = fetch_reddit_topics(category)
        if result.get("configured"):
            for t in result.get("topics", [])[:6]:
                topics.append(t)
            community_scores.update(result.get("scores", {}))
    except Exception as e:
        logger.debug(f"[STEP05-L3] reddit 수집 실패: {e}")

    try:
        from src.step05.sources.community import fetch_community_topics
        result = fetch_community_topics(category)
        topics.extend(result.get("topics", [])[:5])
    except Exception as e:
        logger.debug(f"[STEP05-L3] community 수집 실패: {e}")

    return {"topics": topics, "community_scores": community_scores, "layer": 3}


def _collect_layer4(category: str) -> Dict[str, Any]:
    """Layer 4: 학술/전문 소스 (월간, 카테고리 제한적)"""
    topics: List[str] = []

    # arXiv (과학 전용)
    try:
        from src.step05.sources.arxiv import fetch_arxiv_papers
        result = fetch_arxiv_papers(category)
        if result.get("applicable"):
            topics.extend(result.get("topics", [])[:5])
    except Exception as e:
        logger.debug(f"[STEP05-L4] arxiv 수집 실패: {e}")

    # Semantic Scholar (심리/과학)
    if category in ("psychology", "science", "history", "mystery", "war_history"):
        try:
            from src.step05.sources.scholar import fetch_scholar_papers
            result = fetch_scholar_papers(category)
            topics.extend(result.get("topics", [])[:5])
        except Exception as e:
            logger.debug(f"[STEP05-L4] scholar 수집 실패: {e}")

    # NASA (과학 전용)
    try:
        from src.step05.sources.nasa import fetch_nasa_data
        result = fetch_nasa_data(category)
        if result.get("applicable"):
            topics.extend(result.get("topics", [])[:5])
    except Exception as e:
        logger.debug(f"[STEP05-L4] nasa 수집 실패: {e}")

    return {"topics": topics, "layer": 4}


def _collect_layer5(category: str, limit: int = 10) -> Dict[str, Any]:
    """Layer 5: Wikipedia 확장 + 큐레이션 에버그린"""
    topics: List[str] = []

    try:
        from src.step05.sources.wikipedia import expand_keywords
        # 카테고리 한국어 대표 키워드로 Wikipedia 확장
        _category_seed_kw = {
            "economy": "경제", "realestate": "부동산",
            "psychology": "심리학", "mystery": "미스터리",
            "war_history": "전쟁", "science": "과학",
            "history": "역사",
        }
        seed_kw = _category_seed_kw.get(category, category)
        expanded, _ = expand_keywords([seed_kw], category, lang="ko")
        topics.extend(expanded[:5])
    except Exception as e:
        logger.debug(f"[STEP05-L5] wikipedia 수집 실패: {e}")

    try:
        from src.step05.sources.curated import fetch_curated_topics
        result = fetch_curated_topics(category, limit=limit)
        topics.extend(result.get("topics", []))
    except Exception as e:
        logger.debug(f"[STEP05-L5] curated 수집 실패: {e}")

    return {"topics": topics, "layer": 5}


# ──────────────────────────────────────────────
# 공개 API
# ──────────────────────────────────────────────

def collect_trends(channel_id: str, category: str, limit: int = 20) -> list:
    """
    5계층 소스에서 트렌드 주제 수집 후 점수화·분류

    Returns:
        점수순 정렬된 트렌드 dict 리스트 (grade: auto/review/rejected 포함)
    """
    logger.info(f"[STEP05] {channel_id} ({category}) 5계층 수집 시작")

    layer1 = _collect_layer1(category)
    layer2 = _collect_layer2(category)
    layer3 = _collect_layer3(category)
    layer4 = _collect_layer4(category)

    # 전체 후보 수집 (중복 제거)
    all_raw_topics: List[str] = []
    seen: set = set()
    for layer_data in (layer1, layer2, layer3, layer4):
        for t in layer_data.get("topics", []):
            if t and t not in seen:
                all_raw_topics.append(t)
                seen.add(t)

    # knowledge_store 기존 주제 중복 제거
    all_raw_topics = deduplicate_topics(channel_id, all_raw_topics)

    # 공급 부족 시 Layer 5(에버그린) 보충
    if len(all_raw_topics) < limit:
        shortfall = limit - len(all_raw_topics)
        layer5 = _collect_layer5(category, limit=shortfall + 5)
        for t in layer5.get("topics", []):
            if t and t not in seen:
                all_raw_topics.append(t)
                seen.add(t)
        all_raw_topics = deduplicate_topics(channel_id, all_raw_topics)

    # 점수화
    trends_scores = layer1.get("trends_scores", {})
    news_scores = layer2.get("news_scores", {})
    community_scores = layer3.get("community_scores", {})
    # Reddit/커뮤니티 미설정 시 뉴스 빈도를 커뮤니티 proxy로 활용 (0.6 감쇠)
    community_available = bool(community_scores)

    scored: List[dict] = []
    for topic in all_raw_topics:
        t_score = max(trends_scores.get(topic, 0.0), trends_scores.get(topic.lower(), 0.0))
        n_score = max(news_scores.get(topic, 0.0), news_scores.get(topic.lower(), 0.0))
        c_score = max(community_scores.get(topic, 0.0), community_scores.get(topic.lower(), 0.0))
        # 커뮤니티 점수 없으면 뉴스 점수의 60%를 proxy로 사용
        if not community_available and c_score == 0.0:
            c_score = round(n_score * 0.6, 3)

        result = score_topic(
            topic=topic,
            category=category,
            trends_score=t_score,
            news_score=n_score,
            community_score=c_score,
        )
        result["original_topic"] = topic
        result["collected_at"] = now_iso()
        scored.append(result)

    # 점수 내림차순 정렬
    scored.sort(key=lambda x: -x["score"])

    # 등급별 통계 로깅
    auto_count = sum(1 for s in scored if s["grade"] == "auto")
    review_count = sum(1 for s in scored if s["grade"] == "review")
    rejected_count = sum(1 for s in scored if s["grade"] == "rejected")
    logger.info(
        f"[STEP05] {channel_id} 수집 완료: 전체={len(scored)} "
        f"자동승격={auto_count} 리뷰대기={review_count} 거부={rejected_count}"
    )

    return scored[:limit]


def reinterpret_trend(trend: dict, category: str, channel_id: str) -> dict:
    """
    트렌드 주제를 귀여운 애니메이션 영상 제목으로 재해석

    Args:
        trend: score_topic() 또는 collect_trends() 반환 dict
        category: 채널 카테고리
        channel_id: CH1~CH7

    Returns:
        영상 제작용 주제 dict
    """
    template = _REINTERPRET_TEMPLATES.get(category, "{keyword}의 원리")
    keyword = trend.get("original_topic") or trend.get("topic", "")
    # 제목이 너무 길면 잘라내기
    if len(keyword) > 30:
        keyword = keyword[:30]

    return {
        "original_trend": trend,
        "reinterpreted_title": template.format(keyword=keyword),
        "category": category,
        "channel_id": channel_id,
        "is_trending": True,
        "score": trend.get("score", 0.0),
        "grade": trend.get("grade", "review"),
        "breakdown": trend.get("breakdown"),
        "trend_collected_at": trend.get("collected_at", now_iso()),
        "trend_validity_days": TREND_VALIDITY_DAYS,
        "topic_type": "trending",
    }


def save_knowledge(channel_id: str, topics: list) -> None:
    """수집된 주제 목록을 knowledge_store에 저장"""
    raw_dir = KNOWLEDGE_DIR / channel_id / "discovery" / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)

    with open(raw_dir / "assets.jsonl", "w", encoding="utf-8") as f:
        for t in topics:
            f.write(json.dumps(t, ensure_ascii=True) + "\n")

    report_dir = KNOWLEDGE_DIR / channel_id / "reports"
    report_dir.mkdir(parents=True, exist_ok=True)

    write_json(report_dir / "gate_stats.json", {
        "collected_at": now_iso(),
        "channel_id": channel_id,
        "total_topics": len(topics),
        "trending_count": sum(1 for t in topics if t.get("is_trending")),
        "evergreen_count": sum(1 for t in topics if t.get("topic_type") == "evergreen"),
        "assets_sha256": sha256_dict({"topics": topics}),
    })

    logger.info(f"[STEP05] {channel_id}: {len(topics)}개 topic 저장 완료")
