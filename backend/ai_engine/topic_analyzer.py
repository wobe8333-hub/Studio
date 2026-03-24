"""
Topic Analyzer - 주제/키워드 분석 모듈

역할:
- 사용자가 입력한 주제나 키워드를 분석
- 관련 개념, 난이도, 대상 연령 등을 파악
- 애니메이션 제작에 필요한 메타데이터 추출
"""

from typing import Dict, List, Optional


def analyze_topic(topic: str, keywords: Optional[List[str]] = None) -> Dict:
    """
    주제와 키워드를 분석하여 애니메이션 제작에 필요한 정보를 추출
    
    Args:
        topic: 분석할 주제 (예: "태양계", "프랑스 혁명")
        keywords: 추가 키워드 리스트 (선택사항)
    
    Returns:
        Dict: 분석 결과
            - main_concepts: 주요 개념 리스트
            - difficulty: 난이도 (초급/중급/고급)
            - target_age: 대상 연령
            - estimated_duration: 예상 애니메이션 길이
            - related_topics: 관련 주제들
    """
    # TODO: 실제 AI 분석 로직 구현
    return {
        "main_concepts": [],
        "difficulty": "중급",
        "target_age": "전체",
        "estimated_duration": 0,
        "related_topics": []
    }


def extract_key_concepts(topic: str) -> List[str]:
    """
    주제에서 핵심 개념들을 추출
    
    Args:
        topic: 분석할 주제
    
    Returns:
        List[str]: 핵심 개념 리스트
    """
    # TODO: 개념 추출 로직 구현
    return []


def determine_difficulty(topic: str, concepts: List[str]) -> str:
    """
    주제의 난이도를 판단
    
    Args:
        topic: 주제
        concepts: 관련 개념들
    
    Returns:
        str: 난이도 ("초급", "중급", "고급")
    """
    # TODO: 난이도 판단 로직 구현
    return "중급"







































