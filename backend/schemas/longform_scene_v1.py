"""
롱폼 비디오 Scene JSON 스펙 v1

정의:
- ChapterV1: 챕터 정보
- SceneV1: 개별 씬 정보
- VideoPlanV1: 전체 비디오 플랜
"""

from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field


class ChapterV1(BaseModel):
    """챕터 정보"""
    title: str = Field(..., description="챕터 제목")
    start_sec: int = Field(..., description="챕터 시작 시간 (초)")


class SceneV1(BaseModel):
    """개별 씬 정보"""
    scene_id: str = Field(..., description="씬 고유 ID (예: scene_001)")
    order: int = Field(..., description="씬 순서 (1부터 시작)")
    narration: str = Field(..., description="내레이션 텍스트 (한국어)")
    shot_prompt_en: str = Field(..., description="이미지 생성 프롬프트 (영어)")
    image_asset: Optional[str] = Field(None, description="사용할 이미지 에셋 경로 (선택)")
    duration_sec: int = Field(..., description="씬 지속 시간 (초)", ge=1, le=60)
    overlay_text: Optional[str] = Field(None, description="오버레이 텍스트 (선택)")
    bgm: Optional[str] = Field(None, description="BGM 파일명 또는 ID (선택)")
    status: str = Field("pending", description="씬 상태: pending/rendering/done/failed")
    # 렌더 상태 관리 필드 (추가)
    render_status: str = Field("PENDING", description="렌더 상태: PENDING/RUNNING/DONE/FAILED/SKIPPED")
    render_attempts: int = Field(0, description="렌더 시도 횟수")
    last_error: Optional[str] = Field(None, description="마지막 에러 메시지")
    output_video_path: Optional[str] = Field(None, description="씬 렌더 결과 비디오 경로")


class VideoPlanV1(BaseModel):
    """롱폼 비디오 플랜"""
    video_id: str = Field(..., description="비디오 고유 ID")
    topic: str = Field(..., description="비디오 주제")
    style_profile_id: str = Field(..., description="스타일 프로필 ID (예: longform-default)")
    narration_script: str = Field(..., description="전체 내레이션 스크립트")
    scenes: List[SceneV1] = Field(default_factory=list, description="씬 리스트")
    chapters: List[ChapterV1] = Field(default_factory=list, description="챕터 리스트")
    meta: Dict[str, Any] = Field(default_factory=dict, description="추가 메타데이터")
































