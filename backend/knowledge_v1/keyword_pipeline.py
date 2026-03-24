from __future__ import annotations

from dataclasses import asdict
from typing import Dict, List, Tuple
from collections import defaultdict

from backend.knowledge_v1.keyword_sources import RawKeyword, _norm_keyword


def _score_keyword(sources: List[str], subtypes: List[str]) -> float:
    # 하드 고정 스코어: "다중 출처"를 최우선 신뢰 신호로 사용
    # - source 다양성 가중
    # - youtube/trends/news는 "수요/추세/맥락"으로 추가 가점
    uniq_sources = set(sources)
    base = float(len(uniq_sources)) * 10.0

    bonus = 0.0
    if "youtube" in uniq_sources:
        bonus += 6.0
    if "google_trends" in uniq_sources or "trending" in uniq_sources:
        bonus += 6.0
    if "gdelt_news" in uniq_sources:
        bonus += 4.0
    if "wikipedia" in uniq_sources:
        bonus += 2.0

    # subtype 다양성 보너스
    bonus += float(len(set(subtypes))) * 1.0
    return base + bonus


def build_keyword_evidence_packet(
    *,
    cycle_id: str,
    category: str,
    raw_keywords: List[RawKeyword],
    per_category_limit: int = 80,
) -> Dict:
    """
    Gate-1(카테고리별 상위 80개) 증거 패킷 생성
    - keyword_norm 기준 병합
    - sources/evidence_hashes를 합치고 score 계산
    """
    merged: Dict[str, Dict] = {}
    for rk in raw_keywords:
        kw = _norm_keyword(rk.keyword)
        if len(kw) < 3:
            continue
        k = kw.lower()
        if k not in merged:
            merged[k] = {
                "keyword": kw,
                "keyword_norm": k,
                "sources": [],
                "subtypes": [],
                "evidence_hashes": [],
                "country": rk.country,
                "windows": [],
                "raw_refs": [],
            }
        merged[k]["sources"].append(rk.source)
        merged[k]["subtypes"].append(rk.subtype)
        merged[k]["evidence_hashes"].append(rk.evidence_hash)
        merged[k]["windows"].append(rk.window)
        merged[k]["raw_refs"].append(rk.raw_ref)

    rows: List[Dict] = []
    for k, v in merged.items():
        score = _score_keyword(v["sources"], v["subtypes"])
        rows.append(
            {
                "keyword": v["keyword"],
                "keyword_norm": v["keyword_norm"],
                "sources": sorted(list(set(v["sources"]))),
                "subtypes": sorted(list(set(v["subtypes"]))),
                "score": score,
                "evidence_hashes": sorted(list(set(v["evidence_hashes"]))),
                "country": v["country"],
                "windows": sorted(list(set(v["windows"]))),
                "raw_refs": sorted(list(set(v["raw_refs"]))),
            }
        )

    # score 내림차순, keyword_norm 오름차순(결정적 정렬)
    rows.sort(key=lambda r: (-r["score"], r["keyword_norm"]))
    rows = rows[:per_category_limit]

    return {
        "cycle_id": cycle_id,
        "category": category,
        "gate": {"per_category_limit": per_category_limit},
        "keywords": rows,
    }


def build_daily_keyword_pack(
    *,
    cycle_id: str,
    categories: List[str],
    per_category_packets: Dict[str, Dict],
    daily_total_limit: int = 400,
) -> Dict:
    """
    Gate-1(전체 400개) 일일 패킷
    - 카테고리별 top80을 모아 score 기준으로 전역 상위 400개로 컷
    """
    all_rows: List[Tuple[str, Dict]] = []
    for cat in categories:
        pkt = per_category_packets.get(cat)
        if not pkt:
            continue
        for r in pkt.get("keywords", []):
            all_rows.append((cat, r))

    all_rows.sort(key=lambda cr: (-cr[1]["score"], cr[1]["keyword_norm"]))
    all_rows = all_rows[:daily_total_limit]

    out = []
    for cat, r in all_rows:
        rr = dict(r)
        rr["category"] = cat
        out.append(rr)

    return {
        "cycle_id": cycle_id,
        "gate": {"daily_total_limit": daily_total_limit},
        "keywords": out,
    }

