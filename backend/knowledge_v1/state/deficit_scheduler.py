"""
Deficit Scheduler - 카테고리별 부족분 계산 및 우선순위 스케줄링
"""

from typing import Dict, List, Tuple
from backend.knowledge_v1.paths import get_root


def compute_category_deficit(
    categories: List[str],
    target_per_category: int,
    cycle_id: str = None
) -> Dict[str, int]:
    """
    카테고리별 부족분 계산
    
    Args:
        categories: 카테고리 리스트
        target_per_category: 카테고리당 목표 키워드 수
        cycle_id: cycle_id (스냅샷에서 읽기)
    
    Returns:
        {category: deficit}
    """
    root = get_root()
    kd_root = root / "keyword_discovery"
    
    deficits = {}
    
    for category in categories:
        # 스냅샷에서 키워드 수 확인
        if cycle_id:
            snapshot_dir = kd_root / "snapshots" / cycle_id
            keywords_file = snapshot_dir / f"keywords_{category}_raw.jsonl"
            
            count = 0
            if keywords_file.exists():
                try:
                    with open(keywords_file, "r", encoding="utf-8") as f:
                        for line in f:
                            line = line.strip()
                            if line:
                                count += 1
                except Exception:
                    count = 0
        
        # 부족분 = 목표 - 현재
        current = count if cycle_id else 0
        deficit = max(0, target_per_category - current)
        deficits[category] = deficit
    
    return deficits


def schedule_by_deficit(
    categories: List[str],
    target_per_category: int,
    cycle_id: str = None
) -> List[Tuple[str, int]]:
    """
    부족분 큰 순서로 카테고리 정렬
    
    Returns:
        [(category, deficit), ...] (부족분 큰 순)
    """
    deficits = compute_category_deficit(categories, target_per_category, cycle_id)
    sorted_categories = sorted(deficits.items(), key=lambda x: x[1], reverse=True)
    return sorted_categories

