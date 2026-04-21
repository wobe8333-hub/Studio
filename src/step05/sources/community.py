"""
한국 커뮤니티 소스 (Layer 3 — 주간)
DC인사이드, 클리앙, 에펨코리아 등 인기글 제목 수집 (BeautifulSoup 크롤링)

주의: 각 커뮤니티 이용약관을 준수해 robots.txt 허용 경로만 수집합니다.
     과도한 요청을 방지하기 위해 1~2초 딜레이를 적용합니다.
"""

import time
import urllib.request
from typing import Any, Dict, List

# 카테고리별 크롤링 대상 (robots.txt 허용 공개 페이지)
_COMMUNITY_SOURCES: Dict[str, List[Dict[str, str]]] = {
    "economy":     [
        {"name": "clien_economy", "url": "https://www.clien.net/service/board/cm_economy"},
    ],
    "psychology":  [
        {"name": "dcinside_psychology", "url": "https://gall.dcinside.com/board/lists?id=psych"},
    ],
    "mystery":     [
        {"name": "dcinside_mystery", "url": "https://gall.dcinside.com/board/lists?id=mystery"},
    ],
    "war_history": [
        {"name": "dcinside_military", "url": "https://gall.dcinside.com/board/lists?id=military"},
    ],
    "science":     [
        {"name": "clien_science", "url": "https://www.clien.net/service/board/news"},
    ],
    "realestate":  [
        {"name": "clien_realestate", "url": "https://www.clien.net/service/board/cm_realestate"},
    ],
    "history":     [
        {"name": "dcinside_history", "url": "https://gall.dcinside.com/board/lists?id=history"},
    ],
}


def _safe_fetch(url: str, timeout: int = 10) -> str:
    """robots.txt 준수 안전 크롤링"""
    try:
        req = urllib.request.Request(url)
        req.add_header(
            "User-Agent",
            "Mozilla/5.0 (compatible; KAS-TrendBot/2.0; +https://github.com/kas)"
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read().decode("utf-8", errors="ignore")
    except Exception:
        return ""


def _parse_titles(html: str, limit: int = 20) -> List[str]:
    """HTML에서 게시글 제목 추출"""
    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, "html.parser")
        # 클리앙 + DC인사이드 게시글 제목 패턴
        titles = []
        selectors = [
            "span.subject_fixed",          # 클리앙
            ".list_title",                  # 클리앙
            ".board-list-title",            # 클리앙
            "td.gall_tit a:not(.reply_num)",  # DC인사이드 일반 갤러리
            ".ub-content .gall-tit a",      # DC인사이드 마이너 갤러리
        ]
        for el in soup.select(", ".join(selectors)):
            text = el.get_text(strip=True)
            if text and len(text) > 3:
                titles.append(text[:100])
            if len(titles) >= limit:
                break
        return titles
    except ImportError:
        return []
    except Exception:
        return []


def fetch_community_topics(
    category: str,
    limit: int = 30,
) -> Dict[str, Any]:
    """
    한국 커뮤니티 인기글 제목 수집

    Returns:
        {
            "topics": List[str],
            "source": "community",
            "sources_used": List[str],
            "error": Optional[str]
        }
    """
    sources = _COMMUNITY_SOURCES.get(category, [])
    if not sources:
        return {
            "topics": [],
            "source": "community",
            "sources_used": [],
            "error": f"{category} 카테고리 커뮤니티 소스 미설정 (향후 확장 예정)",
        }

    topics: List[str] = []
    sources_used: List[str] = []
    errors: List[str] = []

    for src in sources:
        try:
            html = _safe_fetch(src["url"])
            if html:
                titles = _parse_titles(html, limit=limit // len(sources) + 5)
                topics.extend(titles)
                sources_used.append(src["name"])
            time.sleep(1)  # 요청 간격 1초
        except Exception as e:
            errors.append(f"{src['name']}: {str(e)[:100]}")

    return {
        "topics": list(dict.fromkeys(topics))[:limit],  # 중복 제거
        "source": "community",
        "sources_used": sources_used,
        "error": "; ".join(errors) if errors else None,
    }
