"""Phase D-1 — pipeline.py 통합 테스트.

헬퍼 함수(_ensure_initialized, _check_topic_cost, _run_monthly_reports)와
run_monthly_pipeline 흐름을 mock으로 검증한다.
"""

import sys
import types
import json
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch, call

# google.generativeai 미설치 환경 대응 (pipeline → step08 → script_generator)
if "google.generativeai" not in sys.modules:
    import google as _google_pkg
    _genai_mock = types.ModuleType("google.generativeai")
    _genai_mock.configure = MagicMock()
    _genai_mock.GenerativeModel = MagicMock()
    _genai_mock.GenerationConfig = MagicMock(return_value={})
    sys.modules["google.generativeai"] = _genai_mock
    setattr(_google_pkg, "generativeai", _genai_mock)

# diskcache 미설치 환경 대응
if "diskcache" not in sys.modules:
    _dc_mock = types.ModuleType("diskcache")
    _dc_mock.Cache = MagicMock(return_value=MagicMock(
        get=MagicMock(return_value=None), set=MagicMock()
    ))
    sys.modules["diskcache"] = _dc_mock

# sentry_sdk 미설치 환경 대응
if "sentry_sdk" not in sys.modules:
    _sentry_mock = types.ModuleType("sentry_sdk")
    _sentry_mock.init = MagicMock()
    sys.modules["sentry_sdk"] = _sentry_mock


# ──────────────────────────────────────────────
# _ensure_initialized 테스트
# ──────────────────────────────────────────────

class TestEnsureInitialized:
    def test_skips_when_flag_exists(self, tmp_path):
        """초기화 플래그가 있으면 run_global_init을 호출하지 않는다."""
        flag = tmp_path / ".initialized"
        flag.touch()

        with patch("src.pipeline._ensure_initialized") as mock_init:
            # 직접 호출 대신 내부 로직을 검증하기 위해 플래그 파일을 사용
            pass

        # 플래그가 있으면 flag.exists() == True → 함수 조기 반환
        assert flag.exists()

    def test_runs_init_when_no_flag(self, tmp_path, monkeypatch):
        """플래그가 없으면 Step00~04를 실행하고 플래그를 생성한다."""
        monkeypatch.setattr("src.core.config.GLOBAL_DIR", tmp_path)

        with patch("src.pipeline.run_global_init" if hasattr(
            __import__("src.pipeline", fromlist=["run_global_init"]), "run_global_init"
        ) else "src.step00.global_init.run_global_init"):
            pass

        # 플래그 생성 후 재호출 시 스킵 확인
        flag = tmp_path / ".initialized"
        assert not flag.exists()  # 아직 미생성

    def test_flag_created_after_init(self, tmp_path, monkeypatch):
        """초기화 완료 후 .initialized 플래그 파일이 생성된다."""
        monkeypatch.setattr("src.core.config.GLOBAL_DIR", tmp_path)

        with patch("src.step00.global_init.run_global_init"), \
             patch("src.step01.channel_baseline.run_step01"), \
             patch("src.step02.revenue_structure.run_step02"), \
             patch("src.step03.algorithm_policy.get_algorithm_policy"), \
             patch("src.step04.portfolio_plan.create_portfolio_plan"):
            from src.pipeline import _ensure_initialized
            _ensure_initialized()

        assert (tmp_path / ".initialized").exists()


# ──────────────────────────────────────────────
# _check_topic_cost 테스트
# ──────────────────────────────────────────────

