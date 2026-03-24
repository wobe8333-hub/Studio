"""
유튜브 메타데이터 자동 생성 모듈

기능:
- 롱폼 영상 기반 유튜브 업로드 메타데이터 생성
- title, description, chapters_text, tags 생성
"""

from typing import List, Dict, Optional, Any, Tuple
from pathlib import Path
from backend.schemas.longform_scene_v1 import VideoPlanV1, SceneV1, ChapterV1


def format_time_mmss(seconds: int) -> str:
    """
    초를 MM:SS 형식으로 변환
    
    Args:
        seconds: 초 단위 시간
    
    Returns:
        str: MM:SS 형식 문자열
    """
    minutes = seconds // 60
    secs = seconds % 60
    return f"{minutes:02d}:{secs:02d}"


def calculate_chapter_timeline(
    scenes: List[SceneV1],
    chapters: Optional[List[ChapterV1]] = None
) -> List[Dict[str, Any]]:
    """
    챕터 타임라인 계산
    
    Args:
        scenes: 씬 리스트 (order 기준 정렬 필요)
        chapters: 챕터 리스트 (있으면 우선 사용)
    
    Returns:
        List[Dict]: 챕터 타임라인 리스트
            - time: "MM:SS" 형식
            - title: 챕터 제목
            - start_sec: 시작 시간 (초)
    """
    # 씬을 order 기준으로 정렬
    sorted_scenes = sorted(scenes, key=lambda s: s.order)
    
    # 빈 narration 씬 제외
    valid_scenes = [s for s in sorted_scenes if s.narration and s.narration.strip()]
    
    if not valid_scenes:
        return []
    
    # chapters가 존재하면 우선 사용
    if chapters and len(chapters) > 0:
        timeline = []
        for chapter in chapters:
            timeline.append({
                "time": format_time_mmss(chapter.start_sec),
                "title": chapter.title,
                "start_sec": chapter.start_sec
            })
        return timeline
    
    # chapters가 없으면 narration 내용 기반으로 자동 묶음
    timeline = []
    accumulated_sec = 0
    min_chapter_duration = 30  # 최소 챕터 길이 30초
    
    current_chapter_start = 0
    current_chapter_scenes = []
    
    for scene in valid_scenes:
        current_chapter_scenes.append(scene)
        accumulated_sec += scene.duration_sec
        
        # 최소 챕터 길이 이상이면 챕터 생성
        if accumulated_sec - current_chapter_start >= min_chapter_duration:
            # 챕터 제목 생성 (첫 씬의 narration에서 핵심 키워드 추출)
            first_scene_narration = current_chapter_scenes[0].narration
            chapter_title = _extract_chapter_title(first_scene_narration)
            
            timeline.append({
                "time": format_time_mmss(current_chapter_start),
                "title": chapter_title,
                "start_sec": current_chapter_start
            })
            
            current_chapter_start = accumulated_sec
            current_chapter_scenes = []
    
    # 마지막 챕터 처리 (남은 씬이 있으면)
    if current_chapter_scenes:
        first_scene_narration = current_chapter_scenes[0].narration
        chapter_title = _extract_chapter_title(first_scene_narration)
        
        timeline.append({
            "time": format_time_mmss(current_chapter_start),
            "title": chapter_title,
            "start_sec": current_chapter_start
        })
    
    # 타임라인이 비어있으면 전체를 하나의 챕터로
    if not timeline:
        timeline.append({
            "time": "00:00",
            "title": _extract_chapter_title(valid_scenes[0].narration) if valid_scenes else "본문",
            "start_sec": 0
        })
    
    # 첫 챕터는 항상 00:00 인트로
    if timeline and timeline[0]["start_sec"] > 0:
        timeline.insert(0, {
            "time": "00:00",
            "title": "인트로",
            "start_sec": 0
        })
    elif not timeline:
        timeline.append({
            "time": "00:00",
            "title": "인트로",
            "start_sec": 0
        })
    
    return timeline


def _extract_chapter_title(narration: str, max_length: int = 30) -> str:
    """
    narration에서 챕터 제목 추출
    
    Args:
        narration: 내레이션 텍스트
        max_length: 최대 길이
    
    Returns:
        str: 챕터 제목
    """
    if not narration:
        return "내용"
    
    # 문장 부호 제거 및 정리
    cleaned = narration.strip()
    
    # 첫 문장 추출 (마침표, 느낌표, 물음표 기준)
    import re
    match = re.match(r'^[^.!?]+', cleaned)
    if match:
        title = match.group(0).strip()
    else:
        title = cleaned
    
    # 길이 제한
    if len(title) > max_length:
        title = title[:max_length].rstrip() + "..."
    
    return title if title else "내용"


def generate_youtube_title(topic: str, scenes: List[SceneV1]) -> str:
    """
    유튜브 제목 생성 (후킹형)
    
    Args:
        topic: 주제
        scenes: 씬 리스트
    
    Returns:
        str: 유튜브 제목
    """
    # 후킹형 문장 패턴
    hook_patterns = [
        f"{topic}에 대해 알아야 할 모든 것",
        f"{topic}의 비밀을 밝힌다",
        f"{topic}에 숨겨진 진실",
        f"{topic}을 제대로 이해하는 방법",
        f"{topic}에 대한 놀라운 사실들"
    ]
    
    # 첫 번째 씬의 narration에서 힌트 추출
    sorted_scenes = sorted(scenes, key=lambda s: s.order)
    if sorted_scenes and sorted_scenes[0].narration:
        first_narration = sorted_scenes[0].narration
        # 질문형이면 질문 활용
        if "?" in first_narration:
            question = first_narration.split("?")[0].strip()
            if len(question) < 50:
                return f"{question}? {topic} 완전 정리"
    
    # 기본 패턴 사용
    return hook_patterns[0]


