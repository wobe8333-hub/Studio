"""
Scene Designer - 씬 구성 및 이미지 프롬프트 생성 모듈

역할:
- 스크립트를 바탕으로 각 장면의 시각적 구성을 설계
- 이미지 생성 AI를 위한 프롬프트 생성
- 장면 전환, 카메라 움직임, 시각적 스타일 결정
"""

from typing import Dict, List, Optional


def design_scenes(script: Dict, style: Optional[str] = "일러스트") -> List[Dict]:
    """
    스크립트를 바탕으로 각 장면의 시각적 구성을 설계
    
    Args:
        script: script_generator가 생성한 스크립트
        style: 시각적 스타일 ("일러스트", "3D", "실사", "만화" 등)
    
    Returns:
        List[Dict]: 장면 구성 리스트
            각 Dict는:
            - scene_number: 장면 번호
            - composition: 장면 구성 설명
            - camera_angle: 카메라 각도
            - transitions: 전환 효과
            - image_prompt: 이미지 생성 프롬프트
    """
    # TODO: 실제 씬 디자인 로직 구현
    return []


def generate_image_prompt(
    scene_description: str,
    style: str,
    mood: Optional[str] = None
) -> str:
    """
    장면 설명을 바탕으로 이미지 생성 AI용 프롬프트 생성
    
    Args:
        scene_description: 장면 설명
        style: 시각적 스타일
        mood: 분위기/톤 (선택사항)
    
    Returns:
        str: 최적화된 이미지 프롬프트
    """
    # TODO: 프롬프트 생성 로직 구현
    return ""


def plan_transitions(scenes: List[Dict]) -> List[Dict]:
    """
    장면들 간의 전환 효과를 계획
    
    Args:
        scenes: 장면 구성 리스트
    
    Returns:
        List[Dict]: 전환 계획 리스트
            각 Dict는:
            - from_scene: 시작 장면 번호
            - to_scene: 끝 장면 번호
            - transition_type: 전환 타입 ("페이드", "슬라이드", "줌" 등)
            - duration: 전환 길이 (초)
    """
    # TODO: 전환 계획 로직 구현
    return []


def optimize_for_animation(scenes: List[Dict]) -> List[Dict]:
    """
    애니메이션 제작에 최적화된 형태로 장면 구성 개선
    
    Args:
        scenes: 장면 구성 리스트
    
    Returns:
        List[Dict]: 최적화된 장면 구성 리스트
    """
    # TODO: 최적화 로직 구현
    return scenes


def generate_scenes_from_script(script: str) -> List[Dict]:
    """
    스크립트 텍스트를 분석하여 씬 구성 리스트를 생성 (더미 구현)
    
    Args:
        script: 스크립트 텍스트
    
    Returns:
        List[Dict]: 씬 구성 리스트
            각 Dict는:
            - scene_number: 씬 번호
            - description: 씬 설명
    """
    # 스크립트를 줄 단위로 분리
    lines = script.split('\n')
    
    scenes = []
    scene_number = 1
    current_description = ""
    
    # 스크립트에서 장면 정보 추출 (더미 로직)
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        # 장면 번호 패턴 감지 (예: "1장면:", "2장면:" 등)
        if '장면' in line or 'Scene' in line or line.startswith(str(scene_number)):
            if current_description:
                scenes.append({
                    "scene_number": scene_number,
                    "description": current_description.strip()
                })
                scene_number += 1
                current_description = ""
            
            # 장면 설명 추출
            if ':' in line:
                current_description = line.split(':', 1)[1].strip()
            else:
                current_description = line
        elif current_description:
            # 현재 장면 설명에 추가
            current_description += " " + line
        else:
            # 새로운 장면 시작
            if any(keyword in line for keyword in ['도입', '본문', '결론', 'Introduction', 'Body', 'Conclusion']):
                continue
            current_description = line
    
    # 마지막 장면 추가
    if current_description:
        scenes.append({
            "scene_number": scene_number,
            "description": current_description.strip()
        })
    
    # 더미 데이터가 비어있으면 기본 장면 생성
    if not scenes:
        scenes = [
            {
                "scene_number": 1,
                "description": "도입부: 주제 소개 및 개요 설명"
            },
            {
                "scene_number": 2,
                "description": "본문 1: 주요 개념 설명"
            },
            {
                "scene_number": 3,
                "description": "본문 2: 상세 내용 및 특징"
            },
            {
                "scene_number": 4,
                "description": "결론: 요약 및 마무리"
            }
        ]
    
    return scenes



