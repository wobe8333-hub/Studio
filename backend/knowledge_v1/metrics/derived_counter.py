"""Derived chunks counter - SSOT for derived_count."""

from __future__ import annotations

from pathlib import Path
from typing import Dict

from backend.knowledge_v1.store import load_jsonl


def count_derived_by_category(chunks_path: str | Path) -> Dict[str, int]:
    """
    chunks.jsonl 기준으로 카테고리별 derived_count를 계산한다.

    규칙:
    - 각 라인은 dict 여야 하며, tags 필드가 list 인 경우 tags에 포함된 카테고리명을 모두 카운트한다.
    - 파싱 실패/형식 오류 라인은 건너뛰고 error_count는 별도로 관리할 수 있도록 확장 가능.
    """
    path = Path(chunks_path)
    counts: Dict[str, int] = {}
    if not path.exists():
        return counts

    for row in load_jsonl(path):
        if not isinstance(row, dict):
            continue
        tags = row.get("tags") or []
        if not isinstance(tags, list):
            continue
        for tag in tags:
            if not isinstance(tag, str):
                continue
            cat = tag.strip()
            if not cat:
                continue
            counts[cat] = counts.get(cat, 0) + 1
    return counts


def count_derived_for_category(chunks_path: str | Path, category: str) -> int:
    """단일 카테고리 derived_count 계산."""
    return count_derived_by_category(chunks_path).get(category, 0)