def generate_youtube_description(
    topic: str,
    scenes: List[SceneV1],
    chapters: Optional[List[ChapterV1]] = None
) -> str:
    """
    유튜브 설명 생성 (3단 구성)
    
    Args:
        topic: 주제
        scenes: 씬 리스트
        chapters: 챕터 리스트
    
    Returns:
        str: 유튜브 설명
    """
    sorted_scenes = sorted(scenes, key=lambda s: s.order)
    valid_scenes = [s for s in sorted_scenes if s.narration and s.narration.strip()]
    
    # 1) 도입 요약 (시청 이유 제시)
    intro = f"이 영상에서는 {topic}에 대해 자세히 알아봅니다. "
    
    if valid_scenes:
        first_narration = valid_scenes[0].narration[:100]
        intro += f"{first_narration}... "
    
    intro += "궁금하셨다면 끝까지 시청해주세요.\n\n"
    
    # 2) 본문 요약 (무엇을 알게 되는지)
    body = "이 영상에서 다루는 내용:\n"
    
    # 챕터가 있으면 챕터 기반, 없으면 씬 기반
    if chapters and len(chapters) > 0:
        for i, chapter in enumerate(chapters[:5], 1):  # 최대 5개
            body += f"• {chapter.title}\n"
    else:
        # 씬 기반 요약 (최대 5개)
        for i, scene in enumerate(valid_scenes[:5], 1):
            scene_summary = scene.narration[:50].strip()
            if scene_summary:
                body += f"• {scene_summary}...\n"
    
    body += "\n"
    
    # 3) 마무리 (구독/다음 영상 유도, 과도한 마케팅 금지)
    outro = "도움이 되셨다면 구독과 좋아요 부탁드립니다.\n"
    outro += "다음 영상도 기대해주세요!\n\n"
    outro += f"#{topic.replace(' ', '')}"
    
    return intro + body + outro


def generate_chapters_text(chapter_timeline: List[Dict[str, Any]]) -> str:
    """
    챕터 텍스트 생성 (유튜브 설명에 붙여넣기용)
    
    Args:
        chapter_timeline: 챕터 타임라인 리스트
    
    Returns:
        str: 챕터 텍스트 (줄바꿈 포함)
    """
    if not chapter_timeline:
        return ""
    
    lines = []
    for chapter in chapter_timeline:
        lines.append(f"{chapter['time']} {chapter['title']}")
    
    return "\n".join(lines)


def generate_tags(topic: str, scenes: List[SceneV1]) -> List[str]:
    """
    유튜브 태그 생성 (10~15개)
    
    Args:
        topic: 주제
        scenes: 씬 리스트
    
    Returns:
        List[str]: 태그 리스트
    """
    tags = set()
    
    # topic 기반 핵심 키워드
    topic_words = topic.split()
    for word in topic_words:
        if len(word) > 1:
            tags.add(word)
            tags.add(f"{word}강의")
            tags.add(f"{word}정리")
    
    # narration에서 키워드 추출
    sorted_scenes = sorted(scenes, key=lambda s: s.order)
    valid_scenes = [s for s in sorted_scenes if s.narration and s.narration.strip()]
    
    # 주요 명사 추출 (간단한 방식)
    import re
    for scene in valid_scenes[:10]:  # 최대 10개 씬만
        narration = scene.narration
        # 2-4자 한글 단어 추출
        words = re.findall(r'[가-힣]{2,4}', narration)
        for word in words[:3]:  # 씬당 최대 3개
            if len(word) >= 2:
                tags.add(word)
    
    # 일반 태그 추가
    tags.add("교육")
    tags.add("강의")
    tags.add("정리")
    tags.add("롱폼")
    tags.add("정보")
    
    # 중복 제거 및 정렬
    tag_list = sorted(list(tags))
    
    # 10~15개로 제한
    if len(tag_list) > 15:
        tag_list = tag_list[:15]
    elif len(tag_list) < 10:
        # 부족하면 topic 기반 추가
        while len(tag_list) < 10 and len(tag_list) < 20:
            tag_list.append(f"{topic}관련")
            if len(tag_list) >= 10:
                break
    
    return tag_list[:15]


def generate_youtube_metadata(
    video_plan: VideoPlanV1
) -> Dict[str, Any]:
    """
    유튜브 메타데이터 생성 (전체)
    
    Args:
        video_plan: VideoPlanV1 객체
    
    Returns:
        Dict: 유튜브 메타데이터
            - video_id
            - title
            - description
            - chapters (타임라인 리스트)
            - chapters_text (붙여넣기용 텍스트)
            - tags
    """
    # 챕터 타임라인 계산
    chapter_timeline = calculate_chapter_timeline(
        video_plan.scenes,
        video_plan.chapters if video_plan.chapters else None
    )
    
    # 제목 생성
    title = generate_youtube_title(video_plan.topic, video_plan.scenes)
    
    # 설명 생성
    description = generate_youtube_description(
        video_plan.topic,
        video_plan.scenes,
        video_plan.chapters if video_plan.chapters else None
    )
    
    # 챕터 텍스트 생성
    chapters_text = generate_chapters_text(chapter_timeline)
    
    # 태그 생성
    tags = generate_tags(video_plan.topic, video_plan.scenes)
    
    return {
        "video_id": video_plan.video_id,
        "title": title,
        "description": description,
        "chapters": chapter_timeline,
        "chapters_text": chapters_text,
        "tags": tags
    }








