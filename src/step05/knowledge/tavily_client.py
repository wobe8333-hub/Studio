"""
Tavily AI Search 클라이언트
실시간 웹 검색 — 주제에 대한 최신 정보 + 출처 URL 추출
"""

from typing import List, Dict, Any
from loguru import logger

from src.core.config import TAVILY_API_KEY


def search_topic(query: str, max_results: int = 5) -> Dict[str, Any]:
    """
    Tavily AI Search로 주제 검색

    Returns:
        {
            "results": [{"title", "url", "content", "score"}],
            "answer": str,  # AI 요약 답변
            "ok": bool
        }
    """
    if not TAVILY_API_KEY:
        logger.debug("[Tavily] API 키 없음 — 건너뜀")
        return {"results": [], "answer": "", "ok": False}

    try:
        from tavily import TavilyClient
        client = TavilyClient(api_key=TAVILY_API_KEY)
        resp = client.search(
            query=query,
            search_depth="advanced",
            max_results=max_results,
            include_answer=True,
        )
        return {
            "results": resp.get("results", []),
            "answer": resp.get("answer", ""),
            "ok": True,
        }
    except Exception as e:
        logger.debug(f"[Tavily] 검색 실패: {e}")
        return {"results": [], "answer": "", "ok": False}


def extract_facts_from_results(results: List[Dict]) -> List[str]:
    """검색 결과에서 핵심 문장 추출 (content 앞 2문장)"""
    facts = []
    for r in results:
        content = r.get("content", "").strip()
        if not content:
            continue
        sentences = [s.strip() for s in content.split(".") if len(s.strip()) > 20]
        facts.extend(sentences[:2])
    return facts[:7]
