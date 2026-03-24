"""
Failure Taxonomy - 실패 분류 표준 정의

처음문서_v1.2 기준:
"실패는 기록이 아니라, 이후 단계의 회피·선택 입력값이다."
"""

from enum import Enum
from typing import Dict, Any, Optional


class FailureType(str, Enum):
    """실패 유형"""
    INPUT = "INPUT"  # 입력 데이터 문제
    STRUCTURE = "STRUCTURE"  # 구조/스키마 문제
    MODEL = "MODEL"  # 모델/알고리즘 문제
    RESOURCE = "RESOURCE"  # 리소스 부족/제한
    EXTERNAL = "EXTERNAL"  # 외부 의존성 문제


def classify_failure(
    failed_step: str,
    error_message: str,
    manifest: Optional[Dict[str, Any]] = None,
    details: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    실패를 분류하여 failure_summary 생성
    
    Args:
        failed_step: 실패한 step 이름
        error_message: 에러 메시지
        manifest: run manifest (선택)
        details: 상세 정보 (선택, v1.4 확장용)
    
    Returns:
        Dict: failure_summary
        {
            "primary_category": FailureType,
            "severity": "hard" | "soft",
            "policy_hint": str,
            "failed_step": str,
            "secondary_tags": List[str],  # v1.4 확장
            "valuable_failure": bool,  # v1.4 확장
            "valuable_reason": Optional[str]  # v1.4 확장
        }
    """
    import re
    error_lower = error_message.lower()
    
    # INPUT 실패 판정
    if any(keyword in error_lower for keyword in [
        "missing", "not found", "invalid input", "required field",
        "manifest_missing", "scenes_fixed.json", "repro", "environment"
    ]):
        primary_category = FailureType.INPUT
        severity = "hard"
        policy_hint = "입력 데이터 검증 강화 필요"
    
    # STRUCTURE 실패 판정
    elif any(keyword in error_lower for keyword in [
        "schema", "structure", "format", "json", "parse", "decode"
    ]):
        primary_category = FailureType.STRUCTURE
        severity = "hard"
        policy_hint = "스키마 검증 강화 필요"
    
    # RESOURCE 실패 판정
    elif any(keyword in error_lower for keyword in [
        "memory", "disk", "timeout", "resource", "ffmpeg", "subprocess"
    ]):
        primary_category = FailureType.RESOURCE
        severity = "hard"
        policy_hint = "리소스 할당/제한 조정 필요"
    
    # EXTERNAL 실패 판정
    elif any(keyword in error_lower for keyword in [
        "network", "api", "connection", "external", "dependency"
    ]):
        primary_category = FailureType.EXTERNAL
        severity = "hard"
        policy_hint = "외부 의존성 재시도/폴백 필요"
    
    # MODEL 실패 판정 (기본값)
    else:
        primary_category = FailureType.MODEL
        severity = "soft"
        policy_hint = "모델/알고리즘 파라미터 조정 필요"
    
    # v1.4 확장: secondary_tags (보수적 키워드 매칭)
    secondary_tags = []
    
    # SEMANTIC_FAILURE: 의미적 실패 신호
    if any(keyword in error_lower for keyword in [
        "semantic", "meaning", "interpretation", "context", "logic"
    ]):
        secondary_tags.append("SEMANTIC_FAILURE")
    
    # IDENTITY_DRIFT: 정체성 드리프트 신호
    if any(keyword in error_lower for keyword in [
        "identity", "drift", "consistency", "coherence"
    ]):
        secondary_tags.append("IDENTITY_DRIFT")
    
    # POLICY_REGRESSION: 정책 회귀 신호
    if any(keyword in error_lower for keyword in [
        "policy", "regression", "violation", "constraint"
    ]):
        secondary_tags.append("POLICY_REGRESSION")
    
    # MEMORY_CONTAMINATION: 메모리 오염 신호
    if any(keyword in error_lower for keyword in [
        "memory", "contamination", "corruption", "leak"
    ]):
        secondary_tags.append("MEMORY_CONTAMINATION")
    
    # DATA_TRUST_LOW: 데이터 신뢰도 낮음 신호
    if any(keyword in error_lower for keyword in [
        "trust", "reliability", "integrity", "validation"
    ]):
        secondary_tags.append("DATA_TRUST_LOW")
    
    # details에서 failures 목록 확인 (전체 컨텍스트 기반 태깅)
    if details:
        failures_list = details.get("failures", [])
        failures_text = " ".join([str(f) for f in failures_list]).lower()
        
        # DATA_SILENCE_SIGNAL: 데이터 침묵 신호
        if "silence" in failures_text or "empty" in failures_text:
            if "DATA_SILENCE_SIGNAL" not in secondary_tags:
                secondary_tags.append("DATA_SILENCE_SIGNAL")
    
    # v1.4 확장: valuable_failure 판정
    valuable_failure = False
    valuable_reason = None
    
    # 재현성/외부 제약으로 실패했는데, 구조/입력은 정상인 케이스
    if details:
        failures_list = details.get("failures", [])
        failures_text = " ".join([str(f) for f in failures_list]).lower()
        
        # valuable_failure 조건: 외부 제약 실패 + 입력/구조 정상
        if any(keyword in failures_text for keyword in [
            "model_output_empty", "image_gen_rate_limited", "external_timeout",
            "api_rate_limit", "network_timeout", "external_service"
        ]):
            # 입력/구조 관련 실패가 없으면 valuable
            if not any(keyword in failures_text for keyword in [
                "input", "structure", "schema", "format", "missing", "invalid"
            ]):
                valuable_failure = True
                valuable_reason = "외부 제약/재현성 이슈로 인한 실패 (입력/구조 정상)"
    
    return {
        "primary_category": primary_category.value,
        "severity": severity,
        "policy_hint": policy_hint,
        "failed_step": failed_step,
        "secondary_tags": secondary_tags,
        "valuable_failure": valuable_failure,
        "valuable_reason": valuable_reason
    }

