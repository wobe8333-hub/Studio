"""Phase D-4 — Step09 BGM 오버레이 단위 테스트."""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock


class TestRunStep09:
    def _make_run_dir(self, tmp_path: Path, channel_id="CH1", run_id="run_001"):
        run_dir = tmp_path / "runs" / channel_id / run_id
        step08_dir = run_dir / "step08"
        step08_dir.mkdir(parents=True)
        return run_dir, step08_dir

    def test_returns_false_when_video_missing(self, tmp_path, monkeypatch):
        """video.mp4가 없으면 False를 반환한다."""
        monkeypatch.setattr("src.core.config.RUNS_DIR", tmp_path / "runs")
        run_dir, step08_dir = self._make_run_dir(tmp_path)
        # video.mp4를 생성하지 않음

        from src.step09.bgm_overlay import run_step09
        result = run_step09("CH1", "run_001")

        assert result is False

    def test_returns_false_when_bgm_missing(self, tmp_path, monkeypatch):
        """BGM 소스 생성에 실패하면 False를 반환한다."""
        monkeypatch.setattr("src.core.config.RUNS_DIR", tmp_path / "runs")
        run_dir, step08_dir = self._make_run_dir(tmp_path)
        (step08_dir / "video.mp4").write_bytes(b"fake_video")

        with patch("src.step09.bgm_generator.generate_bgm", return_value=None):
            from src.step09.bgm_overlay import run_step09
            result = run_step09("CH1", "run_001")

        assert result is False

    def test_returns_true_on_success(self, tmp_path, monkeypatch):
        """BGM 오버레이 성공 시 True를 반환한다."""
        monkeypatch.setattr("src.core.config.RUNS_DIR", tmp_path / "runs")
        run_dir, step08_dir = self._make_run_dir(tmp_path)
        video_path = step08_dir / "video.mp4"
        video_path.write_bytes(b"fake_video")

        bgm_path = tmp_path / "bgm_sample.wav"
        bgm_path.write_bytes(b"fake_wav")
        bgm_out = step08_dir / "video_bgm.mp4"

        def fake_overlay(video, bgm, out):
            out.write_bytes(b"fake_bgm_video")
            return True

        with patch("src.step09.bgm_generator.generate_bgm", return_value=bgm_path), \
             patch("src.step09.bgm_overlay.overlay_bgm", side_effect=fake_overlay):
            from src.step09.bgm_overlay import run_step09
            result = run_step09("CH1", "run_001")

        assert result is True

    def test_bgm_tone_defined_for_all_channels(self):
        """7채널 모두 BGM 톤이 정의되어 있다."""
        from src.step09.bgm_overlay import CHANNEL_BGM_TONE
        for ch in ["CH1", "CH2", "CH3", "CH4", "CH5", "CH6", "CH7"]:
            assert ch in CHANNEL_BGM_TONE
            assert len(CHANNEL_BGM_TONE[ch]) > 0

    def test_updates_render_report_on_bgm_missing(self, tmp_path, monkeypatch):
        """BGM 없을 때 render_report.json의 bgm_used가 False로 업데이트된다."""
        import json
        monkeypatch.setattr("src.core.config.RUNS_DIR", tmp_path / "runs")
        run_dir, step08_dir = self._make_run_dir(tmp_path)
        (step08_dir / "video.mp4").write_bytes(b"fake_video")
        rr_path = step08_dir / "render_report.json"
        rr_path.write_text(json.dumps({"bgm_used": True}), encoding="utf-8")

        with patch("src.step09.bgm_generator.generate_bgm", return_value=None):
            from src.step09.bgm_overlay import run_step09
            run_step09("CH1", "run_001")

        updated = json.loads(rr_path.read_text(encoding="utf-8-sig"))
        assert updated["bgm_used"] is False
