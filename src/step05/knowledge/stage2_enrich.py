"""
Stage 2: 구조화된 지식 보강
Wikipedia + Semantic Scholar + Naver Search
→ timeline, statistics, expert_quotes, counterpoints 구조화
"""

from typing import List, Dict, Any
from loguru import logger

from src.core.config import NAVER_CLIENT_ID, NAVER_CLIENT_SECRET
from src.step05.knowledge.knowledge_package import KnowledgePackage, SourceEntry


# ──────────────────────────────────────────────
# Wikipedia 보강
# ──────────────────────────────────────────────

def _fetch_wikipedia(topic: str) -> Dict[str, Any]:
    """Wikipedia API로 주제 정의·개요·연대표 수집"""
    try:
        import requests
        params = {
            "action": "query",
            "format": "json",
            "titles": topic,
            "prop": "extracts",
            "exintro": True,
            "explaintext": True,
            "exsentences": 8,
            "redirects": 1,
        }
        resp = requests.get(
            "https://ko.wikipedia.org/w/api.php",
            params=params,
            timeout=10,
        )
        data = resp.json()
        pages = data.get("query", {}).get("pages", {})
        for page_id, page in pages.items():
            if page_id == "-1":
                continue
            extract = page.get("extract", "").strip()
            if extract:
                return {
                    "extract": extract,
                    "url": f"https://ko.wikipedia.org/wiki/{topic.replace(' ', '_')}",
                    "ok": True,
                }
    except Exception as e:
        logger.debug(f"[Stage2-Wiki] 수집 실패: {e}")
    return {"extract": "", "url": "", "ok": False}


def _extract_wiki_stats(extract: str) -> List[Dict[str, str]]:
    """Wikipedia 본문에서 수치/통계 추출 (숫자 포함 문장)"""
    import re
    stats = []
    sentences = extract.split(".")
    for s in sentences:
        s = s.strip()
        if re.search(r"\d+[%억만원달러%배]", s) and len(s) > 20:
            stats.append({"value": s, "source": "Wikipedia"})
    return stats[:3]


# ──────────────────────────────────────────────
# Semantic Scholar 보강
# ──────────────────────────────────────────────

def _fetch_scholar(topic: str, category: str) -> Dict[str, Any]:
    """Semantic Scholar API로 관련 학술 논문 수집"""
    try:
        import requests
        # 카테고리별 검색어 영어 매핑
        category_en = {
            "economy": "economics finance",
            "realestate": "real estate housing market",
            "psychology": "psychology behavior",
            "mystery": "paranormal unexplained phenomena",
            "war_history": "military history war",
            "science": "science research",
            "history": "history ancient",
        }
        query_suffix = category_en.get(category, "")
        query = f"{topic} {query_suffix}".strip()

        resp = requests.get(
            "https://api.semanticscholar.org/graph/v1/paper/search",
            params={
                "query": query,
                "fields": "title,abstract,citationCount,year,authors",
                "limit": 5,
            },
            timeout=10,
        )
        data = resp.json()
        papers = data.get("data", [])
        expert_quotes = []
        sources = []
        for p in papers[:3]:
            abstract = p.get("abstract", "") or ""
            if abstract and len(abstract) > 50:
                expert_quotes.append(abstract[:200])
            if p.get("externalIds", {}).get("DOI"):
                sources.append(f"https://doi.org/{p['externalIds']['DOI']}")
        return {
            "expert_quotes": expert_quotes,
            "sources": sources,
            "ok": True,
        }
    except Exception as e:
        logger.debug(f"[Stage2-Scholar] 수집 실패: {e}")
        return {"expert_quotes": [], "sources": [], "ok": False}


# ──────────────────────────────────────────────
# Naver Search API 보강
# ──────────────────────────────────────────────

def _fetch_naver_search(topic: str) -> Dict[str, Any]:
    """Naver Search API로 한국어 블로그/뉴스 자료 수집"""
    if not NAVER_CLIENT_ID or not NAVER_CLIENT_SECRET:
        logger.debug("[Stage2-Naver] API 키 없음")
        return {"items": [], "ok": False}

    try:
        import requests
        headers = {
            "X-Naver-Client-Id": NAVER_CLIENT_ID,
            "X-Naver-Client-Secret": NAVER_CLIENT_SECRET,
        }
        resp = requests.get(
            "https://openapi.naver.com/v1/search/news.json",
            params={"query": topic, "display": 5, "sort": "date"},
            headers=headers,
            timeout=10,
        )
        data = resp.json()
        items = data.get("items", [])
        return {"items": items, "ok": True}
    except Exception as e:
        logger.debug(f"[Stage2-Naver] 수집 실패: {e}")
        return {"items": [], "ok": False}


