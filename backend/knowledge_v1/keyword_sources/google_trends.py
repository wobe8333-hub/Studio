"""
Google Trends (YouTube Search) - 수요 검증 및 우선순위
"""

import os
from typing import Dict, Any, List, Optional


def fetch_trends_scores(keywords: List[str], category: str) -> Dict[str, Any]:
    """
    Google Trends로 키워드별 수요 점수 추출
    
    Returns:
        {
            "demand_score": Dict[str, float],  # keyword -> score (0~1)
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
        pytrends = TrendReq(hl='en-US', tz=360)
        demand_score = {}
        
        # 키워드별 트렌드 조회 (배치 처리)
        for keyword in keywords[:5]:  # API 제한 고려
            try:
                pytrends.build_payload([keyword], cat=0, timeframe='today 12-m', geo='', gprop='youtube')
                data = pytrends.interest_over_time()
                
                if not data.empty:
                    # 평균 관심도 정규화 (0~1)
                    avg_interest = data[keyword].mean()
                    normalized = min(1.0, avg_interest / 100.0)
                    demand_score[keyword] = float(normalized)
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

