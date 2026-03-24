"""
롱폼 스크립트 구조화 파서

기능:
- 롱폼 대본 문자열을 구조화된 데이터로 변환
- 도입부/본문/전환부/결론 구조 유지
- 문장 단위 또는 의미 단락 단위로 분해
"""

import re
from typing import List, Dict, Any, Optional
from datetime import datetime


def parse_longform_script(script: str) -> Dict[str, Any]:
    """
    롱폼 스크립트를 구조화된 데이터로 변환
    
    Args:
        script: 롱폼 대본 문자열
    
    Returns:
        Dict: 구조화된 데이터
            - original_script: 원본 스크립트
            - sentences: 문장 단위 분해 결과
            - scenes: 씬 구조 (scene_index, text, type, length)
            - structure: 도입부/본문/전환부/결론 구조
    """
    if not script or not script.strip():
        return {
            "original_script": "",
            "sentences": [],
            "scenes": [],
            "structure": {
                "intro": [],
                "body": [],
                "transitions": [],
                "conclusion": []
            }
        }
    
    # 문장 단위 분해 (마침표, 느낌표, 물음표 기준)
    sentences = _split_into_sentences(script)
    
    # 의미 단락 단위 분해 (빈 줄 기준)
    paragraphs = _split_into_paragraphs(script)
    
    # 씬 구조 생성
    scenes = _create_scene_structure(sentences, paragraphs)
    
    # 구조 분석 (도입부/본문/전환부/결론)
    structure = _analyze_structure(sentences, paragraphs)
    
    return {
        "original_script": script,
        "sentences": sentences,
        "paragraphs": paragraphs,
        "scenes": scenes,
        "structure": structure
    }


def _split_into_sentences(text: str) -> List[Dict[str, Any]]:
    """
    텍스트를 문장 단위로 분해
    
    Returns:
        List[Dict]: 문장 리스트
            - index: 문장 인덱스 (0부터 시작)
            - text: 문장 텍스트
            - length: 문자 수
    """
    # 문장 구분자: 마침표, 느낌표, 물음표
    pattern = r'([.!?])\s+'
    parts = re.split(pattern, text.strip())
    
    sentences = []
    current_sentence = ""
    
    for i, part in enumerate(parts):
        if part in ['.', '!', '?']:
            current_sentence += part
            if current_sentence.strip():
                sentences.append({
                    "index": len(sentences),
                    "text": current_sentence.strip(),
                    "length": len(current_sentence.strip())
                })
            current_sentence = ""
        else:
            current_sentence += part
    
    # 마지막 문장 처리
    if current_sentence.strip():
        sentences.append({
            "index": len(sentences),
            "text": current_sentence.strip(),
            "length": len(current_sentence.strip())
        })
    
    return sentences


def _split_into_paragraphs(text: str) -> List[Dict[str, Any]]:
    """
    텍스트를 의미 단락 단위로 분해 (빈 줄 기준)
    
    Returns:
        List[Dict]: 단락 리스트
            - index: 단락 인덱스
            - text: 단락 텍스트
            - length: 문자 수
            - sentence_count: 포함된 문장 수
    """
    paragraphs_raw = text.split('\n\n')
    
    paragraphs = []
    for idx, para_text in enumerate(paragraphs_raw):
        para_text = para_text.strip()
        if para_text:
            # 문장 수 계산
            sentence_count = len(re.findall(r'[.!?]\s+', para_text)) + 1
            
            paragraphs.append({
                "index": idx,
                "text": para_text,
                "length": len(para_text),
                "sentence_count": sentence_count
            })
    
    return paragraphs


