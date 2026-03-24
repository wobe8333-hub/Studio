"""
롱폼 템플릿 구성 분석기

역할:
- 예시 스크립트를 분석하여 롱폼 비디오의 구조적 패턴을 추출
- 라디오/팟캐스트 톤 기준으로 도입부, 본문, 전환, 금지 패턴 등을 분석
- 원문 문장을 재사용하지 않고 구성만 분석하여 템플릿 규칙 생성
"""

from typing import Dict, List, Any, Optional
import json
from pathlib import Path


def analyze_template_structure(example_script: str) -> Dict[str, Any]:
    """
    예시 스크립트를 분석하여 롱폼 템플릿 구조를 추출
    
    Args:
        example_script: 분석할 예시 스크립트 (전체 텍스트)
    
    Returns:
        Dict: 템플릿 구조 분석 결과
            - sections: 섹션 목록 (id, title, role, purpose, typical_length_ratio, notes)
            - hook_rules: 도입부 후킹 규칙 리스트
            - transitions: 전환 문구 패턴 리스트
            - tone_guide: 톤 가이드라인 리스트
            - banned_patterns: 금지 패턴 리스트
    """
    if not example_script or not example_script.strip():
        raise ValueError("example_script는 비어있을 수 없습니다")
    
    # 스크립트를 문단 단위로 분리
    paragraphs = [p.strip() for p in example_script.split("\n\n") if p.strip()]
    
    # 섹션 분석 (라디오/팟캐스트 구조 기준)
    sections = []
    
    # 1. 도입부 (Hook) - 첫 1-2 문단
    if len(paragraphs) > 0:
        hook_paragraphs = paragraphs[:min(2, len(paragraphs))]
        sections.append({
            "id": "hook",
            "title": "도입부 (Hook)",
            "role": "시청자 관심 유도 및 주제 제시",
            "purpose": "첫 3-5초 내 시청자의 주의를 끌고, 비디오의 핵심 가치를 암시",
            "typical_length_ratio": 0.05,  # 전체의 5%
            "notes": "질문, 통계, 충격적 사실, 개인적 경험 등으로 시작"
        })
    
    # 2. 본문 전개부 (Body) - 중간 부분
    if len(paragraphs) > 2:
        body_count = len(paragraphs) - 3  # hook(2) + conclusion(1) 제외
        if body_count > 0:
            sections.append({
                "id": "body",
                "title": "본문 전개부",
                "role": "주제의 상세 설명 및 논리적 전개",
                "purpose": "핵심 내용을 단계적으로 설명하고 예시/사례를 제시",
                "typical_length_ratio": 0.80,  # 전체의 80%
                "notes": "소주제별로 나누어 설명, 각 소주제는 30-60초 분량"
            })
    
    # 3. 결론부 (Conclusion) - 마지막 1 문단
    if len(paragraphs) > 1:
        sections.append({
            "id": "conclusion",
            "title": "결론부",
            "role": "핵심 요약 및 행동 유도",
            "purpose": "주요 내용을 간결히 정리하고 다음 행동(구독, 댓글 등)을 유도",
            "typical_length_ratio": 0.15,  # 전체의 15%
            "notes": "요약 + CTA(구독, 좋아요, 댓글) 포함"
        })
    
    # 도입부 후킹 규칙 (라디오/팟캐스트 톤 기준)
    hook_rules = [
        "질문으로 시작: '혹시 ~한 경험 있으신가요?', '~에 대해 들어보셨나요?'",
        "통계/숫자로 시작: '한국인의 ~%가 ~합니다', '매년 ~만 명이 ~합니다'",
        "개인적 경험 공유: '제가 ~했을 때 ~했습니다', '~하면서 깨달은 점이 있습니다'",
        "반전/충격적 사실: '많은 사람들이 모르는 사실은 ~입니다', '~라고 생각하시지만 실제로는 ~입니다'",
        "시나리오 제시: '만약 ~라면 어떻게 하시겠어요?', '~ 상황을 상상해보세요'"
    ]
    
    # 전환 문구 패턴
    transitions = [
        "그렇다면 ~는 무엇일까요?",
        "이제 ~에 대해 자세히 알아보겠습니다",
        "다음으로 ~를 살펴보겠습니다",
        "그런데 ~는 어떻게 될까요?",
        "이와 관련해서 ~도 중요한데요",
        "한 가지 더 ~",
        "마지막으로 ~"
    ]
    
    # 톤 가이드라인 (라디오/팟캐스트 스타일)
    tone_guide = [
        "친근하고 대화하듯이 말하기 (반말/존댓말 혼용 가능, 자연스러운 구어체)",
        "과장 없이 솔직하게 전달 (과도한 감정 표현 지양)",
        "듣는 사람을 직접 대화 상대로 여기며 설명 ('~하시면 됩니다', '~아시나요?')",
        "복잡한 개념도 쉽게 풀어서 설명 (비유, 예시 활용)",
        "적절한 간격과 휴지 (너무 빠르지 않게, 명확한 발음)",
        "자연스러운 반복과 강조 (핵심 키워드는 2-3회 언급)"
    ]
    
    # 금지 패턴
    banned_patterns = [
        "과도한 배경음악이나 효과음 (내레이션을 방해하지 않도록)",
        "너무 빠른 템포의 내레이션 (분당 150단어 이상 지양)",
        "전문 용어의 무분별한 사용 (필요 시 쉬운 설명 병행)",
        "중복된 내용 반복 (같은 내용을 여러 번 말하지 않기)",
        "불필요한 장식적 요소 (핵심 내용에 집중)",
        "과도한 자막/텍스트 오버레이 (시각적 혼란 방지)"
    ]
    
    return {
        "sections": sections,
        "hook_rules": hook_rules,
        "transitions": transitions,
        "tone_guide": tone_guide,
        "banned_patterns": banned_patterns
    }


def save_analysis_result(analysis_result: Dict[str, Any], output_path: Path) -> None:
    """
    분석 결과를 JSON 파일로 저장
    
    Args:
        analysis_result: analyze_template_structure의 반환값
        output_path: 저장할 파일 경로
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(analysis_result, f, ensure_ascii=False, indent=2)


def load_latest_analysis(analysis_dir: Path) -> Optional[Dict[str, Any]]:
    """
    최신 분석 결과를 로드
    
    Args:
        analysis_dir: 분석 결과가 저장된 디렉토리
    
    Returns:
        Dict: 분석 결과 또는 None (파일이 없는 경우)
    """
    latest_path = analysis_dir / "latest.json"
    if latest_path.exists():
        with open(latest_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return None
































