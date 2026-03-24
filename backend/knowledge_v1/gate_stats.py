"""
Gate Stats - 게이트 통계 산출 (READY/BLOCKED/REFERENCE_ONLY/FAIL_REASON 카운트)
"""

import json
from pathlib import Path
from typing import Dict, Any, Optional
from backend.knowledge_v1.paths import get_store_root, get_reports_dir
from backend.knowledge_v1.store import load_jsonl


def compute_gate_stats(store: str = "discovery") -> Dict[str, Any]:
    """
    게이트 통계 산출 (reason_code 기반 진단)
    
    Args:
        store: "discovery" | "approved"
    
    Returns:
        Dict: 게이트 통계 (totals, reasons_top, reasons_by_category 포함)
    """
    from backend.knowledge_v1.paths import get_assets_path, get_chunks_path, get_read_root
    
    assets_path = get_assets_path(store)
    chunks_path = get_chunks_path(store)
    
    # eligibility + reason 로드 (used_assets.jsonl + blocked_assets.jsonl에서) - 읽기 전용
    store_root = get_store_root(store)
    used_path = store_root / "used" / "used_assets.jsonl"
    eligibility_data = {}  # {asset_id: {"eligible_for": str, "reason": str, "category": str}}
    
    # used_assets.jsonl에서 로드 (READY/REFERENCE_ONLY/LIMITED_INJECTION/FULLY_USABLE)
    if used_path.exists():
        for row in load_jsonl(used_path):
            asset_id = row.get("asset_id")
            if asset_id:
                eligibility_data[asset_id] = {
                    "eligible_for": row.get("eligible_for", "REFERENCE_ONLY"),
                    "reason": row.get("reason", "unknown_reason"),  # reason_code (강제)
                    "category": row.get("category")  # 카테고리 (있으면 사용)
                }
    
    # blocked_assets.jsonl에서도 로드 (BLOCKED reason_code 추적)
    blocked_path = store_root / "blocked" / "blocked_assets.jsonl"
    if blocked_path.exists():
        for row in load_jsonl(blocked_path):
            asset_id = row.get("asset_id")
            if asset_id and asset_id not in eligibility_data:
                # BLOCKED도 reason_code 추적 (진단 가능)
                eligibility_data[asset_id] = {
                    "eligible_for": "BLOCKED",
                    "reason": row.get("block_reason") or row.get("reason") or "blocked_unknown",  # reason_code
                    "category": row.get("category")
                }
    
    # 레거시 경로도 확인 (읽기 전용, 하위 호환성)
    legacy_root = get_read_root()
    legacy_used_path = legacy_root / "used" / "used_assets.jsonl"
    
    if legacy_used_path.exists():
        for row in load_jsonl(legacy_used_path):
            asset_id = row.get("asset_id")
            if asset_id and asset_id not in eligibility_data:
                eligibility_data[asset_id] = {
                    "eligible_for": row.get("eligible_for", "REFERENCE_ONLY"),
                    "reason": row.get("reason", "unknown_reason"),
                    "category": row.get("category")
                }
    
    # 레거시 blocked 경로도 확인
    legacy_blocked_path = legacy_root / "blocked" / "blocked_assets.jsonl"
    if legacy_blocked_path.exists():
        for row in load_jsonl(legacy_blocked_path):
            asset_id = row.get("asset_id")
            if asset_id and asset_id not in eligibility_data:
                eligibility_data[asset_id] = {
                    "eligible_for": "BLOCKED",
                    "reason": row.get("block_reason") or row.get("reason") or "blocked_unknown",
                    "category": row.get("category")
                }
    
    # asset 카테고리 매핑 생성 (reason_by_category를 위해)
    asset_category_map = {}
    if assets_path.exists():
        for row in load_jsonl(assets_path):
            asset_id = row.get("asset_id")
            category = row.get("category", "unknown")
            if asset_id:
                asset_category_map[asset_id] = category
                # eligibility_data에 카테고리 업데이트
                if asset_id in eligibility_data:
                    eligibility_data[asset_id]["category"] = category
    
    # assets 카운트
    assets_count = 0
    if assets_path.exists():
        for _ in load_jsonl(assets_path):
            assets_count += 1
    
    # chunks 카운트: 라인 수가 아니라 유니크 chunk_id 수 (중복 누적 시에도 gate_stats_sha256 안정화)
    unique_chunk_keys = set()
    if chunks_path.exists():
        for row in load_jsonl(chunks_path):
            cid = row.get("chunk_id")
            if cid:
                unique_chunk_keys.add(cid)
            else:
                unique_chunk_keys.add((row.get("asset_id", ""), row.get("text", "")))
    chunks_count = len(unique_chunk_keys)
    
    # eligibility 통계
    stats = {
        "READY": 0,
        "BLOCKED": 0,
        "REFERENCE_ONLY": 0,
        "LIMITED_INJECTION": 0,
        "FULLY_USABLE": 0,
        "UNKNOWN": 0
    }
    
    # reason_code 집계 (모든 reason 수집)
    reason_counts = {}  # {reason_code: count}
    reason_by_category = {}  # {category: {reason_code: count}}
    
    # 결정론: dict iteration 금지, key 정렬 후 누적
    for asset_id, data in sorted(eligibility_data.items(), key=lambda x: (x[0], str(x[1].get("reason", "")))):
        eligible_for = data["eligible_for"]
        reason_code = data.get("reason", "unknown_reason")  # reason_code 강제
        category = data.get("category") or asset_category_map.get(asset_id, "unknown")
        
        # eligible_for 통계
        if eligible_for == "READY" or eligible_for == "FULLY_USABLE":
            stats["READY"] += 1
        elif eligible_for == "BLOCKED":
            stats["BLOCKED"] += 1
        elif eligible_for == "REFERENCE_ONLY":
            stats["REFERENCE_ONLY"] += 1
        elif eligible_for == "LIMITED_INJECTION":
            stats["LIMITED_INJECTION"] += 1
        elif eligible_for == "FULLY_USABLE":
            stats["FULLY_USABLE"] += 1
        else:
            stats["UNKNOWN"] += 1
        
        # reason_code 집계
        reason_counts[reason_code] = reason_counts.get(reason_code, 0) + 1
        
        # 카테고리별 reason_code 집계
        if category not in reason_by_category:
            reason_by_category[category] = {}
        reason_by_category[category][reason_code] = reason_by_category[category].get(reason_code, 0) + 1
    
    # chunks per asset 평균 계산
    avg_chunks_per_asset = chunks_count / assets_count if assets_count > 0 else 0.0
    
    # reasons_top (상위 10개 reason_code) - 정렬로 결정론
    reasons_top = sorted(reason_counts.items(), key=lambda x: (-x[1], x[0]))[:10]
    reasons_top_dict = dict(sorted((r, c) for r, c in reasons_top))
    # reasons_by_category: 키 정렬로 결정론 (generated_at 등 시간 필드 없음)
    reason_by_category_sorted = {cat: dict(sorted(inner.items())) for cat, inner in sorted(reason_by_category.items())}
    all_reasons_sorted = dict(sorted(reason_counts.items()))
    
    totals = {
        "total_assets": assets_count,
        "total_chunks": chunks_count,
        "total_eligible": len(eligibility_data),
        **stats
    }
    
    result = {
        "store": store,
        "assets_count": assets_count,
        "chunks_count": chunks_count,
        "avg_chunks_per_asset": round(avg_chunks_per_asset, 2),
        "eligibility_stats": stats,
        "totals": totals,
        "reasons_top": reasons_top_dict,
        "reasons_by_category": reason_by_category_sorted,
        "all_reasons": all_reasons_sorted,
    }
    return result


def save_gate_stats(store: str = "discovery", gate_stats_path: Optional[Path] = None) -> Path:
    """
    게이트 통계를 파일로 저장.

    Args:
        store: "discovery" | "approved"
        gate_stats_path: 지정 시 이 경로에 저장 (SSOT 하드락용). None이면 get_reports_dir() 기반.

    Returns:
        Path: 저장된 파일 경로
    """
    from backend.knowledge_v1.store import atomic_write_json

    stats = compute_gate_stats(store)
    if gate_stats_path is not None:
        gate_stats_path.parent.mkdir(parents=True, exist_ok=True)
        atomic_write_json(gate_stats_path, stats, sort_keys=True)
        return gate_stats_path
    reports_dir = get_reports_dir()
    reports_dir.mkdir(parents=True, exist_ok=True)
    stats_path = reports_dir / "gate_stats.json"
    atomic_write_json(stats_path, stats, sort_keys=True)
    return stats_path