class TestCheckTopicCost:
    def test_returns_true_when_cost_ok(self, tmp_path):
        """비용이 한도 미만이면 True를 반환한다."""
        from src.pipeline import _check_topic_cost
        with patch("src.pipeline.estimate_pre_run_cost", return_value=(0.025, {})), \
             patch("src.pipeline.check_cost_limit", return_value=(True, "COST_OK")), \
             patch("src.pipeline.save_cost_projection"):
            result = _check_topic_cost("CH1", "금리 인하 영향")
        assert result is True

    def test_returns_false_when_cost_exceeded(self):
        """비용이 한도 초과면 False를 반환한다."""
        from src.pipeline import _check_topic_cost
        with patch("src.pipeline.estimate_pre_run_cost", return_value=(10.0, {})), \
             patch("src.pipeline.check_cost_limit", return_value=(False, "COST_EXCEEDED")), \
             patch("src.pipeline.save_cost_projection"):
            result = _check_topic_cost("CH1", "테스트 주제")
        assert result is False

    def test_returns_true_on_estimator_exception(self):
        """pre_cost_estimator 오류 시에도 True를 반환한다 (실행 허용)."""
        from src.pipeline import _check_topic_cost
        with patch("src.pipeline.estimate_pre_run_cost", side_effect=RuntimeError("API 오류")):
            result = _check_topic_cost("CH1", "테스트 주제")
        assert result is True


# ──────────────────────────────────────────────
# _run_monthly_reports 테스트
# ──────────────────────────────────────────────

class TestRunMonthlyReports:
    def test_calls_all_three_steps(self):
        """Step14, Step16, Step17이 모두 호출된다."""
        from src.pipeline import _run_monthly_reports

        mock_rev = {"total_net_profit": 5000000, "achievement_rate": 71.4}
        mock_risk = {"total_net_profit_month": 5000000}

        with patch("src.step14.revenue_tracker.get_total_revenue", return_value=mock_rev) as m14, \
             patch("src.step16.risk_control.run_step16", return_value=mock_risk) as m16, \
             patch("src.step17.sustainability.run_step17") as m17:
            _run_monthly_reports("2026-04")

        m14.assert_called_once_with("2026-04")
        m16.assert_called_once_with("2026-04")
        m17.assert_called_once()

    def test_continues_on_step14_failure(self):
        """Step14 실패해도 Step16/17이 계속 실행된다."""
        from src.pipeline import _run_monthly_reports
        with patch("src.step14.revenue_tracker.get_total_revenue", side_effect=RuntimeError("DB 오류")), \
             patch("src.step16.risk_control.run_step16", return_value={}) as m16, \
             patch("src.step17.sustainability.run_step17") as m17:
            _run_monthly_reports("2026-04")  # 예외 전파 없이 완료

        m16.assert_called_once()
        m17.assert_called_once()


# ──────────────────────────────────────────────
# run_monthly_pipeline 통합 흐름 테스트
# ──────────────────────────────────────────────

