"""
BaselineV4 스키마 정의

v4-Step1: KPI 평가 + Baseline Freeze
"""

from typing import Dict, Any, Optional, Union
from datetime import datetime, timezone


def utc_now_iso() -> str:
    """UTC 현재 시간을 ISO8601 형식으로 반환 (끝은 'Z')"""
    dt = datetime.now(timezone.utc).replace(microsecond=0)
    return dt.isoformat().replace("+00:00", "Z")


def utc_now_compact() -> str:
    """UTC 현재 시간을 컴팩트 형식으로 반환 (백업 파일명용: 20251229T000000Z)"""
    dt = datetime.now(timezone.utc)
    return dt.strftime("%Y%m%dT%H%M%SZ")


def create_baseline_v4(
    run_id: str,
    inputs: Dict[str, Any],
    kpis: Dict[str, Union[bool, int, float, str]],
    evidence: Dict[str, Any],
    notes: Dict[str, Any],
    created_at: Optional[str] = None
) -> Dict[str, Any]:
    """
    BaselineV4 생성
    
    Args:
        run_id: 실행 ID
        inputs: 입력 파일 경로 dict
        kpis: KPI 값 dict
        evidence: 증거 dict (source_hashes_sha256 포함)
        notes: 노트 dict (missing_inputs, warnings 포함)
        created_at: 생성 시각 (None이면 현재 시각)
    
    Returns:
        Dict: BaselineV4 JSON 데이터
    """
    if created_at is None:
        created_at = utc_now_iso()
    
    baseline_id = f"baseline_v4_step1:{run_id}:{created_at}"
    
    return {
        "run_id": run_id,
        "baseline_id": baseline_id,
        "created_at": created_at,
        "inputs": inputs,
        "kpis": kpis,
        "evidence": evidence,
        "notes": notes,
        "version": "v4_step1",
        "state": "FROZEN"
    }

