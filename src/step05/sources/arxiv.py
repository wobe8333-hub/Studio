"""
arXiv API 소스 (Layer 4 — 월간, CH6 과학 전용)
최신 과학 논문 제목/초록에서 트렌드 주제 추출
"""

import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
from typing import Dict, Any, List

# 과학 카테고리별 arXiv 검색 쿼리
_ARXIV_QUERIES: Dict[str, List[str]] = {
    "science": [
        "cat:astro-ph",        # 천문학/우주
        "cat:physics.pop-ph",  # 일반 물리
        "cat:q-bio",           # 생물학
        "cat:cs.AI",           # AI
    ],
}

_ARXIV_NS = "http://www.w3.org/2005/Atom"


def fetch_arxiv_papers(
    category: str = "science",
    max_results: int = 20,
) -> Dict[str, Any]:
    """
    arXiv API로 최신 논문 수집 (과학 채널 전용)

    Returns:
        {
            "topics": List[str],       — 논문 제목 리스트
            "summaries": List[str],    — 초록 요약
            "source": "arxiv",
            "applicable": bool,        — 비과학 채널이면 False
            "error": Optional[str]
        }
    """
    queries = _ARXIV_QUERIES.get(category)
    if not queries:
        return {
            "topics": [],
            "summaries": [],
            "source": "arxiv",
            "applicable": False,
            "error": f"arXiv는 science 카테고리 전용 (현재: {category})",
        }

    topics: List[str] = []
    summaries: List[str] = []
    errors: List[str] = []

    for query in queries[:2]:  # 최대 2개 카테고리
        try:
            params = urllib.parse.urlencode({
                "search_query": query,
                "start": 0,
                "max_results": max_results // 2,
                "sortBy": "submittedDate",
                "sortOrder": "descending",
            })
            url = f"https://export.arxiv.org/api/query?{params}"
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "KAS-AI-Animation-Studio/2.0"}
            )

            with urllib.request.urlopen(req, timeout=15) as resp:
                root = ET.fromstring(resp.read())

            for entry in root.findall(f"{{{_ARXIV_NS}}}entry"):
                title_el = entry.find(f"{{{_ARXIV_NS}}}title")
                summary_el = entry.find(f"{{{_ARXIV_NS}}}summary")

                if title_el is not None and title_el.text:
                    title = title_el.text.strip().replace("\n", " ")
                    topics.append(title)

                if summary_el is not None and summary_el.text:
                    summary = summary_el.text.strip()[:300]
                    summaries.append(summary)

        except Exception as e:
            errors.append(f"{query}: {str(e)[:100]}")

    return {
        "topics": topics[:30],
        "summaries": summaries[:30],
        "source": "arxiv",
        "applicable": True,
        "error": "; ".join(errors) if errors else None,
    }
