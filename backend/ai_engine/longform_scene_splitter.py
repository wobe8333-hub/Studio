"""
롱폼 스크립트 → 씬 자동 분해 로직

역할:
- 전체 스크립트를 씬 단위로 자동 분해
- 씬 길이 기본 8초 (6~12초 가변)
- 초반 2~3씬은 hook_rules 반영
- narration(한국어)와 shot_prompt_en(영어) 자동 생성
"""

from typing import List, Dict, Any, Optional
import json
from pathlib import Path
import uuid

from backend.schemas.longform_scene_v1 import SceneV1, VideoPlanV1, ChapterV1


def split_script_to_scenes(
    full_script: str,
    video_plan: VideoPlanV1,
    hook_rules: Optional[List[str]] = None,
    style_profile: Optional[Dict[str, Any]] = None
) -> VideoPlanV1:
    """
    전체 스크립트를 씬 단위로 분해하여 VideoPlanV1을 업데이트
    
    Args:
        full_script: 전체 내레이션 스크립트
        video_plan: 기존 VideoPlanV1 객체 (scenes는 비어있을 수 있음)
        hook_rules: 도입부 후킹 규칙 리스트 (선택)
        style_profile: 스타일 프로필 설정 (선택)
    
    Returns:
        VideoPlanV1: 씬이 추가된 업데이트된 VideoPlanV1
    """
    if not full_script or not full_script.strip():
        raise ValueError("full_script는 비어있을 수 없습니다")
    
    # 스크립트를 문장 단위로 분리 (마침표, 느낌표, 물음표 기준)
    import re
    sentences = re.split(r'[.!?]\s+', full_script.strip())
    sentences = [s.strip() for s in sentences if s.strip()]
    
    if not sentences:
        raise ValueError("분해할 문장이 없습니다")
    
    # 기본 씬 길이 설정 (초)
    default_scene_duration = 8  # 기본 8초
    min_scene_duration = 6
    max_scene_duration = 12
    
    # 스타일 프로필에서 shot_prompt 접두사/접미사 추출
    shot_prefix = ""
    shot_suffix = ""
    if style_profile:
        shot_config = style_profile.get("shot_style", {})
        shot_prefix = style_profile.get("shot_prompt_prefix", "")
        shot_suffix = style_profile.get("shot_prompt_suffix", "")
    
    scenes: List[SceneV1] = []
    current_order = 1
    
    # 초반 2~3씬은 hook_rules 반영 (더 짧게, 더 강렬하게)
    hook_scene_count = min(3, len(sentences))
    
    for i, sentence in enumerate(sentences):
        # 씬 길이 결정
        if i < hook_scene_count:
            # 초반 씬: 6-8초 (더 빠른 템포)
            duration = min(max_scene_duration, max(min_scene_duration, default_scene_duration - 2))
        else:
            # 일반 씬: 8초 (기본값)
            duration = default_scene_duration
        
        # 씬 ID 생성
        scene_id = f"scene_{current_order:03d}"
        
        # narration (한국어) - 원문 문장 사용
        narration = sentence
        
        # shot_prompt_en (영어) - 간단한 번역/요약 기반 생성
        # 실제로는 번역 API를 사용하거나 더 정교한 로직이 필요하지만,
        # 여기서는 기본적인 키워드 추출 방식 사용
        shot_prompt_en = _generate_shot_prompt(sentence, shot_prefix, shot_suffix)
        
        # overlay_text는 선택적으로 핵심 키워드만 추출
        overlay_text = _extract_keywords(sentence, max_words=5)
        
        scene = SceneV1(
            scene_id=scene_id,
            order=current_order,
            narration=narration,
            shot_prompt_en=shot_prompt_en,
            image_asset=None,
            duration_sec=duration,
            overlay_text=overlay_text if overlay_text else None,
            bgm=None,
            status="pending"
        )
        
        scenes.append(scene)
        current_order += 1
    
    # 씬 수가 너무 적으면 자동 분할 (긴 문장을 여러 씬으로)
    if len(scenes) < 5:
        scenes = _split_long_sentences(scenes, default_scene_duration, shot_prefix, shot_suffix)
    
    # VideoPlanV1 업데이트
    video_plan.scenes = scenes
    video_plan.narration_script = full_script
    
    # 챕터 자동 생성 (씬이 10개 이상이면 3개씩 묶어서 챕터 생성)
    if len(scenes) >= 10:
        chapters = []
        chapter_scene_count = max(3, len(scenes) // 3)
        accumulated_sec = 0
        
        for chapter_idx in range(0, len(scenes), chapter_scene_count):
            chapter_scenes = scenes[chapter_idx:chapter_idx + chapter_scene_count]
            if chapter_scenes:
                chapter_title = f"Part {len(chapters) + 1}"
                chapters.append({
                    "title": chapter_title,
                    "start_sec": accumulated_sec
                })
                accumulated_sec += sum(s.duration_sec for s in chapter_scenes)
        
        video_plan.chapters = [ChapterV1(**ch) for ch in chapters]
    
    return video_plan


def _generate_shot_prompt(sentence: str, prefix: str = "", suffix: str = "") -> str:
    """
    한국어 문장에서 영어 shot_prompt 생성
    
    Args:
        sentence: 한국어 문장
        prefix: 스타일 프로필의 shot_prompt_prefix
        suffix: 스타일 프로필의 shot_prompt_suffix
    
    Returns:
        str: 영어 shot_prompt
    """
    # 간단한 키워드 추출 (실제로는 더 정교한 번역/추출 로직 필요)
    # 여기서는 기본적인 패턴 매칭으로 처리
    
    # 일반적인 키워드 매핑 (예시)
    keyword_map = {
        "사람": "person",
        "장면": "scene",
        "배경": "background",
        "도시": "city",
        "자연": "nature",
        "건물": "building",
        "풍경": "landscape",
        "실내": "indoor",
        "실외": "outdoor"
    }
    
    # 문장에서 키워드 추출 (간단한 방식)
    prompt_parts = []
    for kor, eng in keyword_map.items():
        if kor in sentence:
            prompt_parts.append(eng)
    
    # 기본 프롬프트
    if not prompt_parts:
        prompt_parts = ["informative", "calm", "professional"]
    
    base_prompt = ", ".join(prompt_parts[:3])  # 최대 3개 키워드
    
    # 접두사/접미사 추가
    result = base_prompt
    if prefix:
        result = prefix + result
    if suffix:
        result = result + suffix
    
    return result


def _extract_keywords(sentence: str, max_words: int = 5) -> Optional[str]:
    """
    문장에서 핵심 키워드 추출 (오버레이 텍스트용)
    
    Args:
        sentence: 한국어 문장
        max_words: 최대 단어 수
    
    Returns:
        Optional[str]: 추출된 키워드 또는 None
    """
    # 간단한 방식: 명사/핵심 단어 추출 (실제로는 형태소 분석 필요)
    # 여기서는 공백 기준으로 단어 분리 후 짧은 조사/접속사 제거
    words = sentence.split()
    
    # 조사/접속사 제거 (간단한 필터)
    stopwords = ["은", "는", "이", "가", "을", "를", "의", "와", "과", "도", "만", "에서", "에게", "로", "으로"]
    keywords = [w for w in words if w not in stopwords and len(w) > 1]
    
    if keywords:
        return " ".join(keywords[:max_words])
    return None


def _split_long_sentences(
    scenes: List[SceneV1],
    default_duration: int,
    shot_prefix: str,
    shot_suffix: str
) -> List[SceneV1]:
    """
    긴 문장을 여러 씬으로 분할
    
    Args:
        scenes: 기존 씬 리스트
        default_duration: 기본 씬 길이
        shot_prefix: shot_prompt 접두사
        shot_suffix: shot_prompt 접미사
    
    Returns:
        List[SceneV1]: 분할된 씬 리스트
    """
    new_scenes: List[SceneV1] = []
    
    for scene in scenes:
        # 문장이 너무 길면 (50자 이상) 분할
        if len(scene.narration) > 50:
            # 쉼표나 연결어 기준으로 분할
            parts = scene.narration.split(", ")
            if len(parts) > 1:
                # 여러 부분으로 나누기
                for idx, part in enumerate(parts):
                    if part.strip():
                        new_scene = SceneV1(
                            scene_id=f"{scene.scene_id}_part{idx + 1}",
                            order=scene.order + idx,
                            narration=part.strip(),
                            shot_prompt_en=_generate_shot_prompt(part, shot_prefix, shot_suffix),
                            image_asset=scene.image_asset,
                            duration_sec=default_duration,
                            overlay_text=_extract_keywords(part),
                            bgm=scene.bgm,
                            status=scene.status
                        )
                        new_scenes.append(new_scene)
            else:
                new_scenes.append(scene)
        else:
            new_scenes.append(scene)
    
    # order 재정렬
    for idx, scene in enumerate(new_scenes, start=1):
        scene.order = idx
        scene.scene_id = f"scene_{idx:03d}"
    
    return new_scenes


def load_style_profile(profile_id: str) -> Optional[Dict[str, Any]]:
    """
    스타일 프로필 로드
    
    Args:
        profile_id: 프로필 ID (예: "longform-default")
    
    Returns:
        Optional[Dict[str, Any]]: 스타일 프로필 또는 None
    """
    profile_path = Path(__file__).resolve().parent.parent / "configs" / "style_profiles" / f"{profile_id}.json"
    
    if profile_path.exists():
        with open(profile_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return None


def save_video_plan(video_plan: VideoPlanV1, output_path: Path) -> None:
    """
    VideoPlanV1을 JSON 파일로 저장
    
    Args:
        video_plan: 저장할 VideoPlanV1 객체
        output_path: 저장할 파일 경로
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(video_plan.model_dump(), f, ensure_ascii=False, indent=2)


def load_video_plan(plan_path: Path) -> Optional[VideoPlanV1]:
    """
    VideoPlanV1을 JSON 파일에서 로드
    
    Args:
        plan_path: 로드할 파일 경로
    
    Returns:
        Optional[VideoPlanV1]: VideoPlanV1 객체 또는 None
    """
    if plan_path.exists():
        with open(plan_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return VideoPlanV1(**data)
    return None








