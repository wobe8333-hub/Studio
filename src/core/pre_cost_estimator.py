"""
PRE-RUN COST ESTIMATOR - 사전 비용 차단
실행 전 비용 예측 후 초과 시 차단
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Any, Optional, Tuple


# 비용 상수 (USD)
AVG_COST_PER_API_CALL = 0.001  # YouTube API 호출당 평균 비용
AVG_COST_PER_TOKEN = 0.000002  # 토큰당 평균 비용 (예: GPT API)
COST_LIMIT_PER_RUN = 5.0  # 실행당 최대 비용 (USD)


def estimate_pre_run_cost(
    estimated_api_calls: int = 0,
    estimated_tokens: int = 0,
    custom_cost_per_call: Optional[float] = None,
    custom_token_price: Optional[float] = None
) -> Tuple[float, Dict[str, Any]]:
    """
    실행 전 비용 예측
    
    Args:
        estimated_api_calls: 예상 API 호출 수
        estimated_tokens: 예상 토큰 수
        custom_cost_per_call: 커스텀 API 호출당 비용
        custom_token_price: 커스텀 토큰당 가격
        
    Returns:
        Tuple[float, Dict[str, Any]]: (예상 비용, 상세 내역)
    """
    cost_per_call = custom_cost_per_call or AVG_COST_PER_API_CALL
    token_price = custom_token_price or AVG_COST_PER_TOKEN
    
    api_cost = estimated_api_calls * cost_per_call
    token_cost = estimated_tokens * token_price
    total_cost = api_cost + token_cost
    
    breakdown = {
        "estimated_api_calls": estimated_api_calls,
        "estimated_tokens": estimated_tokens,
        "api_cost": api_cost,
        "token_cost": token_cost,
        "total_cost": total_cost,
        "cost_limit": COST_LIMIT_PER_RUN,
        "cost_per_call": cost_per_call,
        "token_price": token_price,
    }
    
    return total_cost, breakdown


def check_cost_limit(estimated_cost: float, cost_limit: Optional[float] = None) -> Tuple[bool, str]:
    """
    비용 한도 확인
    
    Args:
        estimated_cost: 예상 비용
        cost_limit: 비용 한도 (None이면 기본값 사용)
        
    Returns:
        Tuple[bool, str]: (허용 여부, 메시지)
    """
    limit = cost_limit or COST_LIMIT_PER_RUN
    
    if estimated_cost > limit:
        return (
            False,
            f"COST_EXCEEDED: estimated_cost={estimated_cost:.4f} USD > cost_limit={limit:.4f} USD. Execution blocked."
        )
    
    return (
        True,
        f"COST_OK: estimated_cost={estimated_cost:.4f} USD <= cost_limit={limit:.4f} USD"
    )


def save_cost_projection(projection: Dict[str, Any], repo_root: Path) -> Path:
    """비용 예측 저장"""
    governance_dir = repo_root / "data" / "knowledge_v1_store" / "governance"
    governance_dir.mkdir(parents=True, exist_ok=True)
    
    projection_path = governance_dir / "cost_projection.json"
    with open(projection_path, "w", encoding="utf-8") as f:
        json.dump(projection, f, ensure_ascii=False, indent=2)
    
    return projection_path


def load_cost_projection(repo_root: Path) -> Optional[Dict[str, Any]]:
    """비용 예측 로드"""
    projection_path = repo_root / "data" / "knowledge_v1_store" / "governance" / "cost_projection.json"
    if not projection_path.exists():
        return None
    
    with open(projection_path, "r", encoding="utf-8") as f:
        return json.load(f)

