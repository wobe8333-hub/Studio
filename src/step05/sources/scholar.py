"""
Semantic Scholar API 소스 (Layer 4 — 월간)
학술 논문 기반 트렌드 주제 수집 (무료, 100콜/초)
CH3 심리, CH6 과학 우선 적용
"""

import urllib.request
import urllib.parse
import json
from typing import Dict, Any, List

# 카테고리별 Semantic Scholar 검색 쿼리
_SCHOLAR_QUERIES: Dict[str, List[str]] = {
    "psychology":  ["cognitive bias", "mental health intervention", "behavioral psychology"],
    "science":     ["astrophysics discovery", "quantum mechanics", "climate change research"],
    "history":     ["historical analysis", "archaeological discovery"],
    "mystery":     ["unexplained phenomena", "forensic science unsolved"],
    "war_history": ["military history analysis", "conflict history"],
    "economy":     ["behavioral economics", "market psychology"],
    "realestate":  ["urban economics", "real estate market"],
}

_BASE_URL = "https://api.semanticscholar.org/graph/v1/paper/search"


def fetch_scholar_papers(
    category: str,
    max_results: int = 15,
) -> Dict[str, Any]:
    """
    Semantic Scholar API로 인용수 높은 최신 논문 수집

    Returns:
        {
            "topics": List[str],       — 논문 제목
            "abstracts": List[str],    — 초록 (있는 경우)
            "source": "semantic_scholar",
            "configured": True,
            "error": Optional[str]
        }
    """
    queries = _SCHOLAR_QUERIES.get(category, [category])
    topics: List[str] = []
    abstracts: List[str] = []
    errors: List[str] = []

    for query in queries[:2]:
        try:
            params = urllib.parse.urlencode({
                "query": query,
                "limit": max_results // 2,
                "fields": "title,abstract,year,citationCount",
                "sort": "citationCount",
            })
            url = f"{_BASE_URL}?{params}"
            req = urllib.request.Request(
                url,
                headers={
                    "User-Agent": "KAS-AI-Animation-Studio/2.0",
                    "Accept": "application/json",
                }
            )

            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode("utf-8"))

            for paper in data.get("data", []):
                title = paper.get("title", "")
                abstract = paper.get("abstract", "")
                if title:
                    topics.append(title)
                if abstract:
                    abstracts.append(abstract[:300])

        except Exception as e:
            errors.append(f"{query}: {str(e)[:100]}")

    return {
        "topics": topics[:25],
        "abstracts": abstracts[:25],
        "source": "semantic_scholar",
        "configured": True,
        "error": "; ".join(errors) if errors else None,
    }