def _create_scene_structure(
    sentences: List[Dict[str, Any]],
    paragraphs: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    씬 구조 생성
    
    Returns:
        List[Dict]: 씬 리스트
            - scene_index: 씬 인덱스 (1부터 시작)
            - text: 씬 텍스트
            - type: 씬 타입 (intro/body/transition/conclusion)
            - length: 문자 수
            - sentence_indices: 포함된 문장 인덱스 리스트
    """
    scenes = []
    
    # 단락을 씬으로 사용 (의미 단위)
    for para in paragraphs:
        scene_index = len(scenes) + 1
        
        # 씬 타입 결정 (간단한 휴리스틱)
        scene_type = _determine_scene_type(para, scene_index, len(paragraphs))
        
        # 포함된 문장 인덱스 찾기
        sentence_indices = []
        para_text = para["text"]
        for sent in sentences:
            if sent["text"] in para_text or para_text.startswith(sent["text"][:20]):
                sentence_indices.append(sent["index"])
        
        # source_index_range 계산 (문장 인덱스 범위)
        source_index_range = None
        if sentence_indices:
            source_index_range = {
                "start": min(sentence_indices),
                "end": max(sentence_indices)
            }
        
        # visual_prompt 생성 (이미지/합성용 프롬프트)
        visual_prompt = _generate_visual_prompt(para["text"], scene_type)
        
        scenes.append({
            "scene_index": scene_index,
            "narration": para["text"],  # 대사
            "text": para["text"],  # 하위 호환성
            "type": scene_type,
            "approx_chars": para["length"],
            "source_index_range": source_index_range,
            "sentence_count": para["sentence_count"],
            "sentence_indices": sentence_indices,  # 하위 호환성 유지
            "visual_prompt": visual_prompt,  # 이미지/합성용 프롬프트
            "duration_sec": max(6, min(12, para["length"] // 20))  # 대략적인 duration (문자 수 기반)
        })
    
    return scenes


def _determine_scene_type(
    paragraph: Dict[str, Any],
    scene_index: int,
    total_scenes: int
) -> str:
    """
    씬 타입 결정 (도입부/본문/전환부/결론)
    
    Returns:
        str: 씬 타입 (intro/body/transition/conclusion)
    """
    text = paragraph["text"].lower()
    
    # 도입부: 첫 1-2개 씬
    if scene_index <= 2:
        return "intro"
    
    # 결론부: 마지막 1개 씬
    if scene_index == total_scenes:
        return "conclusion"
    
    # 전환부: 전환 문구 포함
    transition_keywords = [
        "다음으로", "이제", "그렇다면", "그런데", "한 가지 더", "마지막으로"
    ]
    for keyword in transition_keywords:
        if keyword in text:
            return "transition"
    
    # 본문: 나머지
    return "body"


def _analyze_structure(
    sentences: List[Dict[str, Any]],
    paragraphs: List[Dict[str, Any]]
) -> Dict[str, List[Dict[str, Any]]]:
    """
    구조 분석 (도입부/본문/전환부/결론)
    
    Returns:
        Dict: 구조 정보
    """
    scenes = _create_scene_structure(sentences, paragraphs)
    
    structure = {
        "intro": [],
        "body": [],
        "transitions": [],
        "conclusion": []
    }
    
    for scene in scenes:
        scene_type = scene["type"]
        if scene_type == "intro":
            structure["intro"].append(scene)
        elif scene_type == "body":
            structure["body"].append(scene)
        elif scene_type == "transition":
            structure["transitions"].append(scene)
        elif scene_type == "conclusion":
            structure["conclusion"].append(scene)
    
    return structure


def _generate_visual_prompt(text: str, scene_type: str) -> str:
    """
    visual_prompt 생성 (이미지/합성용 프롬프트)
    
    Args:
        text: 씬 텍스트
        scene_type: 씬 타입
    
    Returns:
        str: 영어 프롬프트
    """
    # 기본 프롬프트
    base_prompt = "cinematic, professional, calm, informative"
    
    # 씬 타입에 따른 스타일 추가
    style_map = {
        "intro": "engaging, attention-grabbing, warm lighting",
        "body": "educational, clear, balanced composition",
        "transition": "smooth, connecting, subtle movement",
        "conclusion": "summary, memorable, soft lighting"
    }
    
    style = style_map.get(scene_type, "professional, clear")
    
    # 텍스트에서 키워드 추출 (간단한 방식)
    keywords = []
    # 한글 키워드를 영어로 매핑 (간단한 예시)
    keyword_map = {
        "블랙홀": "black hole",
        "우주": "space",
        "지구": "earth",
        "인공지능": "artificial intelligence",
        "기후변화": "climate change"
    }
    
    for kor, eng in keyword_map.items():
        if kor in text:
            keywords.append(eng)
    
    # 프롬프트 조합
    prompt_parts = [base_prompt, style]
    if keywords:
        prompt_parts.extend(keywords[:3])  # 최대 3개 키워드
    
    prompt_parts.append("high quality, detailed, 4k")
    
    return ", ".join(prompt_parts)
































