"""
네이버 Search API 소스 (Layer 1 — 실시간)
뉴스 / 블로그 / 지식iN 검색으로 한국어 트렌드 수집
"""

import json
import os
import urllib.request
from typing import Any, Dict, List, Tuple


def _load_credentials() -> Tuple[str, str]:
    return (
        os.getenv("NAVER_CLIENT_ID", "").strip(),
        os.getenv("NAVER_CLIENT_SECRET", "").strip(),
    )


def _naver_search(
    query: str,
    endpoint: str,
    client_id: str,
    client_secret: str,
    display: int = 20,
) -> List[Dict[str, str]]:
    """
    네이버 Search API 단일 호출

    endpoint: 'news' | 'blog' | 'kin'
    """
    from urllib.parse import quote
    url = (
        f"https://openapi.naver.com/v1/search/{endpoint}.json"
        f"?query={quote(query)}&display={display}&sort=date"
    )
    req = urllib.request.Request(url)
    req.add_header("X-Naver-Client-Id", client_id)
    req.add_header("X-Naver-Client-Secret", client_secret)

    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        return data.get("items", [])
    except Exception:
        return []


def fetch_naver_trends(
    keywords: List[str],
    category: str,
    endpoints: List[str] = None,
) -> Dict[str, Any]:
    """
    네이버 뉴스/블로그/지식iN 기반 트렌드 키워드 수집

    Args:
        keywords: 검색 키워드 리스트
        category: 채널 카테고리
        endpoints: 검색 대상 ('news', 'blog', 'kin')

    Returns:
        {
            "topics": List[str],       — 수집된 주제 키워드
            "scores": Dict[str, float],— 키워드별 빈도 점수 (0~1)
            "source": "naver",
            "configured": bool,
            "error": Optional[str]
        }
    """
    if endpoints is None:
        endpoints = ["news", "blog"]

    client_id, client_secret = _load_credentials()
    if not client_id or not client_secret:
        return {
            "topics": [],
            "scores": {},
            "source": "naver",
            "configured": False,
            "error": "NAVER_CLIENT_ID / NAVER_CLIENT_SECRET 미설정",
        }

    all_titles: List[str] = []
    errors: List[str] = []

    for keyword in keywords[:5]:
        for ep in endpoints:
            try:
                items = _naver_search(keyword, ep, client_id, client_secret, display=20)
                for item in items:
                    title = item.get("title", "").replace("<b>", "").replace("</b>", "").strip()
                    if title:
                        all_titles.append(title)
            except Exception as e:
                errors.append(f"{keyword}/{ep}: {e}")

    # 키워드 빈도 기반 점수화
    from collections import Counter
    word_counts: Counter = Counter()
    for title in all_titles:
        for kw in keywords:
            if kw in title:
                word_counts[kw] += 1

    scores: Dict[str, float] = {}
    if word_counts:
        max_count = max(word_counts.values())
        for kw, cnt in word_counts.items():
            scores[kw] = round(cnt / max_count, 3)

    # 제목에서 주제 추출 (단순 중복 제거)
    seen: set = set()
    topics: List[str] = []
    for title in all_titles:
        if title not in seen:
            seen.add(title)
            topics.append(title)

    return {
        "topics": topics[:50],
        "scores": scores,
        "source": "naver",
        "configured": True,
        "error": "; ".join(errors) if errors else None,
    }
