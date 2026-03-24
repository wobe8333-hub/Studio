"""
Knowledge 검색 유틸리티 (V3)

기능:
- index.jsonl에서 키워드 검색
"""

import json
from pathlib import Path
from typing import List, Dict, Any, Optional

from backend.utils.knowledge_store import get_knowledge_root


def search_index(q: str, limit: int = 10, base_dir: Optional[Path] = None) -> List[Dict[str, Any]]:
    """
    Index에서 키워드 검색
    
    Args:
        q: 검색 쿼리 (키워드)
        limit: 최대 결과 개수
        base_dir: 기본 디렉토리
    
    Returns:
        List[Dict]: 검색 결과 (run_id, one_liner 등 포함)
    """
    knowledge_root = get_knowledge_root(base_dir)
    index_path = knowledge_root / "index.jsonl"
    
    if not index_path.exists():
        return []
    
    results = []
    q_lower = q.lower()
    
    try:
        # 최신 엔트리 우선: 파일 끝(마지막 라인)부터 검색
        lines = index_path.read_text(encoding="utf-8").splitlines()
        seen_run_ids = set()

        for line in reversed(lines):
            if not line.strip():
                continue
            try:
                item = json.loads(line)
            except json.JSONDecodeError:
                continue

            run_id = item.get("run_id", "")
            if not run_id:
                continue

            # run_id 중복은 최신 1건만 유지
            if run_id in seen_run_ids:
                continue

            searchable_text = " ".join([
                item.get("run_id", ""),
                item.get("one_liner", ""),
                " ".join(item.get("keywords", []))
            ]).lower()

            if q_lower in searchable_text:
                results.append(item)
                seen_run_ids.add(run_id)
                if len(results) >= limit:
                    break
            else:
                # 검색에 실패해도 중복 제어를 위해 run_id 기록은 하지 않음(최신 매칭만)
                pass

    except Exception:
        pass
    
    return results

