"""
Knowledge v1 TTL - Time To Live 자동 삭제 (Discovery 전용)
"""

from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict
from backend.knowledge_v1.store import get_store_root, load_jsonl, append_jsonl
from backend.knowledge_v1.layers import Layer
from backend.knowledge_v1.audit import log_event


def apply_ttl(layer: Layer, ttl_days: int) -> Dict:
    """
    TTL 적용 (Discovery Layer 전용)
    
    Args:
        layer: 레이어 (DISCOVERY만 허용)
        ttl_days: TTL 일수
    
    Returns:
        삭제 통계
    """
    if layer != Layer.DISCOVERY:
        raise ValueError("TTL is only applicable to DISCOVERY layer")
    
    root = get_store_root(layer)
    assets_path = root / "raw" / "assets.jsonl"
    
    if not assets_path.exists():
        return {
            "deleted_count": 0,
            "remaining_count": 0
        }
    
    # TTL 기준 시각
    cutoff_time = datetime.now() - timedelta(days=ttl_days)
    
    # 모든 레코드 로드
    all_assets = list(load_jsonl(assets_path))
    
    # TTL 통과한 레코드 필터링
    remaining = []
    deleted = []
    
    for asset in all_assets:
        fetched_at_str = asset.get("fetched_at", "")
        if not fetched_at_str:
            # fetched_at이 없으면 보존
            remaining.append(asset)
            continue
        
        try:
            # ISO8601 파싱
            if fetched_at_str.endswith("Z"):
                fetched_at_str = fetched_at_str[:-1] + "+00:00"
            fetched_at = datetime.fromisoformat(fetched_at_str.replace("Z", "+00:00"))
            if fetched_at.tzinfo is None:
                fetched_at = fetched_at.replace(tzinfo=datetime.now().astimezone().tzinfo)
            fetched_at = fetched_at.replace(tzinfo=None)  # naive datetime으로 변환
            
            if fetched_at < cutoff_time:
                deleted.append(asset)
            else:
                remaining.append(asset)
        except Exception:
            # 파싱 실패 시 보존
            remaining.append(asset)
    
    # 새 파일로 재작성
    assets_path.parent.mkdir(parents=True, exist_ok=True)
    with open(assets_path, "w", encoding="utf-8") as f:
        for asset in remaining:
            import json
            json.dump(asset, f, ensure_ascii=False)
            f.write("\n")
    
    deleted_count = len(deleted)
    remaining_count = len(remaining)
    
    log_event("TTL_APPLIED", {
        "layer": layer.value,
        "ttl_days": ttl_days,
        "deleted_count": deleted_count,
        "remaining_count": remaining_count
    })
    
    return {
        "deleted_count": deleted_count,
        "remaining_count": remaining_count
    }

