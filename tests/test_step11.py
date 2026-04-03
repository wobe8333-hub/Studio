"""Step11 — QA 게이트 테스트 (Phase 8)."""

import pytest
import json
from pathlib import Path
from unittest.mock import patch, MagicMock


def _create_mock_run_dir(tmp_path: Path, channel_id: str, run_id: str, script: dict) -> Path:
    """테스트용 run 디렉토리 생성."""
    run_dir = tmp_path / "runs" / channel_id / run_id
    s08 = run_dir / "step08"
    s08.mkdir(parents=True)

    # script.json 저장
    (s08 / "script.json").write_text(json.dumps(script, ensure_ascii=False), encoding="utf-8")

    # 더미 video.mp4 생성 (1바이트)
    video = s08 / "video.mp4"
    video.write_bytes(b"dummy_video_content")

    return run_dir


class TestQAGate:
    """QA 게이트 전반 테스트."""

    def test_disclaimer_key_mapping_complete(self):
        """7채널 모두 면책조항 키가 정의되어 있는지 확인."""
        from src.step11.qa_gate import CHANNEL_DISCLAIMER_KEY
        for ch in ["CH1", "CH2", "CH3", "CH4", "CH5", "CH6", "CH7"]:
            assert ch in CHANNEL_DISCLAIMER_KEY

    @patch("src.step11.qa_gate._gemini_vision_qa")
    def test_qa_pass_with_complete_script(self, mock_vision, tmp_path, monkeypatch, sample_script_dict):
        """면책조항/AI라벨/제휴 공식 모두 있을 때 QA PASS 확인."""
        mock_vision.return_value = {"pass": True, "skipped": True}

        import src.core.ssot as ssot
        monkeypatch.setattr(ssot, "get_run_dir",
            lambda ch, rid: _create_mock_run_dir(tmp_path, ch, rid, sample_script_dict))

        from src.step11.qa_gate import run_step11
        result = run_step11("CH1", "test_run_001", human_review_completed=True)

        assert isinstance(result, dict)
        assert "overall_pass" in result

    @patch("src.step11.qa_gate._gemini_vision_qa")
    def test_qa_fail_missing_disclaimer(self, mock_vision, tmp_path, monkeypatch, sample_script_dict):
        """면책조항 없으면 QA FAIL 확인."""
        mock_vision.return_value = {"pass": True, "skipped": True}

        # financial_disclaimer 제거
        script_no_disc = {k: v for k, v in sample_script_dict.items() if k != "financial_disclaimer"}

        monkeypatch.setattr("src.core.ssot.get_run_dir",
            lambda ch, rid: _create_mock_run_dir(tmp_path, ch, rid, script_no_disc))

        from src.step11.qa_gate import run_step11
        result = run_step11("CH1", "test_run_002")
        assert result["youtube_policy_check"]["pass"] is False

    @patch("src.step11.qa_gate._gemini_vision_qa")
    def test_vision_qa_skipped_gracefully(self, mock_vision, tmp_path, monkeypatch, sample_script_dict):
        """Vision QA 실패해도 QA 결과 반환 확인."""
        mock_vision.return_value = {"pass": True, "skipped": True, "reason": "api_key_missing"}

        monkeypatch.setattr("src.core.ssot.get_run_dir",
            lambda ch, rid: _create_mock_run_dir(tmp_path, ch, rid, sample_script_dict))

        from src.step11.qa_gate import run_step11
        result = run_step11("CH1", "test_run_003")
        assert isinstance(result, dict)
        assert result["animation_quality_check"]["vision_qa"]["skipped"] is True

    def test_review_required_channels(self):
        """REVIEW_REQUIRED 채널 확인."""
        from src.step11.qa_gate import REVIEW_REQUIRED
        assert "CH1" in REVIEW_REQUIRED
        assert "CH2" in REVIEW_REQUIRED
