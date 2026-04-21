"""EpisodeMeta 스키마 + PQS 피처 검증 테스트"""
import pytest
from src.pipeline_v2.episode_schema import (
    EpisodeFeatures,
    EpisodeKpi,
    EpisodeMeta,
    FeedbackCycleInput,
    PlatformMeta,
    validate_pqs_features,
)


def _make_meta(channel_id: str = "CH1", episode_id: str = "CH1_2026W17_001") -> EpisodeMeta:
    return EpisodeMeta(
        episode_id=episode_id,
        channel_id=channel_id,
        series_id="금리_시리즈",
        episode_index=1,
    )


def test_episode_meta_defaults():
    meta = _make_meta()
    assert meta.episode_id == "CH1_2026W17_001"
    assert meta.channel_id == "CH1"
    assert meta.kpi_48h.views is None
    assert meta.features.qc_pass is False


def test_pqs_features_all_none_fails():
    meta = _make_meta()
    valid, missing = validate_pqs_features(meta)
    assert not valid
    assert len(missing) > 0


def test_pqs_features_fully_populated_passes():
    meta = _make_meta()
    f = meta.features
    f.thumbnail_ctr_3variants = [0.06, 0.07, 0.05]
    f.title_hook_type = "curiosity_gap"
    f.opening_hook_sec = 12
    f.script_ngram_density = 0.83
    f.emotion_peaks = [42, 187, 263]
    f.character_consistency_score = 0.89
    f.audio_loudness_lufs = -14.2
    f.duration_sec = 482
    f.manim_inserts_count = 3
    f.bgm_mood_tag = "calm_piano"
    f.narrator_voice_id = "voice_abc"
    f.guest_voice_id = "voice_def"
    f.subtitle_sync_score = 0.95
    f.video_frame_drop_count = 0
    f.meta_validation_passed = True
    f.series_episode_index = 3
    f.shorts_derived_count = 4
    f.platform_tag = "youtube_longform"
    f.qc_pass = True
    f.production_time_sec = 14400

    valid, missing = validate_pqs_features(meta)
    assert valid, f"누락 필드: {missing}"
    assert missing == []


def test_kpi_nullable():
    kpi = EpisodeKpi()
    assert kpi.views is None
    assert kpi.ctr is None
    assert kpi.avd_pct is None


def test_platform_meta_defaults():
    meta = _make_meta()
    assert "youtube_longform" in meta.platform.platforms_uploaded


def test_feedback_cycle_input_defaults():
    meta = _make_meta()
    assert meta.feedback_cycle_input.winning_hook is None
    assert meta.feedback_cycle_input.losing_segments == []
