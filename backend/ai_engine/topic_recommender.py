"""
Topic Recommender - 주제 추천 엔진

역할:
- 학습된 concepts를 기반으로 영상 주제 추천 생성
- 빈도 분석을 통한 인기 개념 파악
"""

from typing import List, Dict
from collections import Counter
import random

# 메타 개념 필터링 리스트 (제외할 개념들)
META_CONCEPTS = {
    "주요 개념",
    "핵심 내용",
    "중요 사항",
    "개요",
    "요약",
    "결론",
    "기본 개념 1",
    "기본 개념 2"
}

# 질문형 제목 템플릿
QUESTION_TEMPLATES = [
    "{concept}은 왜 중요한 개념일까?",
    "{concept}은 우리에게 어떤 영향을 미칠까?",
    "{concept}은 어떻게 작동할까?",
    "{concept}에 대해 알아보자",
    "{concept}의 비밀은 무엇일까?"
]


def is_valid_concept(concept: str) -> bool:
    """
    개념이 실제 의미 있는 개념인지 확인
    
    Args:
        concept: 확인할 개념
    
    Returns:
        bool: 유효한 개념이면 True
    """
    # 메타 개념 제외
    if concept in META_CONCEPTS:
        return False
    
    # 너무 짧은 개념 제외 (2자 이하)
    if len(concept) <= 2:
        return False
    
    # 메타 개념이 포함된 경우 제외
    for meta in META_CONCEPTS:
        if meta in concept:
            return False
    
    return True


def convert_to_question_title(concept: str) -> str:
    """
    개념을 질문형 영상 제목으로 변환
    
    Args:
        concept: 개념
    
    Returns:
        str: 질문형 제목
    """
    template = random.choice(QUESTION_TEMPLATES)
    return template.format(concept=concept)


def recommend_topics(concepts: List[str], limit: int = 5) -> List[Dict]:
    """
    concepts 빈도를 분석하여 주제 추천 생성
    
    Args:
        concepts: 개념 리스트 (중복 포함 가능)
        limit: 추천할 주제 수
    
    Returns:
        List[Dict]: 추천 주제 리스트
            각 Dict는:
            - title: 추천 주제 제목
            - reason: 추천 이유
    """
    if not concepts:
        # concepts가 없으면 기본 추천 주제 반환
        default_concepts = ["태양계", "인공지능", "프랑스 혁명", "블랙홀", "중력"]
        return [
            {
                "title": convert_to_question_title(concept),
                "reason": "학습 데이터가 없어 기본 추천 주제입니다."
            }
            for concept in default_concepts[:limit]
        ]
    
    # concepts 빈도 계산
    concept_counts = Counter(concepts)
    
    # 유효한 개념만 필터링
    valid_concepts = [
        (concept, count) 
        for concept, count in concept_counts.items() 
        if is_valid_concept(concept)
    ]
    
    if not valid_concepts:
        # 유효한 개념이 없으면 기본 추천 주제 반환
        default_concepts = ["태양계", "인공지능", "프랑스 혁명", "블랙홀", "중력"]
        return [
            {
                "title": convert_to_question_title(concept),
                "reason": "학습 데이터에 유효한 개념이 없어 기본 추천 주제입니다."
            }
            for concept in default_concepts[:limit]
        ]
    
    # 빈도순으로 정렬
    valid_concepts.sort(key=lambda x: x[1], reverse=True)
    
    # 상위 개념 추출 (빈도순)
    top_concepts = valid_concepts[:limit * 2]  # 여유있게 추출
    
    recommendations = []
    
    # 상위 개념을 기반으로 주제 추천 생성
    for concept, count in top_concepts:
        # 질문형 제목 생성
        title = convert_to_question_title(concept)
        
        # 추천 이유 생성
        reason = f"최근 학습 로그에서 '{concept}' 개념이 {count}회 등장했습니다."
        
        recommendations.append({
            "title": title,
            "reason": reason
        })
        
        if len(recommendations) >= limit:
            break
    
    # 추천 주제가 부족하면 기본 주제 추가
    default_concepts = [
        "태양계",
        "인공지능",
        "프랑스 혁명",
        "블랙홀",
        "중력",
        "DNA와 유전",
        "기후 변화",
        "사건의 지평선"
    ]
    
    # 이미 사용된 개념 추출 (reason에서)
    used_concepts = set()
    for rec in recommendations:
        # reason에서 개념 추출 (간단한 파싱)
        reason = rec["reason"]
        if "최근 학습 로그에서" in reason:
            # "'{concept}' 개념이" 패턴에서 개념 추출
            start = reason.find("'") + 1
            end = reason.find("'", start)
            if start > 0 and end > start:
                used_concepts.add(reason[start:end])
    
    while len(recommendations) < limit:
        for default_concept in default_concepts:
            if len(recommendations) >= limit:
                break
            # 이미 사용된 개념이 아니면 추가
            if default_concept not in used_concepts:
                recommendations.append({
                    "title": convert_to_question_title(default_concept),
                    "reason": "학습 데이터가 부족하여 기본 추천 주제입니다."
                })
                used_concepts.add(default_concept)
    
    return recommendations[:limit]