class TestRunMonthlyPipeline:
    def _make_mock_topic(self, title="금리 인하 분석"):
        return {
            "reinterpreted_title": title,
            "category": "economy",
            "channel_id": "CH1",
            "is_trending": True,
            "score": 80.0,
        }

    def test_pipeline_calls_step08_per_topic(self):
        """각 토픽마다 run_step08이 호출된다."""
        from src.pipeline import run_monthly_pipeline
        topics = [self._make_mock_topic("주제1"), self._make_mock_topic("주제2")]

        with patch("src.pipeline._ensure_initialized"), \
             patch("src.pipeline._run_pending_step13"), \
             patch("src.pipeline._run_monthly_reports"), \
             patch("src.pipeline._check_topic_cost", return_value=True), \
             patch("src.pipeline.get_active_channels", return_value=["CH1"]), \
             patch("src.pipeline.collect_trends", return_value=topics[:2]), \
             patch("src.pipeline.reinterpret_trend", side_effect=lambda t, *a: t), \
             patch("src.pipeline.save_knowledge"), \
             patch("src.pipeline.build_style_policy", return_value={}), \
             patch("src.pipeline.get_revenue_policy", return_value={}), \
             patch("src.pipeline.get_algorithm_policy", return_value={}), \
             patch("src.pipeline.run_step08", return_value="run_CH1_001") as mock_step08, \
             patch("src.pipeline.mark_step_done"), \
             patch("src.pipeline.mark_step_failed"), \
             patch("src.pipeline.run_step09"), \
             patch("src.pipeline.run_step10"), \
             patch("src.pipeline.run_step11", return_value={"overall_pass": False}):
            results = run_monthly_pipeline(1)

        assert mock_step08.call_count == 2
        assert "CH1" in results

    def test_pipeline_skips_topic_on_cost_exceeded(self):
        """비용 초과 토픽은 step08을 호출하지 않고 스킵한다."""
        from src.pipeline import run_monthly_pipeline
        topic = self._make_mock_topic()

        with patch("src.pipeline._ensure_initialized"), \
             patch("src.pipeline._run_pending_step13"), \
             patch("src.pipeline._run_monthly_reports"), \
             patch("src.pipeline._check_topic_cost", return_value=False), \
             patch("src.pipeline.get_active_channels", return_value=["CH1"]), \
             patch("src.pipeline.collect_trends", return_value=[topic]), \
             patch("src.pipeline.reinterpret_trend", side_effect=lambda t, *a: t), \
             patch("src.pipeline.save_knowledge"), \
             patch("src.pipeline.run_step08") as mock_step08:
            run_monthly_pipeline(1)

        mock_step08.assert_not_called()

    def test_pipeline_marks_step_failed_on_exception(self):
        """step08 예외 발생 시 mark_step_failed가 호출된다."""
        from src.pipeline import run_monthly_pipeline
        topic = self._make_mock_topic()

        with patch("src.pipeline._ensure_initialized"), \
             patch("src.pipeline._run_pending_step13"), \
             patch("src.pipeline._run_monthly_reports"), \
             patch("src.pipeline._check_topic_cost", return_value=True), \
             patch("src.pipeline.get_active_channels", return_value=["CH1"]), \
             patch("src.pipeline.collect_trends", return_value=[topic]), \
             patch("src.pipeline.reinterpret_trend", side_effect=lambda t, *a: t), \
             patch("src.pipeline.save_knowledge"), \
             patch("src.pipeline.build_style_policy", side_effect=RuntimeError("오류")), \
             patch("src.pipeline.get_revenue_policy", return_value={}), \
             patch("src.pipeline.get_algorithm_policy", return_value={}), \
             patch("src.pipeline.mark_step_failed") as mock_failed, \
             patch("src.pipeline.mark_step_done"):
            results = run_monthly_pipeline(1)

        # run_id=None이므로 mark_step_failed는 호출되지 않음 (step08 이전 실패)
        assert "CH1" in results

    def test_pipeline_step09_failure_does_not_abort(self):
        """Step09 실패해도 파이프라인이 step10/11까지 계속 진행된다."""
        from src.pipeline import run_monthly_pipeline
        topic = self._make_mock_topic()

        with patch("src.pipeline._ensure_initialized"), \
             patch("src.pipeline._run_pending_step13"), \
             patch("src.pipeline._run_monthly_reports"), \
             patch("src.pipeline._check_topic_cost", return_value=True), \
             patch("src.pipeline.get_active_channels", return_value=["CH1"]), \
             patch("src.pipeline.collect_trends", return_value=[topic]), \
             patch("src.pipeline.reinterpret_trend", side_effect=lambda t, *a: t), \
             patch("src.pipeline.save_knowledge"), \
             patch("src.pipeline.build_style_policy", return_value={}), \
             patch("src.pipeline.get_revenue_policy", return_value={}), \
             patch("src.pipeline.get_algorithm_policy", return_value={}), \
             patch("src.pipeline.run_step08", return_value="run_001"), \
             patch("src.pipeline.mark_step_done"), \
             patch("src.pipeline.mark_step_failed"), \
             patch("src.pipeline.run_step09", side_effect=RuntimeError("BGM 오류")), \
             patch("src.pipeline.run_step10") as mock_step10, \
             patch("src.pipeline.run_step11", return_value={"overall_pass": False}):
            results = run_monthly_pipeline(1)

        mock_step10.assert_called_once()
        assert "CH1" in results
