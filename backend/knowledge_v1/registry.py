"""
Knowledge v1 Source Registry - 내장 소스 레지스트리
"""

import json
from pathlib import Path
from typing import Dict, List, Optional


def load_registry() -> Dict:
    """Source Registry 로드 (fixtures/sample_sources.json)"""
    registry_path = Path(__file__).parent / "fixtures" / "sample_sources.json"
    with open(registry_path, "r", encoding="utf-8") as f:
        return json.load(f)


def get_sources_by_category(category: str) -> List[Dict]:
    """카테고리별 소스 목록 반환"""
    registry = load_registry()
    sources = registry.get("sources", [])
    return [s for s in sources if category in s.get("category_tags", [])]


def get_source_by_id(source_id: str) -> Optional[Dict]:
    """source_id로 소스 조회"""
    registry = load_registry()
    sources = registry.get("sources", [])
    for s in sources:
        if s.get("source_id") == source_id:
            return s
    return None


def find_sources(category: str, keywords: List[str]) -> List[Dict]:
    """카테고리와 키워드로 소스 찾기"""
    sources = get_sources_by_category(category)
    # 키워드 정보 추가
    result = []
    for source in sources:
        source_copy = source.copy()
        source_copy["keywords"] = keywords
        result.append(source_copy)
    return result

