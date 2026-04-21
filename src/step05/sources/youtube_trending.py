"""
YouTube Data API v3 트렌딩 소스 (Layer 2 — 일간)
카테고리별 경쟁 채널 인기 영상 분석으로 트렌드 키워드 추출
"""

import os
import re
from collections import Counter
from typing import Any, Dict, List

# 7채널 카테고리별 YouTube 검색 키워드 (경쟁 채널 분석용)
_CATEGORY_SEARCH_TERMS: Dict[str, List[str]] = {
    "economy":     ["경제 설명", "금리 분석", "주식 전망", "재테크 방법"],
    "realestate":  ["아파트 분석", "부동산 투자", "청약 방법", "전세 시세"],
    "psychology":  ["심리학 실험", "번아웃 극복", "자존감 높이기", "인간관계"],
    "mystery":     ["미해결 사건", "음모론 진실", "미스터리 사건", "도시전설"],
    "war_history": ["2차 세계대전", "전쟁사 설명", "한국전쟁 진실", "나폴레옹"],
    "science":     ["우주 신비", "양자역학 쉽게", "블랙홀 설명", "진화론"],
    "history":     ["조선 역사", "고대 문명", "세계사 설명", "역사 인물"],
}


def _load_api_key() -> str:
    return os.getenv("YOUTUBE_API_KEY", "").strip()


def _search_videos(query: str, api_key: str, max_results: int = 10) -> List[Dict[str, Any]]:
    """YouTube Data API v3 search.list 호출"""
    import json
    import urllib.parse
    import urllib.request

    params = urllib.parse.urlencode({
        "part": "snippet",
        "q": query,
        "type": "video",
        "order": "viewCount",
        "regionCode": "KR",
        "maxResults": max_results,
        "key": api_key,
    })
    url = f"https://www.googleapis.com/youtube/v3/search?{params}"
    req = urllib.request.Request(url)

    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        return data.get("items", [])
    except Exception:
        return []


def _extract_keywords(title: str) -> List[str]:
    """영상 제목에서 의미 있는 키워드 추출 (2~6글자 단어)"""
    # 특수문자/숫자/조사 제거 후 단어 분리
    cleaned = re.sub(r"[^\w\s]", " ", title)
    words = [w for w in cleaned.split() if 2 <= len(w) <= 10]
    # 흔한 불용어 제거
    stopwords = {"이유", "방법", "의미", "이것", "그것", "하지만", "그리고", "또한"}
    # 순수 숫자 키워드 제거 (예: "39", "2024" 등)
    return [w for w in words if w not in stopwords and not w.isdigit()]


def fetch_youtube_trending(
    category: str,
    quota_cost: int = 100,
) -> Dict[str, Any]:
    """
    YouTube 경쟁 채널 인기 영상 제목 기반 트렌드 키워드 수집

    Args:
        category: 채널 카테고리
        quota_cost: 이 호출에 사용할 최대 YouTube API 쿼터 유닛

    Returns:
        {
            "topics": List[str],       — 영상 제목 리스트
            "keywords": List[str],     — 추출된 핵심 키워드
            "scores": Dict[str, float],
            "source": "youtube_trending",
            "configured": bool,
            "error": Optional[str]
        }
    """
    api_key = _load_api_key()
    if not api_key:
        return {
            "topics": [],
            "keywords": [],
            "scores": {},
            "source": "youtube_trending",
            "configured": False,
            "error": "YOUTUBE_API_KEY 미설정",
        }

    search_terms = _CATEGORY_SEARCH_TERMS.get(category, [f"{category} 설명"])
    titles: List[str] = []
    errors: List[str] = []
    keyword_counter: Counter = Counter()

    for term in search_terms[:2]:  # 쿼터 절약: 최대 2개 검색어
        items = _search_videos(term, api_key, max_results=5)
        for item in items:
            title = item.get("snippet", {}).get("title", "")
            if title:
                titles.append(title)
                for kw in _extract_keywords(title):
                    keyword_counter[kw] += 1

    # 상위 키워드 점수화
    scores: Dict[str, float] = {}
    if keyword_counter:
        max_cnt = max(keyword_counter.values())
        for kw, cnt in keyword_counter.most_common(20):
            scores[kw] = round(cnt / max_cnt, 3)

    return {
        "topics": titles[:30],
        "keywords": list(scores.keys()),
        "scores": scores,
        "source": "youtube_trending",
        "configured": True,
        "error": "; ".join(errors) if errors else None,
    }
