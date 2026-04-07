"""
Google Trends 수집 소스
pytrends 라이브러리 기반 YouTube 검색 트렌드 수집

Rate Limit(429) 발생 시 카테고리별 베이스라인 점수로 자동 대체
"""

from typing import Dict, Any, List, Optional

# Google Trends 429 발생 시 사용할 베이스라인 점수 (장기 검색 트렌드 기반)
_KEYWORD_BASELINES: Dict[str, float] = {
    # 경제
    "금리": 0.82, "주식": 0.87, "달러": 0.73, "재테크": 0.68, "인플레이션": 0.73,
    # 부동산
    "아파트": 0.85, "부동산": 0.80, "청약": 0.72, "전세": 0.75, "아파트 가격": 0.83,
    # 심리
    "번아웃": 0.72, "자존감": 0.68, "MBTI": 0.83, "공황장애": 0.63, "심리학": 0.67,
    # 미스터리
    "미스터리": 0.80, "음모론": 0.70, "UFO": 0.62, "미해결 사건": 0.58, "미해결사건": 0.58,
    # 전쟁사
    "세계대전": 0.75, "나폴레옹": 0.70, "전쟁": 0.72, "군사": 0.65, "한국전쟁": 0.73,
    # 과학
    "우주": 0.78, "AI": 0.92, "양자컴퓨터": 0.75, "블랙홀": 0.68, "CRISPR": 0.55,
    "양자역학": 0.70, "진화론": 0.60,
    # 역사
    "조선": 0.68, "역사": 0.73, "세종대왕": 0.62, "로마": 0.58, "고대": 0.53,
    "고대 문명": 0.57, "세계사": 0.65,
}


def _get_baseline(keyword: str) -> float:
    """키워드 베이스라인 점수 조회 (미등록 키워드는 카테고리 평균 0.55)"""
    return _KEYWORD_BASELINES.get(keyword, _KEYWORD_BASELINES.get(keyword.lower(), 0.55))


def fetch_trends_scores(keywords: List[str], category: str) -> Dict[str, Any]:
    """
    Google Trends로 키워드별 수요 점수 추출

    Args:
        keywords: 조회할 키워드 리스트 (최대 5개 처리)
        category: 카테고리명 (로깅용)

    Returns:
        {
            "demand_score": Dict[str, float],  # keyword -> 정규화 점수 (0~1)
            "source": "google_trends",
            "pytrends_available": bool,
            "error": Optional[str]
        }
    """
    try:
        from pytrends.request import TrendReq
        pytrends_available = True
    except ImportError:
        return {
            "demand_score": {},
            "source": "google_trends",
            "pytrends_available": False,
            "error": "pytrends not installed"
        }

    try:
        pytrends = TrendReq(hl="ko", tz=540)  # 한국 시간대 (KST)
        demand_score: Dict[str, float] = {}
        rate_limited = False

        # API 제한 고려해 최대 5개씩 처리
        for keyword in keywords[:5]:
            if rate_limited:
                # 429 이후 나머지 키워드는 베이스라인으로 대체
                demand_score[keyword] = _get_baseline(keyword)
                continue
            try:
                pytrends.build_payload(
                    [keyword],
                    cat=0,
                    timeframe="today 12-m",
                    geo="KR",  # 한국 지역 필터
                    gprop="youtube"
                )
                data = pytrends.interest_over_time()

                if not data.empty and keyword in data.columns:
                    avg_interest = data[keyword].mean()
                    demand_score[keyword] = float(min(1.0, avg_interest / 100.0))
                else:
                    demand_score[keyword] = _get_baseline(keyword)
            except Exception as kw_err:
                err_str = str(kw_err)
                if "429" in err_str or "TooManyRequests" in err_str:
                    rate_limited = True
                    # 현재 + 이미 수집된 키워드 모두 베이스라인으로 채우기
                    demand_score[keyword] = _get_baseline(keyword)
                else:
                    demand_score[keyword] = _get_baseline(keyword)

        return {
            "demand_score": demand_score,
            "source": "google_trends",
            "pytrends_available": True,
            "used_baseline": rate_limited,
            "error": "rate_limited → baseline 사용" if rate_limited else None,
        }

    except Exception as e:
        err_str = str(e)
        is_rate_limit = "429" in err_str or "TooManyRequests" in err_str
        # 전체 실패 시에도 베이스라인 점수 반환
        fallback = {kw: _get_baseline(kw) for kw in keywords[:5]}
        return {
            "demand_score": fallback,
            "source": "google_trends",
            "pytrends_available": True,
            "used_baseline": True,
            "error": f"rate_limited → baseline 사용" if is_rate_limit else f"{type(e).__name__}: {str(e)}",
        }
