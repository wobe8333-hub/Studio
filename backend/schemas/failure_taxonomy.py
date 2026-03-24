"""
Failure Taxonomy Schema (P1)

Enum 기반 실패 분류:
- INPUT: 입력 데이터 문제
- STRUCTURE: 구조/스키마 문제
- MODEL: 모델/LLM 문제
- RESOURCE: 리소스/시스템 문제
- EXTERNAL: 외부 서비스 문제
"""

from enum import Enum
from typing import Dict, Any, Optional, List


class FailureTaxonomy(str, Enum):
    """실패 분류 Enum"""
    INPUT = "INPUT"
    STRUCTURE = "STRUCTURE"
    MODEL = "MODEL"
    RESOURCE = "RESOURCE"
    EXTERNAL = "EXTERNAL"


def normalize_failure_taxonomy(value: Any) -> FailureTaxonomy:
    """
    문자열/값을 FailureTaxonomy Enum으로 정규화
    
    Args:
        value: 분류 값 (문자열, Enum 등)
    
    Returns:
        FailureTaxonomy: 정규화된 Enum 값
    """
    if isinstance(value, FailureTaxonomy):
        return value
    
    if isinstance(value, str):
        value_upper = value.upper()
        for taxonomy in FailureTaxonomy:
            if taxonomy.value == value_upper:
                return taxonomy
    
    # 기본값: STRUCTURE
    return FailureTaxonomy.STRUCTURE


def create_failure_classification(
    primary_taxonomy: FailureTaxonomy,
    secondary_tags: Optional[List[str]] = None,
    valuable_failure: bool = False,
    valuable_reason: Optional[str] = None
) -> Dict[str, Any]:
    """
    Step5 결과 구조 생성
    
    Args:
        primary_taxonomy: 주요 분류 (Enum)
        secondary_tags: 보조 태그 리스트
        valuable_failure: 가치 있는 실패 여부
        valuable_reason: 가치 있는 실패 사유
    
    Returns:
        Dict: Step5 결과 구조
    """
    return {
        "primary_taxonomy": primary_taxonomy.value,
        "secondary_tags": secondary_tags or [],
        "valuable_failure": valuable_failure,
        "valuable_reason": valuable_reason
    }


def convert_string_to_taxonomy(value: str) -> FailureTaxonomy:
    """
    문자열을 FailureTaxonomy로 변환 (하위 호환)
    
    Args:
        value: 분류 문자열
    
    Returns:
        FailureTaxonomy: Enum 값
    """
    return normalize_failure_taxonomy(value)

