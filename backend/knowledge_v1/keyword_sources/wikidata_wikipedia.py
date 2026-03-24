"""
Wikidata/Wikipedia 키워드 확장 (Wikipedia OpenSearch 기반)
- 외부 라이브러리 없이 urllib로 동작
- 네트워크 실패 시에도 최소 1개 키워드는 반환(0개 금지)
"""

from __future__ import annotations

import json
import re
from typing import List, Dict, Any, Tuple
from urllib.parse import quote
from urllib.request import urlopen, Request

def _norm(s: str) -> str:
    s = (s or "").strip()
    s = " ".join(s.split())
    return s

def _fetch_opensearch(seed: str, limit: int = 10) -> List[str]:
    seed = _norm(seed)
    if not seed:
        return []
    q = quote(seed)
    url = f"https://en.wikipedia.org/w/api.php?action=opensearch&search={q}&limit={limit}&namespace=0&format=json"
    req = Request(url, headers={"User-Agent": "AI-Animation-Studio/1.0"})
    with urlopen(req, timeout=15) as r:
        data = json.loads(r.read().decode("utf-8", errors="ignore"))
    # [search, titles[], desc[], links[]]
    if isinstance(data, list) and len(data) >= 2 and isinstance(data[1], list):
        return [_norm(x) for x in data[1] if _norm(x)]
    return []

def expand_keywords(keywords: List[str], category: str) -> Tuple[List[str], Dict[str, Any]]:
    seeds = [_norm(k) for k in (keywords or []) if _norm(k)]
    if not seeds:
        seeds = [_norm(category)] if _norm(category) else []

    out = []
    errors = []

    for s in seeds[:10]:
        try:
            out += _fetch_opensearch(s, limit=10)
        except Exception as e:
            errors.append({"seed": s, "error": f"{type(e).__name__}: {str(e)[:200]}"})

    # dedup + 최소 1개 보장
    uniq = []
    seen = set()
    for k in out:
        lk = k.lower()
        if lk in seen:
            continue
        seen.add(lk)
        uniq.append(k)

    if not uniq:
        # 0개 금지: seed 1개라도 반환
        uniq = [seeds[0]] if seeds else [category]

    meta = {
        "ok": True,
        "mode": "wikipedia_opensearch",
        "used_sources": ["wikipedia_opensearch"],
        "seed_count": len(seeds),
        "returned_count": len(uniq),
        "errors": errors,
        "category": category,
    }
    return uniq[:500], meta
