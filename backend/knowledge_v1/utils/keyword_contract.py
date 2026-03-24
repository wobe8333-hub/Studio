"""Keyword Type Contract SSOT."""

from __future__ import annotations

from typing import Any, List


def _norm_key(s: str) -> str:
    return " ".join((s or "").lower().split())


def normalize_kw(x: Any) -> str:
    """단일 keyword 값을 항상 str로 정규화한다."""
    if isinstance(x, str):
        return x.strip()

    if isinstance(x, dict):
        return normalize_kw(x.get("keyword") or x.get("text") or "")

    if isinstance(x, (list, tuple)):
        flattened: list[Any] = []
        for item in x:
            if isinstance(item, (list, tuple)):
                flattened.extend(item)
            else:
                flattened.append(item)
        str_items = [item.strip() for item in flattened if isinstance(item, str) and item.strip()]
        return " ".join(str_items).strip()

    return ""


def normalize_kw_list(kws: Any) -> List[str]:
    """다양한 입력을 list[str]로 정규화한다."""
    if isinstance(kws, (list, tuple)):
        candidates = [normalize_kw(item) for item in kws]
    else:
        candidates = [normalize_kw(kws)]

    out: List[str] = []
    seen = set()
    for kw in candidates:
        if not kw:
            continue
        key = _norm_key(kw)
        if key in seen:
            continue
        seen.add(key)
        out.append(kw)
    return out


def assert_kw_contract(kws: Any, context: str) -> List[str]:
    """키워드 계약: 비어있지 않은 list[str]만 통과."""
    normalized = normalize_kw_list(kws)
    if not normalized:
        raise ValueError(f"EMPTY_KEYWORDS_AFTER_NORMALIZE: {context}")
    return normalized

