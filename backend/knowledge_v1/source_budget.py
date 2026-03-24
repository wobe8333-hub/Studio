"""
Source Budget - Yield 기반 소스별 호출량 조정
"""

import json
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime
from backend.knowledge_v1.paths import get_root


def _find_repo_root() -> Path:
    """repo root 탐색"""
    p = Path(__file__).resolve()
    for parent in [p.parent] + list(p.parents):
        if (parent / "backend").is_dir() and (parent / "config").is_dir():
            return parent
    raise RuntimeError(f"repo root not found. Searched from: {__file__}")


def compute_source_yield(
    source_id: str,
    cycle_id: str,
    policy: Dict[str, Any] = None
) -> float:
    """
    소스별 Yield 계산 (성공률 기반)
    
    Args:
        source_id: 소스 ID
        cycle_id: cycle_id
        policy: 정책 딕셔너리
    
    Returns:
        Yield (0.0~1.0)
    """
    root = get_root()
    kd_root = root / "keyword_discovery"
    snapshots_dir = kd_root / "snapshots" / cycle_id
    
    # 스냅샷에서 소스별 키워드 수 집계
    source_count = 0
    total_count = 0
    
    for category in ["history", "mystery", "economy", "myth", "science", "war_history"]:
        keywords_file = snapshots_dir / f"keywords_{category}_raw.jsonl"
        if keywords_file.exists():
            try:
                with open(keywords_file, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            entry = json.loads(line)
                            total_count += 1
                            if entry.get("source") == source_id:
                                source_count += 1
                        except Exception:
                            continue
            except Exception:
                continue
    
    if total_count == 0:
        return 0.0
    
    return source_count / total_count


def allocate_budget(
    cycle_id: str,
    policy: Dict[str, Any] = None
) -> Dict[str, int]:
    """
    다음 cycle 호출량 조정 (Yield 기반)
    
    Returns:
        {source_id: next_call_count}
    """
    if policy is None:
        from backend.knowledge_v1.policy.validator import load_policy
        policy = load_policy()
    
    budget_config = policy.get("yield_budget_allocator", {})
    min_calls = budget_config.get("min_calls", 1)
    max_calls = budget_config.get("max_calls", 10)
    
    sources = ["yt_api", "yt_dlp", "dataset", "wiki", "news"]
    budget = {}
    
    for source_id in sources:
        yield_val = compute_source_yield(source_id, cycle_id, policy)
        
        # Yield 기반 호출량 계산
        # yield가 높을수록 더 많이 호출
        call_count = int(min_calls + (max_calls - min_calls) * yield_val)
        call_count = max(min_calls, min(max_calls, call_count))
        
        budget[source_id] = call_count
    
    return budget


def save_budget(cycle_id: str, budget: Dict[str, int]) -> Path:
    """Budget 저장"""
    root = get_root()
    kd_root = root / "keyword_discovery"
    snapshots_dir = kd_root / "snapshots" / cycle_id
    snapshots_dir.mkdir(parents=True, exist_ok=True)
    
    budget_path = snapshots_dir / f"budget_{cycle_id}.json"
    with open(budget_path, "w", encoding="utf-8") as f:
        json.dump({
            "cycle_id": cycle_id,
            "created_at": datetime.utcnow().isoformat() + "Z",
            "budget": budget
        }, f, ensure_ascii=False, indent=2)
    
    return budget_path

