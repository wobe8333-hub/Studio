"""
Knowledge v1 Retrieve Gate - STEP3 주제 입력 시 사용 게이트

전체코드_5 기준 설계 원칙(데이터 기반):
- 신규 store 경로: backend/output/knowledge_v1/{discovery|approved}/...
  (paths.py, cycle.py가 사용하는 경로)
- 레거시 경로(used/index/audit 일부): backend/output/knowledge_v1/used, index/index.json, audit/audit.jsonl
  (classify.py, derive.py, audit.py가 사용하는 경로)

따라서 STEP3는:
- store 우선순위: approved → discovery
- index가 없거나 mismatch여도 tags/text 스캔으로 반드시 후보를 찾음
- eligibility는 레거시(root/used/used_assets.jsonl) + store별 used(있으면) 모두 취합
- BLOCKED는 결과에서 제외
- mode:
  - reference_only: injection_allowed 항상 False
  - limited_injection: eligibility in {LIMITED_INJECTION, FULLY_USABLE} 일 때만 True
- QUERY audit: store audit(append_audit)로 기록(approved/discovery 모두 시도)
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from backend.knowledge_v1.paths import get_root, get_store_root, get_assets_path, get_chunks_path, get_audit_path, ensure_dirs
from backend.knowledge_v1.store import load_jsonl, append_jsonl
from backend.knowledge_v1.schema import AuditEvent


def _safe_read_json(path: Path) -> Optional[dict]:
    try:
        if path.exists():
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                return json.load(f)
    except Exception:
        return None
    return None


def _append_store_audit(store: str, event_type: str, details: Dict[str, Any]) -> None:
    # store audit (신규 경로)
    try:
        ensure_dirs(store)  # discovery/approved 디렉토리 생성 보장
        ap = get_audit_path(store)
        ev = AuditEvent.create(event_type, details).to_dict()
        append_jsonl(ap, ev)
    except Exception:
        pass


def _append_legacy_audit(event_type: str, details: Dict[str, Any]) -> None:
    # 레거시 audit 경로 (읽기 전용이므로 읽기 루트 사용)
    try:
        from backend.knowledge_v1.paths import get_read_root
        root = get_read_root()  # 읽기용 (레거시 폴백 허용)
        ap = root / "audit" / "audit.jsonl"
        # 읽기 전용이므로 쓰기 시도하지 않음 (audit은 새 store에만 기록)
    except Exception:
        pass


def _normalize_topic(topic: str) -> Tuple[str, str, List[str]]:
    topic_norm = (topic or "").strip()
    topic_lower = topic_norm.lower()
    tokens = [t for t in re.split(r"\s+", topic_lower) if t]
    return topic_norm, topic_lower, tokens


def _get_store_candidates() -> List[str]:
    # approved 우선, 그 다음 discovery
    return ["approved", "discovery"]


def _choose_active_store() -> str:
    # chunks 존재/라인>0인 store를 우선 사용(approved 우선)
    for s in _get_store_candidates():
        p = get_chunks_path(s)
        if p.exists():
            try:
                # 빈 파일이면 skip
                with open(p, "r", encoding="utf-8", errors="ignore") as f:
                    for _ in range(1):
                        line = f.readline()
                        if line and line.strip():
                            return s
            except Exception:
                pass
    return "discovery"


def _load_indexes(store: str) -> Tuple[dict, bool]:
    """
    인덱스는 레거시/신규 둘 다 시도 (읽기 전용):
    - 신규(가능성): store_root/indexes/index.json  (paths.ensure_dirs가 만드는 폴더)
    - 신규(대안): store_root/index/index.json      (과거 코드/패치에서 사용 가능)
    - 레거시: get_read_root()/index/index.json     (읽기용)
    """
    from backend.knowledge_v1.paths import get_read_root
    store_root = get_store_root(store)

    candidates = [
        store_root / "indexes" / "index.json",
        store_root / "index" / "index.json",
        get_read_root() / "index" / "index.json",  # 읽기용
    ]
    for p in candidates:
        obj = _safe_read_json(p)
        if isinstance(obj, dict):
            return obj, True
    return {}, False


def _load_asset_map() -> Dict[str, Dict[str, Any]]:
    """
    asset map은 store별 raw + 레거시 raw도 함께 취합 (읽기 전용)
    - store raw: get_assets_path(store)
    - 레거시 raw: get_read_root()/raw/assets.jsonl (읽기용)
    """
    from backend.knowledge_v1.paths import get_read_root
    out: Dict[str, Dict[str, Any]] = {}

    legacy_assets = get_read_root() / "raw" / "assets.jsonl"  # 읽기용
    paths = [
        get_assets_path("approved"),
        get_assets_path("discovery"),
        legacy_assets,
    ]
    for p in paths:
        if not p.exists():
            continue
        for row in load_jsonl(p):
            aid = row.get("asset_id")
            if aid and aid not in out:
                out[aid] = row
    return out


def _load_eligibility_map() -> Dict[str, str]:
    """
    eligibility는 classify.py가 새 store에 쓰지만, 레거시도 읽기용으로 포함.
    추가로 store별 used가 존재하면 함께 취합 (읽기 전용).
    """
    from backend.knowledge_v1.paths import get_read_root
    out: Dict[str, str] = {}
    candidates = [
        get_read_root() / "used" / "used_assets.jsonl",               # 읽기용 (레거시 폴백 허용)
        get_store_root("approved") / "used" / "used_assets.jsonl",    # store별(존재 시)
        get_store_root("discovery") / "used" / "used_assets.jsonl",   # store별(존재 시)
    ]
    for p in candidates:
        if not p.exists():
            continue
        for row in load_jsonl(p):
            aid = row.get("asset_id")
            if not aid:
                continue
            out[aid] = row.get("eligible_for", "REFERENCE_ONLY")
    return out


def _index_candidates(index: dict, category: str, topic_norm: str, topic_lower: str, tokens: List[str]) -> Tuple[List[str], bool]:
    """
    index dict 구조는 키->chunk_id 리스트 형태를 기대한다.
    - topic_norm, topic_lower, tokens, category 모두 조회
    """
    chunk_ids: List[str] = []
    hit = False

    def _add(key: str) -> None:
        nonlocal hit
        if not key:
            return
        v = index.get(key)
        if isinstance(v, list) and v:
            hit = True
            for cid in v:
                if cid not in chunk_ids:
                    chunk_ids.append(cid)

    _add(topic_norm)
    _add(topic_lower)
    for t in tokens:
        _add(t)
    _add(category)
    return chunk_ids, hit


def _scan_chunks_by_tags_and_text(chunks_path: Path, topic_norm: str, topic_lower: str, tokens: List[str], limit: int) -> List[Dict[str, Any]]:
    """
    index가 없거나 빈 결과면 전체 스캔.
    매칭 규칙(정확):
    - tags(lower) 에 topic_lower 또는 tokens 중 하나라도 포함 OR
    - chunk.text(lower) 에 topic_lower 포함
    """
    out: List[Dict[str, Any]] = []
    if not chunks_path.exists():
        return out

    want = set([topic_lower] + tokens)
    for row in load_jsonl(chunks_path):
        tags = row.get("tags") or []
        tags_l = set([str(t).strip().lower() for t in tags if t])
        text_l = str(row.get("text") or "").lower()

        tag_hit = any(w in tags_l for w in want if w)
        text_hit = topic_lower and (topic_lower in text_l)

        if tag_hit or text_hit:
            out.append(row)
            if len(out) >= limit:
                break
    return out


def query(category: str, topic: str, limit: int = 10, mode: str = "reference_only") -> Dict[str, Any]:
    """
    STEP3 주제 입력 시 사용 게이트
    Returns:
      { topic, category, results[], debug{} }
    """
    # mode 정규화
    if mode not in {"reference_only", "limited_injection"}:
        mode = "reference_only"

    topic_norm, topic_lower, tokens = _normalize_topic(topic)

    # store 선택 (approved 우선, 없으면 discovery)
    active_store = _choose_active_store()

    # store별 chunks 경로 후보(검색은 active_store부터, 없으면 다른 store fallback)
    store_order = [active_store] + [s for s in _get_store_candidates() if s != active_store]

    # index 로드 (store별 + 레거시)
    index, index_loaded = _load_indexes(active_store)

    eligibility_map = _load_eligibility_map()
    assets_map = _load_asset_map()

    # 후보 chunk 로딩
    chunk_rows: List[Dict[str, Any]] = []
    used_store: Optional[str] = None
    chunks_path_used: Optional[Path] = None
    index_hit = False
    fallback_scan_used = False

    # 1) index 기반 후보 chunk_id 도출
    chunk_ids, index_hit = _index_candidates(index, category, topic_norm, topic_lower, tokens)

    # 2) store별로 chunk_ids 로드 시도, 실패하면 scan fallback
    if chunk_ids:
        idset = set(chunk_ids)
        for s in store_order:
            p = get_chunks_path(s)
            if not p.exists():
                continue
            found: List[Dict[str, Any]] = []
            for row in load_jsonl(p):
                cid = row.get("chunk_id")
                if cid and cid in idset:
                    found.append(row)
                    if len(found) >= limit:
                        break
            if found:
                chunk_rows = found
                used_store = s
                chunks_path_used = p
                break

    if not chunk_rows:
        # 3) scan fallback (tags/text)
        fallback_scan_used = True
        for s in store_order:
            p = get_chunks_path(s)
            rows = _scan_chunks_by_tags_and_text(p, topic_norm, topic_lower, tokens, limit)
            if rows:
                chunk_rows = rows
                used_store = s
                chunks_path_used = p
                break

    # 결과 구성
    results: List[Dict[str, Any]] = []
    for row in chunk_rows[:limit]:
        cid = row.get("chunk_id")
        aid = row.get("asset_id")
        if not cid or not aid:
            continue

        eligible_for = eligibility_map.get(aid, "REFERENCE_ONLY")

        # BLOCKED는 절대 반환 금지
        if eligible_for == "BLOCKED":
            continue

        if mode == "limited_injection":
            injection_allowed = eligible_for in {"LIMITED_INJECTION", "FULLY_USABLE"}
        else:
            injection_allowed = False

        asset = assets_map.get(aid, {})
        text_full = row.get("text") or ""
        text_short = (text_full[:200] + "...") if len(text_full) > 200 else text_full

        results.append({
            "chunk_id": cid,
            "asset_id": aid,
            "text": text_short,
            "tags": row.get("tags") or [],
            "eligibility": eligible_for,
            "injection_allowed": bool(injection_allowed),
            "source_ref": asset.get("source_ref", ""),
        })

    details = {
        "category": category,
        "topic": topic,
        "topic_norm": topic_norm,
        "topic_tokens": tokens,
        "limit": int(limit),
        "mode": mode,
        "active_store": active_store,
        "used_store": used_store,
        "chunks_path": str(chunks_path_used) if chunks_path_used else "",
        "index_loaded": bool(index_loaded),
        "index_hit": bool(index_hit),
        "fallback_scan_used": bool(fallback_scan_used),
        "result_count": len(results),
    }

    # audit: store + legacy(root) 모두 기록(실패해도 파이프라인 중단 금지)
    _append_store_audit("approved", "QUERY", details)
    _append_store_audit("discovery", "QUERY", details)
    _append_legacy_audit("QUERY", details)

    return {
        "topic": topic,
        "category": category,
        "results": results,
        "debug": {
            "results_returned": len(results),
            "used_store": used_store,
            "index_loaded": bool(index_loaded),
            "index_hit": bool(index_hit),
            "fallback_scan_used": bool(fallback_scan_used),
        },
    }
