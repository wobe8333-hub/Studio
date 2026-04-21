"""
Wikipedia OpenSearch 소스
외부 라이브러리 없이 urllib로 동작 — 네트워크 실패 시에도 최소 1개 키워드 보장
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Tuple
from urllib.parse import quote
from urllib.request import Request, urlopen


def _norm(s: str) -> str:
    """문자열 정규화 (공백 정리)"""
    s = (s or "").strip()
    return " ".join(s.split())


def _fetch_opensearch(seed: str, limit: int = 10, lang: str = "ko") -> List[str]:
    """
    Wikipedia OpenSearch API로 관련 주제 확장

    Args:
        seed: 검색 시드 키워드
        limit: 최대 결과 수
        lang: 언어 코드 ("ko"=한국어, "en"=영어)

    Returns:
        관련 Wikipedia 문서 제목 리스트
    """
    seed = _norm(seed)
    if not seed:
        return []

    q = quote(seed)
    url = (
        f"https://{lang}.wikipedia.org/w/api.php"
        f"?action=opensearch&search={q}&limit={limit}&namespace=0&format=json"
    )
    req = Request(url, headers={"User-Agent": "KAS-AI-Animation-Studio/2.0"})

    with urlopen(req, timeout=15) as r:
        data = json.loads(r.read().decode("utf-8", errors="ignore"))

    # OpenSearch 응답 형식: [search_term, [titles], [descs], [links]]
    if isinstance(data, list) and len(data) >= 2 and isinstance(data[1], list):
        return [_norm(x) for x in data[1] if _norm(x)]
    return []


def expand_keywords(
    keywords: List[str],
    category: str,
    lang: str = "ko"
) -> Tuple[List[str], Dict[str, Any]]:
    """
    Wikipedia OpenSearch 기반 키워드 확장

    Args:
        keywords: 시드 키워드 리스트
        category: 카테고리명 (시드가 없을 때 fallback으로 사용)
        lang: 검색 언어 ("ko" 또는 "en")

    Returns:
        (expanded_keywords, metadata)
        expanded_keywords: 최대 500개, 최소 1개 보장
        metadata: {ok, mode, seed_count, returned_count, errors, category}
    """
    seeds = [_norm(k) for k in (keywords or []) if _norm(k)]
    if not seeds:
        seeds = [_norm(category)] if _norm(category) else []

    out: List[str] = []
    errors: List[Dict[str, str]] = []

    for seed in seeds[:10]:
        try:
            results = _fetch_opensearch(seed, limit=10, lang=lang)
            out.extend(results)
            # 한국어가 없으면 영어로도 시도
            if lang == "ko" and not results:
                out.extend(_fetch_opensearch(seed, limit=5, lang="en"))
        except Exception as e:
            errors.append({"seed": seed, "error": f"{type(e).__name__}: {str(e)[:200]}"})

    # 중복 제거 (순서 유지)
    seen: set = set()
    unique: List[str] = []
    for k in out:
        lk = k.lower()
        if lk not in seen:
            seen.add(lk)
            unique.append(k)

    # 0개 금지: seed 1개라도 반환 보장
    if not unique:
        unique = [seeds[0]] if seeds else [category]

    return unique[:500], {
        "ok": True,
        "mode": "wikipedia_opensearch",
        "used_sources": ["wikipedia_opensearch"],
        "seed_count": len(seeds),
        "returned_count": len(unique),
        "errors": errors,
        "category": category,
        "lang": lang
    }
