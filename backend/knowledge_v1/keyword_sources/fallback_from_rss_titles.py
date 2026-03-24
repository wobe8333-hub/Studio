"""RSS title 기반 키워드 보충."""

from __future__ import annotations

import re
from collections import defaultdict
from typing import Dict, List, Set

from backend.knowledge_v1.keyword_sources.news_context import fetch_news_context
from backend.knowledge_v1.utils.keyword_uniqueness import normalize


CATEGORY_HINTS: Dict[str, List[str]] = {
    "history": ["ancient", "dynasty", "empire", "revolution", "civilization", "history", "joseon"],
    "mystery": ["unsolved", "mystery", "disappearance", "ufo", "secret", "conspiracy", "cold case"],
    "economy": ["inflation", "gdp", "interest rate", "stock", "market", "recession", "trade"],
    "myth": ["myth", "legend", "god", "goddess", "norse", "greek", "roman", "dragon"],
    "science": ["quantum", "space", "physics", "biology", "astronomy", "experiment", "nasa"],
    "war_history": ["war", "battle", "ww1", "ww2", "vietnam war", "korean war", "army", "strategy"],
}

_TOKEN_RE = re.compile(r"[0-9A-Za-z\uac00-\ud7a3]{2,}")
_STOPWORDS = {
    "the", "a", "an", "in", "on", "at", "of", "for", "to", "and", "or", "is", "are", "was", "were",
    "this", "that", "with", "from", "by", "as", "it", "be",
}


def _extract_candidates_from_title(title: str) -> List[str]:
    text = (title or "").strip()
    if not text:
        return []
    tokens = _TOKEN_RE.findall(text)
    out: List[str] = []
    # 토큰 단일 + bi-gram 후보
    for tok in tokens:
        if len(tok) >= 2 and tok.lower() not in _STOPWORDS:
            out.append(tok)
    for i in range(len(tokens) - 1):
        t1 = tokens[i].lower()
        t2 = tokens[i + 1].lower()
        if t1 in _STOPWORDS or t2 in _STOPWORDS:
            continue
        out.append(f"{tokens[i]} {tokens[i + 1]}")
    # 제목 전체도 후보에 포함 (데이터 기반 원문 유지)
    out.append(text)
    return out


def extract_fallback_keywords_from_rss_titles(
    category: str,
    k: int,
    exclude_norms: Set[str] | None = None,
) -> List[str]:
    """
    RSS 실제 title만 사용해서 카테고리 후보 키워드를 생성한다.
    """
    exclude_norms = exclude_norms or set()
    hints = CATEGORY_HINTS.get(category, [category])
    query_terms = []
    if hints:
        query_terms.append(hints[0])
    if category not in query_terms:
        query_terms.append(category)
    query_terms = query_terms[:2]
    # 힌트 기반으로 RSS 수집 (source 반환 데이터만 사용)
    keyword_scores, snapshot = fetch_news_context(keywords=query_terms, lookback_days=7, max_items=30)
    headlines = snapshot.get("top_headlines", []) if isinstance(snapshot, dict) else []

    scored = defaultdict(float)
    first_seen = {}

    # RSS가 keyword score를 준 경우 가중치 사용
    norm_kw_scores = {normalize(k): float(v) for k, v in (keyword_scores or {}).items()}

    for idx, item in enumerate(headlines):
        if not isinstance(item, dict):
            continue
        title = (item.get("title") or "").strip()
        if not title:
            continue
        for cand in _extract_candidates_from_title(title):
            norm = normalize(cand)
            if not norm or norm in exclude_norms:
                continue
            score = 1.0
            for hint in hints:
                hint_norm = normalize(hint)
                if hint_norm and hint_norm in norm:
                    score += 3.0
            for k_norm, k_score in norm_kw_scores.items():
                if k_norm and k_norm in norm:
                    score += k_score
            scored[cand] += score
            if cand not in first_seen:
                first_seen[cand] = idx

    ranked = sorted(scored.items(), key=lambda kv: (-kv[1], first_seen.get(kv[0], 10**9), kv[0].lower()))
    out: List[str] = []
    local_seen = set()
    for cand, _ in ranked:
        norm = normalize(cand)
        if norm in local_seen or norm in exclude_norms:
            continue
        local_seen.add(norm)
        out.append(cand.strip())
        if len(out) >= k:
            break
    return out


