"""Phase D-3 — Step07 revenue_policy 단위 테스트."""

import json
import pytest
from pathlib import Path
from unittest.mock import patch


class TestGetRevenuePolicy:
    def test_creates_file_when_missing(self, tmp_path, monkeypatch):
        """revenue_policy.json이 없으면 새로 생성한다."""
        monkeypatch.setattr("src.step07.revenue_policy.CHANNELS_DIR", tmp_path)
        (tmp_path / "CH1").mkdir()

        from src.step07.revenue_policy import get_revenue_policy
        result = get_revenue_policy("CH1")

        assert (tmp_path / "CH1" / "revenue_policy.json").exists()
        assert isinstance(result, dict)

    def test_returns_existing_file_unchanged(self, tmp_path, monkeypatch):
        """기존 파일이 있으면 그대로 반환한다."""
        monkeypatch.setattr("src.step07.revenue_policy.CHANNELS_DIR", tmp_path)
        ch_dir = tmp_path / "CH1"
        ch_dir.mkdir()
        existing = {"channel_id": "CH1", "revenue_target_net": 2000000, "policy_version": "v2.0"}
        (ch_dir / "revenue_policy.json").write_text(
            json.dumps(existing, ensure_ascii=False), encoding="utf-8"
        )

        from src.step07.revenue_policy import get_revenue_policy
        result = get_revenue_policy("CH1")

        assert result["revenue_target_net"] == 2000000
        assert result["policy_version"] == "v2.0"

    def test_revenue_target_matches_config(self, tmp_path, monkeypatch):
        """신규 생성 시 revenue_target_net이 config의 REVENUE_TARGET_PER_CHANNEL과 일치한다."""
        from src.core.config import REVENUE_TARGET_PER_CHANNEL
        monkeypatch.setattr("src.step07.revenue_policy.CHANNELS_DIR", tmp_path)
        (tmp_path / "CH2").mkdir()

        from src.step07.revenue_policy import get_revenue_policy
        result = get_revenue_policy("CH2")

        assert result["revenue_target_net"] == REVENUE_TARGET_PER_CHANNEL

    def test_all_7_channels_create_policy(self, tmp_path, monkeypatch):
        """7채널 모두 revenue_policy.json을 생성할 수 있다."""
        monkeypatch.setattr("src.step07.revenue_policy.CHANNELS_DIR", tmp_path)
        for ch in ["CH1", "CH2", "CH3", "CH4", "CH5", "CH6", "CH7"]:
            (tmp_path / ch).mkdir()

        from src.step07.revenue_policy import get_revenue_policy
        for ch in ["CH1", "CH2", "CH3", "CH4", "CH5", "CH6", "CH7"]:
            result = get_revenue_policy(ch)
            assert result["channel_id"] == ch
            assert result["rpm_proxy"] > 0

    def test_policy_contains_required_keys(self, tmp_path, monkeypatch):
        """생성된 정책에 필수 키가 모두 포함된다."""
        monkeypatch.setattr("src.step07.revenue_policy.CHANNELS_DIR", tmp_path)
        (tmp_path / "CH3").mkdir()

        from src.step07.revenue_policy import get_revenue_policy
        result = get_revenue_policy("CH3")

        required = ["channel_id", "revenue_target_net", "rpm_proxy",
                    "rpm_initial", "rpm_floor", "midroll_count_target"]
        for key in required:
            assert key in result, f"필수 키 누락: {key}"
