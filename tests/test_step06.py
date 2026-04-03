"""Phase D-3 — Step06 style_policy 단위 테스트."""

import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path


SAMPLE_TOPIC = {
    "reinterpreted_title": "금리 인하가 내 지갑에 미치는 영향",
    "is_trending": True,
    "original_trend": {"video_id": "abc123"},
}

SAMPLE_CHANNEL = {
    "channel_id": "CH1",
    "category": "economy",
    "rpm_tier": "HIGH",
    "affiliate": {
        "product": "토스증권",
        "click_rate_initial": 0.003,
        "click_rate_growth": 0.006,
        "purchase_conversion_rate": 0.01,
    },
}


class TestBuildStylePolicy:
    def _build(self, channel_id="CH1", topic=None, month_number=1):
        from src.step06.style_policy import build_style_policy
        return build_style_policy(channel_id, topic or SAMPLE_TOPIC, month_number)

    def test_returns_dict_with_required_keys(self, tmp_path, monkeypatch):
        """build_style_policy가 필수 키를 모두 포함한 dict를 반환한다."""
        monkeypatch.setattr("src.core.config.CHANNELS_DIR", tmp_path)
        monkeypatch.setattr("src.core.config.MEMORY_DIR", tmp_path)
        monkeypatch.setattr("src.core.config.KAS_ROOT", tmp_path)
        (tmp_path / "CH1").mkdir(exist_ok=True)

        with patch("src.step00.channel_registry.get_channel", return_value=SAMPLE_CHANNEL), \
             patch("src.step07.revenue_policy.get_revenue_policy", return_value={"revenue_target_net": 2000000}), \
             patch("src.step03.algorithm_policy.get_algorithm_policy", return_value={
                 "upload_timing_rules": {"preferred_days": ["화", "목"], "preferred_hours_kst": [18]}
             }):
            result = self._build()

        required_keys = [
            "channel_id", "animation_style", "render_tool",
            "hook_direction", "preferred_title_mode", "style_policy_fingerprint"
        ]
        for key in required_keys:
            assert key in result, f"필수 키 누락: {key}"

    def test_channel_animation_style_mapping(self, tmp_path, monkeypatch):
        """채널별 animation_style이 올바르게 매핑된다."""
        monkeypatch.setattr("src.core.config.CHANNELS_DIR", tmp_path)
        monkeypatch.setattr("src.core.config.MEMORY_DIR", tmp_path)
        monkeypatch.setattr("src.core.config.KAS_ROOT", tmp_path)

        expected = {
            "CH1": "comparison",
            "CH3": "metaphor",
            "CH5": "timeline",
            "CH6": "process",
        }
        for ch, expected_style in expected.items():
            (tmp_path / ch).mkdir(exist_ok=True)
            with patch("src.step00.channel_registry.get_channel", return_value={
                **SAMPLE_CHANNEL, "channel_id": ch
            }), \
                 patch("src.step07.revenue_policy.get_revenue_policy", return_value={}), \
                 patch("src.step03.algorithm_policy.get_algorithm_policy", return_value={}):
                from src.step06.style_policy import build_style_policy
                result = build_style_policy(ch, SAMPLE_TOPIC, 1)
            assert result["animation_style"] == expected_style, f"{ch}: {result['animation_style']} != {expected_style}"

    def test_rpm_stage_initial_for_month_1(self, tmp_path, monkeypatch):
        """월차 1~3은 INITIAL 스테이지 (click_rate_initial 적용)."""
        monkeypatch.setattr("src.core.config.CHANNELS_DIR", tmp_path)
        monkeypatch.setattr("src.core.config.MEMORY_DIR", tmp_path)
        monkeypatch.setattr("src.core.config.KAS_ROOT", tmp_path)
        (tmp_path / "CH1").mkdir(exist_ok=True)

        with patch("src.step00.channel_registry.get_channel", return_value=SAMPLE_CHANNEL), \
             patch("src.step07.revenue_policy.get_revenue_policy", return_value={}), \
             patch("src.step03.algorithm_policy.get_algorithm_policy", return_value={}):
            result = self._build(month_number=1)

        assert result["affiliate_click_rate_applied"] == SAMPLE_CHANNEL["affiliate"]["click_rate_initial"]

    def test_fingerprint_is_stable(self, tmp_path, monkeypatch):
        """동일 입력에 대해 fingerprint가 일정하다."""
        monkeypatch.setattr("src.core.config.CHANNELS_DIR", tmp_path)
        monkeypatch.setattr("src.core.config.MEMORY_DIR", tmp_path)
        monkeypatch.setattr("src.core.config.KAS_ROOT", tmp_path)
        (tmp_path / "CH1").mkdir(exist_ok=True)

        with patch("src.step00.channel_registry.get_channel", return_value=SAMPLE_CHANNEL), \
             patch("src.step07.revenue_policy.get_revenue_policy", return_value={}), \
             patch("src.step03.algorithm_policy.get_algorithm_policy", return_value={}):
            r1 = self._build()
            r2 = self._build()

        assert r1["style_policy_fingerprint"] == r2["style_policy_fingerprint"]

    def test_trending_topic_sets_trend_ref(self, tmp_path, monkeypatch):
        """is_trending=True인 주제는 trend_topic_ref가 설정된다."""
        monkeypatch.setattr("src.core.config.CHANNELS_DIR", tmp_path)
        monkeypatch.setattr("src.core.config.MEMORY_DIR", tmp_path)
        monkeypatch.setattr("src.core.config.KAS_ROOT", tmp_path)
        (tmp_path / "CH1").mkdir(exist_ok=True)

        with patch("src.step00.channel_registry.get_channel", return_value=SAMPLE_CHANNEL), \
             patch("src.step07.revenue_policy.get_revenue_policy", return_value={}), \
             patch("src.step03.algorithm_policy.get_algorithm_policy", return_value={}):
            result = self._build(topic={**SAMPLE_TOPIC, "is_trending": True})

        assert result["trend_topic_ref"] == "abc123"
