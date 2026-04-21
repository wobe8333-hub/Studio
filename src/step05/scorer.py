"""
주제 점수화 엔진
관심도(40%) + 적합도(25%) + 수익성(20%) + 긴급도(15%) 종합 점수 계산
"""

from typing import Any, Dict, List, Optional

# 채널별 RPM 프록시 (원화 기준, 한국 YouTube 교육 카테고리 실측 기반)
_CHANNEL_RPM: Dict[str, int] = {
    "economy": 7000,
    "realestate": 7000,    # 부동산 CPM 경제급으로 상향 (투자·재테크 광고)
    "psychology": 4500,
    "mystery": 4000,
    "war_history": 5000,   # 역사·교육 카테고리 CPM 상향
    "science": 4500,
    "history": 4500,
}

# 카테고리별 귀여운 애니메이션 변환 적합도 기본값 (0~1)
# 애니메이션으로 시각화·캐릭터화가 용이할수록 높은 값
_ANIMATION_FIT: Dict[str, float] = {
    "economy": 0.7,
    "realestate": 0.75,    # 부동산 그래프·지도·캐릭터 설명에 적합
    "psychology": 0.9,
    "mystery": 0.95,
    "war_history": 0.85,   # 전쟁사 캐릭터화·지도 애니메이션에 매우 적합
    "science": 0.95,
    "history": 0.9,
}

# 검색 필터링용 불용어
_STOPWORDS = {"the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", "of", "with", "by"}


def _normalize_keyword(keyword: str) -> Optional[str]:
    """키워드 소문자 정규화 + 불용어 제거 (3자 미만 제외)"""
    kw = keyword.strip().lower()
    if len(kw) < 2:
        return None
    words = [w for w in kw.split() if w not in _STOPWORDS]
    return " ".join(words) if words else None


def score_topic(
    topic: str,
    category: str,
    trends_score: float = 0.0,
    news_score: float = 0.0,
    community_score: float = 0.0,
    is_evergreen: bool = False,
    days_since_trending: int = 0,
) -> Dict[str, Any]:
    """
    단일 주제에 대한 종합 점수 계산

    점수 공식:
        score = interest(40%) + fit(25%) + revenue(20%) + urgency(15%)

    Args:
        topic: 주제명
        category: 채널 카테고리
        trends_score: Google Trends / 검색량 점수 (0~1)
        news_score: 뉴스 RSS 빈도 점수 (0~1)
        community_score: Reddit / 커뮤니티 점수 (0~1)
        is_evergreen: 에버그린 주제 여부
        days_since_trending: 트렌딩 시작 후 경과 일수 (낮을수록 긴급)

    Returns:
        {
            "topic": str,
            "category": str,
            "score": float (0~100),
            "grade": str ("auto"(80+) / "review"(60~79) / "rejected"(<60)),
            "breakdown": {interest, fit, revenue, urgency},
        }
    """
    # 1. 관심도 점수 (40%) — 트렌드 + 뉴스 + 커뮤니티 가중 평균
    raw_interest = (trends_score * 0.5 + news_score * 0.3 + community_score * 0.2)
    interest_score = min(1.0, raw_interest)

    # 2. 적합도 점수 (25%) — 카테고리별 애니메이션 변환 가능성
    fit_score = _ANIMATION_FIT.get(category, 0.7)

    # 3. 수익성 점수 (20%) — RPM 정규화 (최대 7000원 기준)
    rpm = _CHANNEL_RPM.get(category, 4000)
    revenue_score = min(1.0, rpm / 7000.0)

    # 4. 긴급도 점수 (15%) — 에버그린은 낮음, 신규 트렌드는 높음
    if is_evergreen:
        urgency_score = 0.3  # 에버그린은 항상 적당한 긴급도
    elif days_since_trending <= 3:
        urgency_score = 1.0
    elif days_since_trending <= 7:
        urgency_score = 0.8
    elif days_since_trending <= 14:
        urgency_score = 0.5
    else:
        urgency_score = 0.2

    # 종합 점수 (0~100)
    raw_score = (
        interest_score * 0.40
        + fit_score * 0.25
        + revenue_score * 0.20
        + urgency_score * 0.15
    )
    final_score = round(raw_score * 100, 1)

    # 등급 분류
    if final_score >= 80:
        grade = "auto"      # 자동 승격
    elif final_score >= 60:
        grade = "review"    # 인간 리뷰 대기
    else:
        grade = "rejected"  # 폐기

    return {
        "topic": topic,
        "category": category,
        "score": final_score,
        "grade": grade,
        "breakdown": {
            "interest": round(interest_score * 100, 1),
            "fit": round(fit_score * 100, 1),
            "revenue": round(revenue_score * 100, 1),
            "urgency": round(urgency_score * 100, 1),
        }
    }


def score_keywords(
    candidate_keywords: List[str],
    demand_score: Dict[str, float],
    evidence_snapshot: List[str],
    performance_hint: Optional[Dict[str, float]] = None,
) -> List[Dict[str, Any]]:
    """
    키워드 배치 점수화 (backend/keyword_discovery_engine.py의 _score_keywords 기반)

    Args:
        candidate_keywords: 후보 키워드 리스트
        demand_score: Google Trends 수요 점수 (keyword -> 0~1)
        evidence_snapshot: 데이터셋 키워드 리스트 (존재하면 +보너스)
        performance_hint: 과거 성과 힌트 (keyword -> 0~1), 없으면 {}

    Returns:
        final_score 내림차순 정렬된 스코어 결과 리스트
    """
    if performance_hint is None:
        performance_hint = {}

    evidence_set = {_normalize_keyword(k) for k in evidence_snapshot if _normalize_keyword(k)}
    scored: List[Dict[str, Any]] = []

    for kw in candidate_keywords:
        kw_norm = _normalize_keyword(kw)
        if not kw_norm:
            continue

        score = 0.0
        sources_count = 0

        # YouTube 후보 존재: +3
        score += 3.0
        sources_count += 1

        # Trends 점수: +(2 * trends_val)
        trends_val = demand_score.get(kw, demand_score.get(kw_norm, 0.0))
        if trends_val > 0:
            score += 2.0 * trends_val
            sources_count += 1

        # 데이터셋 존재 여부: +1
        if kw_norm in evidence_set:
            score += 1.0
            sources_count += 1

        # 과거 성과 힌트: +(1 * hint_val)
        hint_val = performance_hint.get(kw, performance_hint.get(kw_norm, 0.0))
        if hint_val > 0:
            score += 1.0 * hint_val
            sources_count += 1

        scored.append({
            "keyword": kw_norm,
            "original": kw,
            "final_score": round(score, 3),
            "sources_count": sources_count,
            "trends_score": trends_val,
            "dataset_present": kw_norm in evidence_set,
            "analytics_hint": hint_val
        })

    # final_score 내림차순, 동점이면 keyword 사전순
    scored.sort(key=lambda x: (-x["final_score"], x["keyword"]))
    return scored
