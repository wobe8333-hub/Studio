"""Empty-asset drop metrics - SSOT for 'empty' 판정 및 by_source 집계."""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Tuple, Any

from backend.knowledge_v1.store import load_jsonl


def is_empty_asset(a: dict) -> bool:
    """
    빈 asset 판정 (SSOT) - KnowledgeAsset 스키마 기준

    KnowledgeAsset 구조: source_id/source_ref/keywords/payload 중심
    아래 중 1개라도 있으면 NOT empty:
    - source_id 존재
    - source_ref 존재
    - keywords가 비어있지 않음
    - payload 안에 text/title/url/source 중 1개라도 존재
    - raw_hash 존재 (자산 실체가 있음을 의미)
    """
    if not isinstance(a, dict):
        return True

    def _has(v: Any) -> bool:
        return (v is not None) and (str(v).strip() != "")

    # KnowledgeAsset 스키마 기준: source_id/source_ref/keywords/raw_hash 확인
    if _has(a.get("source_id")):
        return False
    if _has(a.get("source_ref")):
        return False
    if a.get("keywords"):
        # keywords가 리스트이고 비어있지 않으면 NOT empty
        if isinstance(a.get("keywords"), list) and len(a.get("keywords", [])) > 0:
            return False
        # 문자열이면 비어있지 않은지 확인
        if isinstance(a.get("keywords"), str) and _has(a.get("keywords")):
            return False
    if _has(a.get("raw_hash")):
        return False

    # payload 딕셔너리 내 nested 확인
    payload = a.get("payload", {}) or {}
    if not isinstance(payload, dict):
        payload = {}

    # payload 텍스트 계열
    for key in ("text", "summary", "content", "body"):
        if _has(payload.get(key)):
            return False

    # payload 메타 계열
    for key in ("title", "url", "source", "source_id"):
        if _has(payload.get(key)):
            return False

    # 레거시 호환: top-level title/url/source/text도 확인 (하위 우선순위)
    if _has(a.get("text")):
        return False
    if _has(a.get("title")):
        return False
    if _has(a.get("url")):
        return False
    if _has(a.get("source")):
        return False

    # 모든 조건이 없으면 empty
    return True


def _source_key_for_asset(a: dict) -> str:
    """
    empty 드랍 집계용 source key (UNKNOWN 버킷 금지, SSOT).
    
    우선순위:
    1) asset_dict.get("source_id")
    2) asset_dict.get("payload", {}).get("source")
    3) asset_dict.get("source")  (레거시 호환)
    4) "unknown_source"  (절대 "UNKNOWN" 문자열 사용 금지)
    """
    if not isinstance(a, dict):
        return "unknown_source"
    
    payload = a.get("payload", {}) or {}
    if not isinstance(payload, dict):
        payload = {}
    
    # 우선순위 1: source_id (KnowledgeAsset 스키마 기준)
    source_id = a.get("source_id")
    if source_id:
        s = str(source_id).strip()
        if s:
            return s
    
    # 우선순위 2: payload.source
    payload_source = payload.get("source")
    if payload_source:
        s = str(payload_source).strip()
        if s:
            return s
    
    # 우선순위 3: 레거시 호환 (top-level source)
    legacy_source = a.get("source")
    if legacy_source:
        s = str(legacy_source).strip()
        if s:
            return s
    
    # 우선순위 4: payload.source_id (하위 우선순위)
    payload_source_id = payload.get("source_id")
    if payload_source_id:
        s = str(payload_source_id).strip()
        if s:
            return s
    
    # 우선순위 5: provider 계열 (하위 우선순위)
    provider = a.get("provider") or payload.get("provider")
    if provider:
        s = str(provider).strip()
        if s:
            return s
    
    # 최종 fallback: unknown_source (절대 "UNKNOWN" 사용 금지)
    return "unknown_source"


def collect_empty_drop_stats(assets_path: Path, max_samples: int = 20) -> Tuple[int, Dict[str, int], List[Dict[str, Any]]]:
    """
    assets.jsonl 기반 empty 드랍 재계산.

    Returns:
        total: empty asset 총 개수
        by_source: source_id 기준 카운트 (UNKNOWN 키 절대 사용 안 함)
        samples: 샘플 asset 메타 (최대 max_samples)
    """
    total = 0
    by_source: Dict[str, int] = {}
    samples: List[Dict[str, Any]] = []

    if not assets_path.exists():
        return total, by_source, samples

    for a in load_jsonl(assets_path):
        if not isinstance(a, dict):
            continue
        if not is_empty_asset(a):
            continue

        total += 1
        src = _source_key_for_asset(a)
        by_source[src] = by_source.get(src, 0) + 1

        if len(samples) < max_samples:
            payload = a.get("payload", {}) or {}
            text = payload.get("text") or payload.get("content") or payload.get("body") or a.get("text") or ""
            cleaned_text = payload.get("cleaned_text") or ""
            samples.append(
                {
                    "asset_id": a.get("asset_id"),
                    "source_id": a.get("source_id") or payload.get("source_id") or a.get("source"),
                    "category": a.get("category"),
                    "keyword": payload.get("keyword") or (a.get("keywords") or [None])[0],
                    "title": payload.get("title") or a.get("title"),
                    "url": payload.get("url") or a.get("url"),
                    "raw_text_len": len(str(text)),
                    "cleaned_text_len": len(str(cleaned_text)),
                }
            )

    return total, by_source, samples


