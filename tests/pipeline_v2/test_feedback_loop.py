"""피드백 루프 단위 테스트"""
import pytest
from src.pipeline_v2.episode_schema import EpisodeMeta, EpisodeKpi
from src.pipeline_v2.feedback_loop import generate_next_series_input


def _make_meta_with_kpi(ep_id: str, ctr: float, avd_pct: float, hook: str) -> EpisodeMeta:
    m = EpisodeMeta(episode_id=ep_id, channel_id="CH1", series_id="test_series", episode_index=1)
    m.kpi_48h = EpisodeKpi(views=10000, ctr=ctr, avd_pct=avd_pct)
    m.features.title_hook_type = hook
    m.features.bgm_mood_tag = "calm_piano"
    return m


def test_generate_next_series_input_empty():
    result = generate_next_series_input("CH1", [])
    assert result == {}


def test_generate_next_series_input_winning_hooks():
    episodes = [
        _make_meta_with_kpi("ep001", 0.08, 62.0, "curiosity_gap"),
        _make_meta_with_kpi("ep002", 0.05, 55.0, "list"),
        _make_meta_with_kpi("ep003", 0.10, 70.0, "shocking"),
    ]
    result = generate_next_series_input("CH1", episodes)
    assert "winning_hooks" in result
    assert "avg_ctr" in result
    assert "avg_avd_pct" in result
    assert result["avg_ctr"] == pytest.approx((0.08 + 0.05 + 0.10) / 3, abs=0.001)


def test_losing_segments_detected():
    episodes = [
        _make_meta_with_kpi("ep001", 0.08, 65.0, "curiosity_gap"),
        _make_meta_with_kpi("ep002", 0.03, 30.0, "list"),
        _make_meta_with_kpi("ep003", 0.02, 28.0, "question"),
    ]
    result = generate_next_series_input("CH1", episodes)
    assert len(result["losing_segments"]) >= 1


def test_recommended_hook_types():
    episodes = [_make_meta_with_kpi(f"ep{i}", 0.06 + i * 0.01, 60.0, "curiosity_gap") for i in range(5)]
    result = generate_next_series_input("CH1", episodes)
    assert isinstance(result.get("recommended_hook_types"), list)
