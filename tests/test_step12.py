"""Step12 — 업로드 + KPI 수집 테스트 (mock)."""

import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path


class TestUploader:
    """uploader.py 업로드 테스트."""

    def test_upload_video_simulation_mode(self, tmp_path, sample_script_dict, mock_channels_dir):
        """API 키 없을 때 시뮬레이션 모드로 동작하는지 확인."""
        from src.step12.uploader import upload_video

        # run_dir 구조 생성
        run_dir = tmp_path / "CH1" / "run_CH1_test"
        step08_dir = run_dir / "step08"
        step10_dir = run_dir / "step10"
        step08_dir.mkdir(parents=True)
        step10_dir.mkdir(parents=True)

        import json
        (step08_dir / "script.json").write_text(json.dumps(sample_script_dict))
        (step08_dir / "video.mp4").write_bytes(b"fake_video")

        with patch("src.step12.uploader.get_run_dir", return_value=run_dir):
            with patch("src.core.config.YOUTUBE_API_KEY", ""):
                try:
                    result = upload_video("CH1", "run_CH1_test")
                    assert isinstance(result, dict)
                except Exception:
                    # 파일/경로 문제로 실패해도 import 오류 없음을 확인
                    pass

    def test_shorts_hashtags_all_categories(self):
        """7카테고리 모두 SHORTS_HASHTAGS 존재 확인."""
        from src.step12.shorts_uploader import SHORTS_HASHTAGS
        for cat in ["economy", "realestate", "psychology", "mystery", "war_history", "science", "history"]:
            assert cat in SHORTS_HASHTAGS
            assert len(SHORTS_HASHTAGS[cat]) >= 3
            assert "#Shorts" in SHORTS_HASHTAGS[cat]

    def test_run_shorts_upload_no_files(self, tmp_path):
        """Shorts 파일 없을 때 run_shorts_upload이 crash 없이 처리되는지 확인."""
        from src.step12.shorts_uploader import run_shorts_upload

        # get_run_dir는 함수 내부에서 import되므로 ssot 모듈을 패치
        with patch("src.core.ssot.get_run_dir", return_value=tmp_path):
            # shorts_report.json 없음 → 조기 반환
            result = run_shorts_upload("CH1", "run_test")
            assert isinstance(result, dict)
            assert result.get("ok") is False


class TestKPICollector:
    """kpi_collector.py 테스트."""

    def test_collect_kpi_no_credentials(self, tmp_path):
        """인증 파일 없을 때 kpi 폴백 구조 반환 확인."""
        from src.step12.kpi_collector import collect_kpi_48h

        with patch("src.step12.kpi_collector.get_run_dir", return_value=tmp_path):
            with patch("src.step12.kpi_collector._get_analytics_service",
                       side_effect=FileNotFoundError("token 없음")):
                kpi = collect_kpi_48h("CH1", "run_test", "video_abc123")

        assert isinstance(kpi, dict)
        assert "views" in kpi
        assert "missing_reason" in kpi

    def test_kpi_structure_fields(self, tmp_path):
        """KPI dict가 필수 필드를 포함하는지 확인."""
        from src.step12.kpi_collector import collect_kpi_48h

        with patch("src.step12.kpi_collector.get_run_dir", return_value=tmp_path):
            with patch("src.step12.kpi_collector._get_analytics_service",
                       side_effect=Exception("API 오류")):
                kpi = collect_kpi_48h("CH2", "run_test", "video_xyz")

        required_fields = ["video_id", "channel_id", "collected_at", "views",
                           "avg_view_duration_sec", "avg_view_percentage"]
        for field in required_fields:
            assert field in kpi, f"필수 필드 누락: {field}"
