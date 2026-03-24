"""
SOURCE EVOLUTION ENGINE - 소스 진화 및 점수 기반 자동 격리/우선순위
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple


def calculate_source_score(
    gate_pass_rate: float,
    avg_view_norm: float,
    drift_rate: float,
    revenue_proxy_score: float = 0.5
) -> float:
    """
    소스 점수 계산
    
    score = 0.35 * gate_pass_rate
         + 0.35 * avg_view_norm
         + 0.15 * (1 - drift_rate)
         + 0.15 * revenue_proxy_score
    
    Args:
        gate_pass_rate: 게이트 통과율 (0.0 ~ 1.0)
        avg_view_norm: 평균 조회수 정규화 값 (0.0 ~ 1.0)
        drift_rate: 드리프트 비율 (0.0 ~ 1.0)
        revenue_proxy_score: 수익 프록시 점수 (0.0 ~ 1.0)
        
    Returns:
        float: 소스 점수 (0.0 ~ 1.0)
    """
    score = (
        0.35 * gate_pass_rate +
        0.35 * avg_view_norm +
        0.15 * (1.0 - drift_rate) +
        0.15 * revenue_proxy_score
    )
    
    # 0.0 ~ 1.0 범위로 클램핑
    return max(0.0, min(1.0, score))


def apply_moving_average(
    current_score: float,
    historical_scores: List[float],
    window: int = 3
) -> float:
    """
    3-run moving average 적용
    
    Args:
        current_score: 현재 점수
        historical_scores: 과거 점수 리스트
        window: 이동 평균 윈도우 크기
        
    Returns:
        float: 이동 평균 점수
    """
    all_scores = historical_scores + [current_score]
    recent_scores = all_scores[-window:]
    
    if not recent_scores:
        return current_score
    
    return sum(recent_scores) / len(recent_scores)


def evaluate_source_status(score: float) -> Tuple[str, bool]:
    """
    소스 상태 평가
    
    Args:
        score: 소스 점수
        
    Returns:
        Tuple[str, bool]: (상태, 격리 여부)
    """
    if score < 0.25:
        return ("quarantine", True)
    elif score > 0.75:
        return ("priority_boost", False)
    else:
        return ("normal", False)


def compute_evolution_snapshot(categories_result: Dict[str, Any], stats: Dict[str, Any]) -> Dict[str, Any]:
    """
    현재 런의 확정 가능한 값만 기록하는 evolution snapshot
    
    Args:
        categories_result: report["categories"] 딕셔너리
        stats: report["summary"] 딕셔너리
        
    Returns:
        Dict: evolution snapshot
    """
    from datetime import datetime
    
    # 모든 카테고리의 docs_by_source 합산
    sources_agg = {}
    for cat, cat_data in categories_result.items():
        if isinstance(cat_data, dict):
            docs_by_source = cat_data.get("docs_by_source", {})
            if isinstance(docs_by_source, dict):
                for source, count in docs_by_source.items():
                    sources_agg[source] = sources_agg.get(source, 0) + count
    
    # source_probabilities.weights를 next_run_weights_hint로 사용
    # (실제로는 load_source_probabilities로 가져와야 하지만, 여기서는 간단히 sources_agg 기반으로 생성)
    next_run_weights_hint = {}
    total_count = sum(sources_agg.values())
    if total_count > 0:
        for source, count in sources_agg.items():
            next_run_weights_hint[source] = float(count) / total_count
    else:
        # 기본값
        next_run_weights_hint = {"rss": 1.0}
    
    return {
        "version": 1,
        "computed_at": datetime.utcnow().isoformat() + "Z",
        "run_summary": {
            "total_ingested": stats.get("total_ingested", 0),
            "total_derived": stats.get("total_derived", 0),
            "total_blocked": stats.get("total_blocked", 0),
            "total_promoted": stats.get("total_promoted", 0),
        },
        "sources_agg": sources_agg,
        "next_run_weights_hint": next_run_weights_hint,
        "notes": "v1 baseline; KPI 연결 시 score 확장"
    }


def append_evolution_history(repo_root: Path, snapshot: Dict[str, Any]) -> str:
    """
    SSOT 경로 evolution_history.json에 snapshot append
    
    Args:
        repo_root: 레포 루트
        snapshot: compute_evolution_snapshot 결과
        
    Returns:
        str: 저장된 경로
    """
    from backend.knowledge_v1.paths import get_evolution_history_path, ensure_governance_dir
    from backend.knowledge_v1.io.json_io import load_json, dump_json
    
    ensure_governance_dir(repo_root)
    history_path = get_evolution_history_path(repo_root)
    
    # 기존 이력 로드 (없으면 빈 리스트)
    history_list = []
    if history_path.exists():
        try:
            history_list = load_json(history_path)
            if not isinstance(history_list, list):
                history_list = []
        except Exception:
            history_list = []
    
    # snapshot append
    history_list.append(snapshot)
    
    # 저장 (UTF-8 강제, ensure_ascii=False)
    dump_json(history_path, history_list)
    
    return str(history_path)


def save_evolution_history(history: Dict[str, Any], repo_root: Path) -> Path:
    """진화 이력 저장 (레거시 호환)"""
    from backend.knowledge_v1.paths import get_evolution_history_path, ensure_governance_dir
    from backend.knowledge_v1.io.json_io import dump_json
    
    ensure_governance_dir(repo_root)
    history_path = get_evolution_history_path(repo_root)
    
    # UTF-8 강제 저장 (ensure_ascii=False)
    dump_json(history_path, history)
    
    return history_path


def load_evolution_history(repo_root: Path) -> Optional[Dict[str, Any]]:
    """진화 이력 로드 (레거시 호환)"""
    from backend.knowledge_v1.paths import get_evolution_history_path
    from backend.knowledge_v1.io.json_io import load_json
    
    history_path = get_evolution_history_path(repo_root)
    if not history_path.exists():
        return {}
    
    # UTF-8 강제 로드
    data = load_json(history_path)
    # 리스트인 경우 마지막 항목 반환 (레거시 호환)
    if isinstance(data, list):
        return data[-1] if data else {}
    return data

