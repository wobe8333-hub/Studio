"""
Google Trends 수집 소스
pytrends 라이브러리 기반 YouTube 검색 트렌드 수집
"""

from typing import Dict, Any, List


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

        # API 제한 고려해 최대 5개씩 처리
        for keyword in keywords[:5]:
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
                    demand_score[keyword] = 0.0
            except Exception:
                demand_score[keyword] = 0.0

        return {
            "demand_score": demand_score,
            "source": "google_trends",
            "pytrends_available": True,
            "error": None
        }

    except Exception as e:
        return {
            "demand_score": {},
            "source": "google_trends",
            "pytrends_available": True,
            "error": f"{type(e).__name__}: {str(e)}"
        }