def _extract_counterpoints_from_news(items: List[Dict]) -> List[str]:
    """뉴스 항목에서 다른 시각/반론 추출 (제목 기반)"""
    counterpoints = []
    for item in items[:5]:
        title = item.get("title", "").replace("<b>", "").replace("</b>", "")
        desc = item.get("description", "").replace("<b>", "").replace("</b>", "")
        if any(kw in title for kw in ["비판", "논란", "반론", "의문", "우려", "문제"]):
            counterpoints.append(title)
        elif desc and len(desc) > 30:
            counterpoints.append(desc[:100])
    return counterpoints[:2]


# ──────────────────────────────────────────────
# Stage 2 메인 함수
# ──────────────────────────────────────────────

def stage2_enrich(pkg: KnowledgePackage) -> KnowledgePackage:
    """
    Stage 2: Wikipedia + Scholar + Naver로 구조화 보강
    timeline, statistics, expert_quotes, counterpoints, sources 추가
    """
    logger.info(f"[Stage2] '{pkg.topic}' 구조화 보강 시작")
    enriched = 0

    # ── 1) Wikipedia ──────────────────────────────────────────────
    wiki = _fetch_wikipedia(pkg.topic)
    if wiki["ok"] and wiki["extract"]:
        # 핵심 팩트 보강 (기존 팩트가 부족하면 추가)
        if len(pkg.core_facts) < 5:
            sentences = [s.strip() for s in wiki["extract"].split(".") if len(s.strip()) > 20]
            for s in sentences[:3]:
                if s not in pkg.core_facts:
                    pkg.core_facts.append(s)

        # 통계 추출
        stats = _extract_wiki_stats(wiki["extract"])
        pkg.statistics.extend(stats)

        # 출처 추가
        pkg.sources.append(SourceEntry(
            url=wiki["url"],
            title=f"Wikipedia: {pkg.topic}",
            source_type="wiki",
            reliability="MED",
        ))
        enriched += 1
        logger.debug(f"[Stage2] Wikipedia: 팩트+{max(0,5-len(pkg.core_facts))} 통계+{len(stats)}")

    # ── 2) Semantic Scholar ───────────────────────────────────────
    scholar = _fetch_scholar(pkg.topic, pkg.category)
    if scholar["ok"] and scholar.get("expert_quotes"):
        pkg.expert_quotes.extend(scholar["expert_quotes"][:2])
        for url in scholar.get("sources", [])[:2]:
            pkg.sources.append(SourceEntry(
                url=url,
                title="",
                source_type="scholar",
                reliability="HIGH",
            ))
        enriched += 1
        logger.debug(f"[Stage2] Scholar: 인용+{len(scholar['expert_quotes'])}")

    # ── 3) Naver Search ───────────────────────────────────────────
    naver = _fetch_naver_search(pkg.topic)
    if naver["ok"]:
        counterpoints = _extract_counterpoints_from_news(naver["items"])
        pkg.counterpoints.extend(counterpoints)
        # Naver 뉴스 출처 추가
        for item in naver["items"][:2]:
            pkg.sources.append(SourceEntry(
                url=item.get("link", ""),
                title=item.get("title", "").replace("<b>", "").replace("</b>", ""),
                source_type="news",
                reliability="MED",
            ))
        enriched += 1
        logger.debug(f"[Stage2] Naver: 반론+{len(counterpoints)}")

    pkg.stage2_ok = enriched > 0

    # 신뢰도 상향 (Stage 2 성공 시)
    if enriched > 0:
        pkg.confidence_score = min(pkg.confidence_score + 0.1 * enriched, 0.85)

    logger.info(
        f"[Stage2] 완료: 팩트={len(pkg.core_facts)}, 통계={len(pkg.statistics)}, "
        f"인용={len(pkg.expert_quotes)}, 반론={len(pkg.counterpoints)}, 소스={len(pkg.sources)}"
    )
    return pkg
