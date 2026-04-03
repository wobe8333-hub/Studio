"""Phase D-5 — Step13~17 단위 테스트.

Step13: learning_feedback
Step14: revenue_tracker
Step15: session_chain
Step16: risk_control
Step17: sustainability
"""

import json
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock


# ──────────────────────────────────────────────
# Step13 — learning_feedback
# ──────────────────────────────────────────────

class TestRunStep13:
    def _make_run_dir(self, tmp_path: Path, channel_id="CH1", run_id="run_001"):
        run_dir = tmp_path / "runs" / channel_id / run_id
        for sub in ("step08", "step11", "step12", "step13"):
            (run_dir / sub).mkdir(parents=True)
        return run_dir

    def test_creates_output_files(self, tmp_path, monkeypatch):
        """run_step13 완료 후 variant_performance.json / next_policy_update.json이 생성된다."""
        monkeypatch.setattr("src.step13.learning_feedback.MEMORY_DIR", tmp_path / "memory")
        monkeypatch.setattr("src.core.config.RUNS_DIR", tmp_path / "runs")
        (tmp_path / "memory").mkdir()
        run_dir = self._make_run_dir(tmp_path)

        from src.step13.learning_feedback import run_step13
        result = run_step13("CH1", "run_001")

        s13 = run_dir / "step13"
        assert (s13 / "variant_performance.json").exists()
        assert (s13 / "next_policy_update.json").exists()
        assert isinstance(result, dict)

    def test_revenue_on_track_uses_config_constant(self, tmp_path, monkeypatch):
        """revenue_on_track은 REVENUE_TARGET_PER_CHANNEL 기반 임계값을 사용한다."""
        from src.core.config import REVENUE_TARGET_PER_CHANNEL
        monkeypatch.setattr("src.step13.learning_feedback.MEMORY_DIR", tmp_path / "memory")
        monkeypatch.setattr("src.core.config.RUNS_DIR", tmp_path / "runs")
        (tmp_path / "memory").mkdir()
        run_dir = self._make_run_dir(tmp_path)

        # views가 임계값 이상인 경우
        kpi = {"views": REVENUE_TARGET_PER_CHANNEL // 40 + 1, "ctr": 3.0}
        (run_dir / "step12" / "kpi_48h.json").write_text(
            json.dumps(kpi), encoding="utf-8"
        )

        from src.step13.learning_feedback import run_step13
        run_step13("CH1", "run_001")

        data = json.loads(
            (run_dir / "step13" / "next_policy_update.json").read_text(encoding="utf-8-sig")
        )
        assert data["revenue_on_track"] is True

    def test_updates_bias_on_high_ctr_avp(self, tmp_path, monkeypatch):
        """CTR>=6.0, AVP>=50.0이면 winning_animation_patterns에 추가된다."""
        monkeypatch.setattr("src.step13.learning_feedback.MEMORY_DIR", tmp_path / "memory")
        monkeypatch.setattr("src.core.config.RUNS_DIR", tmp_path / "runs")
        (tmp_path / "memory").mkdir()
        run_dir = self._make_run_dir(tmp_path)

        kpi = {"ctr": 7.0, "avg_view_percentage": 55.0, "views": 100000}
        (run_dir / "step12" / "kpi_48h.json").write_text(
            json.dumps(kpi), encoding="utf-8"
        )

        from src.step13.learning_feedback import run_step13
        run_step13("CH1", "run_001")

        bias = json.loads(
            (tmp_path / "memory" / "topic_priority_bias.json").read_text(encoding="utf-8-sig")
        )
        assert len(bias.get("winning_animation_patterns", [])) >= 1

    def test_writes_run_history_jsonl(self, tmp_path, monkeypatch):
        """run_history.jsonl에 실행 이력이 한 줄 추가된다."""
        monkeypatch.setattr("src.step13.learning_feedback.MEMORY_DIR", tmp_path / "memory")
        monkeypatch.setattr("src.core.config.RUNS_DIR", tmp_path / "runs")
        (tmp_path / "memory").mkdir()
        self._make_run_dir(tmp_path)

        from src.step13.learning_feedback import run_step13
        run_step13("CH1", "run_001")

        history_path = tmp_path / "memory" / "run_history.jsonl"
        assert history_path.exists()
        lines = history_path.read_text(encoding="utf-8-sig").strip().split("\n")
        assert len(lines) >= 1
        record = json.loads(lines[0])
        assert record["channel_id"] == "CH1"
        assert record["run_id"] == "run_001"


# ──────────────────────────────────────────────
# Step14 — revenue_tracker
# ──────────────────────────────────────────────

class TestRevenueTracker:
    def test_update_revenue_monthly(self, tmp_path, monkeypatch):
        """update_revenue_monthly가 monthly_records에 데이터를 저장한다."""
        monkeypatch.setattr("src.step14.revenue_tracker.CHANNELS_DIR", tmp_path)
        (tmp_path / "CH1").mkdir()

        from src.step14.revenue_tracker import update_revenue_monthly
        result = update_revenue_monthly(
            channel_id="CH1",
            month_str="2026-04",
            adsense_krw=1_500_000,
            affiliate_krw=500_000,
            operating_cost=200_000,
        )

        assert result["monthly_records"]["2026-04"]["net_profit"] == 1_800_000
        assert result["monthly_records"]["2026-04"]["total_revenue"] == 2_000_000

    def test_get_total_revenue_aggregates_channels(self, tmp_path, monkeypatch):
        """get_total_revenue가 전체 채널 수익을 집계한다."""
        monkeypatch.setattr("src.step14.revenue_tracker.CHANNELS_DIR", tmp_path)
        monkeypatch.setattr("src.step14.revenue_tracker.GLOBAL_DIR", tmp_path / "global")
        (tmp_path / "global" / "revenue").mkdir(parents=True)

        for ch in ["CH1", "CH2", "CH3", "CH4", "CH5", "CH6", "CH7"]:
            ch_dir = tmp_path / ch
            ch_dir.mkdir()
            data = {
                "channel_id": ch,
                "monthly_records": {
                    "2026-04": {"net_profit": 1_000_000, "target_achieved": False}
                }
            }
            (ch_dir / "revenue_monthly.json").write_text(
                json.dumps(data), encoding="utf-8"
            )

        from src.step14.revenue_tracker import get_total_revenue
        result = get_total_revenue("2026-04")

        assert result["total_net_profit"] == 7_000_000
        assert "by_channel" in result

    def test_net_profit_calculation(self, tmp_path, monkeypatch):
        """net = adsense + affiliate - operating_cost."""
        monkeypatch.setattr("src.step14.revenue_tracker.CHANNELS_DIR", tmp_path)
        (tmp_path / "CH2").mkdir()

        from src.step14.revenue_tracker import update_revenue_monthly
        result = update_revenue_monthly("CH2", "2026-04", 1_200_000, 300_000, 100_000)

        net = result["monthly_records"]["2026-04"]["net_profit"]
        assert net == 1_400_000


# ──────────────────────────────────────────────
# Step15 — session_chain
# ──────────────────────────────────────────────

class TestSessionChain:
    def test_build_series_chain_returns_dict(self):
        """build_series_chain이 에피소드 체인 dict를 반환한다."""
        from src.step15.session_chain import build_series_chain
        result = build_series_chain("CH1", "금리 시리즈", episode_count=3)

        assert isinstance(result, dict)
        assert "episodes" in result or "channel_id" in result

    def test_episode_count_respected(self):
        """episode_count만큼 에피소드가 생성된다."""
        from src.step15.session_chain import build_series_chain
        result = build_series_chain("CH7", "역사 시리즈", episode_count=3)

        episodes = result.get("episodes", [])
        assert len(episodes) == 3


# ──────────────────────────────────────────────
# Step16 — risk_control
# ──────────────────────────────────────────────

class TestRunStep16:
    def test_returns_aggregate_dict(self, tmp_path, monkeypatch):
        """run_step16이 월별 리스크 집계 dict를 반환한다."""
        monkeypatch.setattr("src.step16.risk_control.CHANNELS_DIR", tmp_path)
        monkeypatch.setattr("src.step16.risk_control.GLOBAL_DIR", tmp_path / "global")
        (tmp_path / "global" / "risk").mkdir(parents=True)
        for ch in ["CH1", "CH2", "CH3", "CH4", "CH5", "CH6", "CH7"]:
            ch_dir = tmp_path / ch
            (ch_dir / "risk").mkdir(parents=True)

        from src.step16.risk_control import run_step16
        result = run_step16("2026-04")

        assert result["month"] == "2026-04"
        assert "channels" in result
        assert len(result["channels"]) == 7

    def test_risk_level_high_when_below_target(self, tmp_path, monkeypatch):
        """순이익이 목표 미달이면 risk_level이 HIGH다."""
        from src.core.config import REVENUE_TARGET_PER_CHANNEL
        monkeypatch.setattr("src.step16.risk_control.CHANNELS_DIR", tmp_path)
        monkeypatch.setattr("src.step16.risk_control.GLOBAL_DIR", tmp_path / "global")
        (tmp_path / "global" / "risk").mkdir(parents=True)
        for ch in ["CH1", "CH2", "CH3", "CH4", "CH5", "CH6", "CH7"]:
            ch_dir = tmp_path / ch
            (ch_dir / "risk").mkdir(parents=True)
            # 수익 파일 없음 → net=0 → 목표 미달

        from src.step16.risk_control import run_step16
        result = run_step16("2026-04")

        assert result["channels"]["CH1"]["risk_level"] == "HIGH"

    def test_target_achieved_true_when_above_target(self, tmp_path, monkeypatch):
        """순이익 >= 목표이면 target_achieved=True."""
        from src.core.config import REVENUE_TARGET_PER_CHANNEL
        monkeypatch.setattr("src.step16.risk_control.CHANNELS_DIR", tmp_path)
        monkeypatch.setattr("src.step16.risk_control.GLOBAL_DIR", tmp_path / "global")
        (tmp_path / "global" / "risk").mkdir(parents=True)

        for ch in ["CH1", "CH2", "CH3", "CH4", "CH5", "CH6", "CH7"]:
            ch_dir = tmp_path / ch
            (ch_dir / "risk").mkdir(parents=True)
            rev_data = {
                "monthly_records": {
                    "2026-04": {"net_profit": REVENUE_TARGET_PER_CHANNEL}
                }
            }
            (ch_dir / "revenue_monthly.json").write_text(
                json.dumps(rev_data), encoding="utf-8"
            )

        from src.step16.risk_control import run_step16
        result = run_step16("2026-04")

        assert result["channels"]["CH1"]["target_achieved"] is True


# ──────────────────────────────────────────────
# Step17 — sustainability
# ──────────────────────────────────────────────

class TestRunStep17:
    def test_returns_dict(self, tmp_path, monkeypatch):
        """run_step17이 dict를 반환한다."""
        monkeypatch.setattr("src.step17.sustainability.GLOBAL_DIR", tmp_path / "global")
        monkeypatch.setattr("src.step17.sustainability.CHANNEL_CATEGORIES",
                            {"CH1": "economy", "CH2": "realestate"})
        (tmp_path / "global" / "sustainability").mkdir(parents=True)

        from src.step17.sustainability import run_step17
        result = run_step17()

        assert isinstance(result, dict)

    def test_creates_sustainability_report(self, tmp_path, monkeypatch):
        """sustainability 보고서 파일이 생성된다."""
        monkeypatch.setattr("src.step17.sustainability.GLOBAL_DIR", tmp_path / "global")
        monkeypatch.setattr("src.step17.sustainability.CHANNEL_CATEGORIES",
                            {"CH1": "economy"})
        (tmp_path / "global" / "sustainability").mkdir(parents=True)

        from src.step17.sustainability import run_step17
        run_step17()

        sustainability_files = list((tmp_path / "global" / "sustainability").glob("*.json"))
        assert len(sustainability_files) >= 1
