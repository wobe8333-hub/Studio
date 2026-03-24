"""
MemorySnapshotV3 스키마 정의

v3-Step1: Reference-only Memory Layer
- 기존 run 산출물로부터 관측 데이터를 읽어 MemorySnapshotV3 생성
- 생성 파이프라인 영향 금지
- 판단/추천/자동선택 금지
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from datetime import datetime, timezone


def utc_now_iso() -> str:
    """UTC 현재 시간을 ISO8601 형식으로 반환"""
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def missing_dict(reason: str) -> Dict[str, str]:
    """
    데이터가 없을 때 사용하는 표준 형식
    
    Args:
        reason: 누락 사유
    
    Returns:
        Dict: {"status": "missing", "reason": reason}
    """
    return {"status": "missing", "reason": reason}


@dataclass
class MemorySnapshotV3:
    """
    MemorySnapshotV3 스키마
    
    v3-Step1 필수 최상위 키:
    - run_id: str
    - collected_at: ISO8601 UTC str
    - source_paths: dict
    - run_state: dict
    - step_status_map: dict
    - artifacts_index: dict
    - verify_summary: dict
    - metrics_summary: dict
    - structure_summary: dict
    - tags: list[str]
    - questions_seed: list[dict]
    - memory_version: "v3_step1"
    - state: "ACTIVE"
    """
    run_id: str
    collected_at: str
    source_paths: Dict[str, Any]
    run_state: Dict[str, Any]
    step_status_map: Dict[str, Any]
    artifacts_index: Dict[str, Any]
    verify_summary: Dict[str, Any]
    metrics_summary: Dict[str, Any]
    structure_summary: Dict[str, Any]
    tags: List[str]
    questions_seed: List[Dict[str, Any]]
    memory_version: str = "v3_step1"
    state: str = "ACTIVE"
    
    def to_dict(self) -> Dict[str, Any]:
        """Dict로 변환"""
        return asdict(self)

