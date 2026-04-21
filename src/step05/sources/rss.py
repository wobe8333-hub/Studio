"""
RSS 뉴스 수집 소스
Google News RSS 기반 키워드 뉴스 컨텍스트 수집
"""

import os
import urllib.request
from collections import Counter
from typing import Any, Dict, List, Tuple
from urllib.parse import quote


def _normalize(keyword: str) -> str:
    """키워드 소문자 정규화"""
    return keyword.strip().lower()


def fetch_news_context(
    keywords: List[str],
    lookback_days: int = 7,
    max_items: int = 50,
    lang: str = "ko"
) -> Tuple[Dict[str, float], Dict[str, Any]]:
    """
    Google News RSS로 뉴스 컨텍스트 수집

    Args:
        keywords: 검색 키워드 리스트 (최대 10개 처리)
        lookback_days: 조회 기간 (현재 미사용, 향후 확장용)
        max_items: 수집할 최대 기사 수
        lang: 언어 코드 ("ko"=한국어, "en"=영어)

    Returns:
        (keyword_scores, snapshot)
        keyword_scores: Dict[str, float] — 키워드별 정규화 빈도 점수 (0~1)
        snapshot: {ok, provider, items_count, top_headlines, errors}
    """
    try:
        import feedparser
    except ImportError:
        return {}, {
            "ok": False,
            "provider": "rss",
            "items_count": 0,
            "top_headlines": [],
            "errors": [{"message": "feedparser not installed"}]
        }

    if not keywords:
        return {}, {
            "ok": False,
            "provider": "rss",
            "items_count": 0,
            "top_headlines": [],
            "errors": [{"message": "no keywords provided"}]
        }

    keyword_counts: Counter = Counter()
    top_headlines: List[Dict[str, str]] = []
    errors: List[Dict[str, str]] = []

    # 언어별 RSS 파라미터 설정
    if lang == "ko":
        hl, gl, ceid = "ko", "KR", "KR:ko"
    else:
        hl, gl, ceid = "en-US", "US", "US:en"

    timeout_sec = int(os.getenv("NEWS_RSS_TIMEOUT_SECONDS", "10"))

    for keyword in keywords[:10]:
        try:
            query = quote(_normalize(keyword))
            url = f"https://news.google.com/rss/search?q={query}&hl={hl}&gl={gl}&ceid={ceid}"

            req = urllib.request.Request(url)
            req.add_header(
                "User-Agent",
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            )

            try:
                with urllib.request.urlopen(req, timeout=timeout_sec) as resp:
                    feed = feedparser.parse(resp.read())
            except Exception as net_err:
                errors.append({
                    "keyword": keyword,
                    "message": f"{type(net_err).__name__}: {str(net_err)}",
                    "exception_type": type(net_err).__name__
                })
                continue

            if feed.bozo and feed.bozo_exception:
                errors.append({
                    "keyword": keyword,
                    "message": f"RSS parse error: {type(feed.bozo_exception).__name__}"
                })
                continue

            for entry in feed.get("entries", [])[:max_items]:
                title = entry.get("title", "")
                link = entry.get("link", "")
                published = entry.get("published", "")

                if _normalize(keyword) in _normalize(title):
                    keyword_counts[keyword] += 1

                if len(top_headlines) < max_items:
                    headline = {"title": title[:200], "link": link, "published": published}
                    if headline not in top_headlines:
                        top_headlines.append(headline)

        except Exception as e:
            errors.append({"keyword": keyword, "message": f"{type(e).__name__}: {str(e)}"})

    # 점수 정규화 (0~1)
    keyword_scores: Dict[str, float] = {}
    if keyword_counts:
        max_count = max(keyword_counts.values())
        for kw, count in keyword_counts.items():
            keyword_scores[kw] = float(count) / max_count if max_count > 0 else 0.0

    return keyword_scores, {
        "ok": bool(top_headlines or keyword_scores),
        "provider": "rss",
        "items_count": len(top_headlines),
        "top_headlines": top_headlines[:max_items],
        "errors": errors
    }
