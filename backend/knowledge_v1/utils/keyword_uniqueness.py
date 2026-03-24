"""Keyword uniqueness helpers (SSOT)."""

from __future__ import annotations

import re
from typing import Dict, List, Tuple, Any


_NON_WORD_RE = re.compile(r"[^0-9a-zA-Z\uac00-\ud7a3\s]+")


def normalize(s: str) -> str:
    """lower + 공백축약 + 특수문자 제거."""
    text = (s or "").strip().lower()
    text = _NON_WORD_RE.sub(" ", text)
    text = " ".join(text.split())
    return text


def enforce_unique(category_map: Dict[str, List[str]], k: int = 5) -> Tuple[Dict[str, List[str]], Dict[str, Any]]:
    """
    카테고리 간 중복을 제거하고 카테고리당 최대 k개를 유지한다.
    반환 결과는 길이 보정(fill)을 하지 않는다.
    """
    fixed: Dict[str, List[str]] = {}
    dup_report: Dict[str, Any] = {"duplicates": [], "removed_count": 0}
    seen_global = set()

    for category, keywords in category_map.items():
        out: List[str] = []
        local_seen = set()
        for kw in keywords or []:
            norm = normalize(kw)
            if not norm:
                continue
            if norm in local_seen:
                dup_report["duplicates"].append({"category": category, "keyword": kw, "reason": "intra_category"})
                dup_report["removed_count"] += 1
                continue
            if norm in seen_global:
                dup_report["duplicates"].append({"category": category, "keyword": kw, "reason": "inter_category"})
                dup_report["removed_count"] += 1
                continue
            local_seen.add(norm)
            seen_global.add(norm)
            out.append(kw.strip())
            if len(out) >= k:
                break
        fixed[category] = out

    return fixed, dup_report


