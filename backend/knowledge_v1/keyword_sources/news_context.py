"""
News Context (Google News RSS)
"""

import re
import feedparser
import os
import urllib.request
from datetime import datetime, timedelta
from typing import List, Dict, Any, Tuple
from collections import Counter
from urllib.parse import quote


def _normalize_keyword(keyword: str) -> str:
    """키워드 정규화 (검색용)"""
    return keyword.strip().lower()


def fetch_news_context(
    keywords: List[str],
    lookback_days: int = 7,
    max_items: int = 50
) -> Tuple[Dict[str, float], Dict[str, Any]]:
    """
    Google News RSS로 뉴스 컨텍스트 수집
    
    Args:
        keywords: 검색 키워드 리스트
        lookback_days: 조회 기간 (일)
        max_items: 최대 아이템 수
    
    Returns:
        (keyword_scores: Dict[str, float], snapshot: Dict[str, Any])
    """
    keyword_scores = {}
    top_headlines = []
    errors = []
    
    if not keywords:
        return {}, {
            "ok": False,
            "provider": "rss",
            "items_count": 0,
            "top_headlines": [],
            "errors": [{"message": "no keywords provided"}]
        }
    
    # 각 키워드로 RSS 검색
    keyword_counts = Counter()
    
    # timeout 설정 (환경변수 우선, 기본 10초)
    timeout_sec = int(os.getenv("NEWS_RSS_TIMEOUT_SECONDS", "10"))
    
    for keyword in keywords[:10]:  # 최대 10개 키워드만
        try:
            # Google News RSS URL
            query = quote(_normalize_keyword(keyword))
            url = f"https://news.google.com/rss/search?q={query}&hl=en-US&gl=US&ceid=US:en"
            
            # urllib.request로 timeout + user-agent 지정 후 feedparser.parse(bytes)
            req = urllib.request.Request(url)
            req.add_header("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
            
            try:
                with urllib.request.urlopen(req, timeout=timeout_sec) as response:
                    feed_bytes = response.read()
                    feed = feedparser.parse(feed_bytes)
            except Exception as net_err:
                # 네트워크/timeout 예외 발생 시 errors에 기록하고 fixtures fallback으로 진행
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
            
            entries = feed.get("entries", [])[:max_items]
            
            for entry in entries:
                title = entry.get("title", "")
                link = entry.get("link", "")
                published = entry.get("published", "")
                
                # 키워드 빈도 계산 (제목에 포함된 경우)
                if _normalize_keyword(keyword) in _normalize_keyword(title):
                    keyword_counts[keyword] += 1
                
                # 헤드라인 수집 (중복 제거)
                if len(top_headlines) < max_items:
                    headline = {
                        "title": title[:200],
                        "link": link,
                        "published": published
                    }
                    if headline not in top_headlines:
                        top_headlines.append(headline)
            
        except Exception as e:
            errors.append({
                "keyword": keyword,
                "message": f"{type(e).__name__}: {str(e)}"
            })
    
    # 점수 정규화 (0~1)
    if keyword_counts:
        max_count = max(keyword_counts.values())
        for keyword, count in keyword_counts.items():
            keyword_scores[keyword] = float(count) / max_count if max_count > 0 else 0.0
    else:
        keyword_scores = {}
    
    return keyword_scores, {
        "ok": len(top_headlines) >= 1 or len(keyword_scores) >= 1,
        "provider": "rss",
        "items_count": len(top_headlines),
        "top_headlines": top_headlines[:max_items],
        "errors": errors
    }

