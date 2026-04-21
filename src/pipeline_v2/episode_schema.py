"""G3 호환 Episode Metadata 스키마 정의 (최적화 ① — PQS/Content Graph 사전 설계)

모든 pipeline_v2 컴포넌트는 이 스키마를 사용해 episode JSON을 읽고 써야 한다.
Phase 2 PQS XGBoost 학습 피처와 1:1 매핑되어 있으므로 필드명 변경 금지.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field

from src.core.ssot import read_json, write_json

EPISODES_ROOT = Path("data/episodes")


class EpisodeFeatures(BaseModel):
    """PQS 학습 피처 — 생성 단계별 자동 채움 (변경 금지)."""

    thumbnail_ctr_3variants: list[float] = Field(default_factory=list)
    title_hook_type: str = ""                 # curiosity_gap|how_to|shocking|list|question
    opening_hook_sec: int = 0
    script_ngram_density: float = 0.0
    emotion_peaks: list[int] = Field(default_factory=list)
    character_consistency_score: float = 0.0  # QC Layer1 J3 점수
    audio_loudness_lufs: float = 0.0          # EBU R128
    duration_sec: int = 0
    manim_inserts_count: int = 0              # CH1/CH2 전용
    bgm_mood_tag: str = ""
    bgm_bpm: int = 0
    narrator_voice_id: str = ""
    guest_voice_id: str = ""
    subtitle_sync_score: float = 0.0          # QC Layer3
    video_frame_drop_count: int = 0           # QC Layer4
    meta_validation_passed: bool = False       # QC Layer5
    series_episode_index: int = 0
    shorts_derived_count: int = 0
    platform_tag: str = "youtube_longform"
    qc_pass: bool = False
    production_time_sec: int = 0


class EpisodeKpi(BaseModel):
    """YouTube KPI — 피드백 루프(T23)가 자동 채움."""

    views: Optional[int] = None
    ctr: Optional[float] = None
    avd_pct: Optional[float] = None
    retention_curve: Optional[list[float]] = None  # 초당 시청 유지율 배열


class FeedbackCycleInput(BaseModel):
    """차기 시리즈 기획 반영용 — 피드백 루프 출력."""

    winning_hook: Optional[str] = None
    losing_segments: list[dict] = Field(default_factory=list)
    recommended_topics: list[str] = Field(default_factory=list)


class PlatformMeta(BaseModel):
    """Multi-Platform 사전 설계 (Phase 2 T57 착수 시 확장)."""

    platforms_uploaded: list[str] = Field(default_factory=lambda: ["youtube_longform"])
    platforms_ready: list[str] = Field(
        default_factory=lambda: ["youtube_shorts", "tiktok", "ig_reels", "x"]
    )


class EpisodeMeta(BaseModel):
    """Episode 전체 메타데이터 (G3 호환 구조).

    저장 경로: data/episodes/CH{1-7}/{YYYY-MM}/episode_{id}.json
    """

    episode_id: str = Field(default_factory=lambda: str(uuid.uuid4())[:12])
    channel_id: str
    series_id: str
    episode_index: int
    title: str = ""
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    features: EpisodeFeatures = Field(default_factory=EpisodeFeatures)
    kpi_48h: EpisodeKpi = Field(default_factory=EpisodeKpi)
    kpi_7d: EpisodeKpi = Field(default_factory=EpisodeKpi)
    feedback_cycle_input: FeedbackCycleInput = Field(default_factory=FeedbackCycleInput)
    platform: PlatformMeta = Field(default_factory=PlatformMeta)

    # 파일 경로 참조 (런타임에 채움)
    video_path: str = ""
    thumbnail_paths: list[str] = Field(default_factory=list)
    audio_path: str = ""
    subtitle_path: str = ""


def episode_path(channel_id: str, episode_id: str, year_month: Optional[str] = None) -> Path:
    if year_month is None:
        year_month = datetime.now(timezone.utc).strftime("%Y-%m")
    return EPISODES_ROOT / channel_id / year_month / f"episode_{episode_id}.json"


def save_episode(meta: EpisodeMeta) -> Path:
    path = episode_path(meta.channel_id, meta.episode_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    write_json(path, meta.model_dump())
    return path


def load_episode(channel_id: str, episode_id: str, year_month: Optional[str] = None) -> EpisodeMeta:
    path = episode_path(channel_id, episode_id, year_month)
    data = read_json(path)
    return EpisodeMeta.model_validate(data)


def validate_pqs_features(meta: EpisodeMeta) -> tuple[bool, list[str]]:
    """PQS 필드 완전 채움 검증 — T50 감사에서 사용."""
    errors: list[str] = []
    f = meta.features

    if not f.title_hook_type:
        errors.append("title_hook_type 미설정")
    if f.opening_hook_sec == 0:
        errors.append("opening_hook_sec 미설정")
    if f.duration_sec == 0:
        errors.append("duration_sec 미설정")
    if f.character_consistency_score == 0.0:
        errors.append("character_consistency_score 미채움 (QC Layer1 필요)")
    if f.audio_loudness_lufs == 0.0:
        errors.append("audio_loudness_lufs 미채움 (QC Layer2 필요)")
    if not f.bgm_mood_tag:
        errors.append("bgm_mood_tag 미설정")
    if not f.narrator_voice_id:
        errors.append("narrator_voice_id 미설정")
    if not f.meta_validation_passed:
        errors.append("meta_validation_passed=False (QC Layer5 미통과)")

    return len(errors) == 0, errors
