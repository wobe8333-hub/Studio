"""Step08 FFmpeg composer 단위 테스트."""
import subprocess
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest


def _load_ffmpeg_composer():
    """google.generativeai 체인 없이 ffmpeg_composer.py만 직접 로드."""
    import importlib.util, sys, types

    # google.generativeai mock (conftest.py와 동일한 패턴)
    if "google.generativeai" not in sys.modules:
        import google as _g
        m = types.ModuleType("google.generativeai")
        sys.modules["google.generativeai"] = m
        setattr(_g, "generativeai", m)

    spec = importlib.util.spec_from_file_location(
        "ffmpeg_composer",
        Path(__file__).parent.parent / "src" / "step08" / "ffmpeg_composer.py",
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


composer = _load_ffmpeg_composer()


class TestImageToClip:
    """image_to_clip CRF 설정 테스트."""

    def test_crf_22_in_command(self, tmp_path):
        """image_to_clip 커맨드에 -crf 22가 포함되어야 한다."""
        img = tmp_path / "test.png"
        img.write_bytes(b"fake_png")
        out = tmp_path / "out.mp4"

        captured_cmd = []

        def fake_run(cmd, **kwargs):
            captured_cmd.extend(cmd)
            r = MagicMock()
            r.returncode = 0
            return r

        with patch("subprocess.run", side_effect=fake_run):
            composer.image_to_clip(img, out, duration_sec=5.0)

        assert "-crf" in captured_cmd, "FFmpeg 커맨드에 -crf 플래그가 없음"
        crf_idx = captured_cmd.index("-crf")
        assert captured_cmd[crf_idx + 1] == "22", \
            f"CRF 값이 22가 아님: {captured_cmd[crf_idx + 1]}"

    def test_preset_medium_in_command(self, tmp_path):
        """-preset medium이 커맨드에 포함되어야 한다."""
        img = tmp_path / "test.png"
        img.write_bytes(b"fake_png")
        out = tmp_path / "out.mp4"

        captured_cmd = []

        def fake_run(cmd, **kwargs):
            captured_cmd.extend(cmd)
            r = MagicMock()
            r.returncode = 0
            return r

        with patch("subprocess.run", side_effect=fake_run):
            composer.image_to_clip(img, out)

        assert "-preset" in captured_cmd, "FFmpeg 커맨드에 -preset 플래그가 없음"
        preset_idx = captured_cmd.index("-preset")
        assert captured_cmd[preset_idx + 1] == "medium", \
            f"preset 값이 medium이 아님: {captured_cmd[preset_idx + 1]}"


class TestAddSubtitles:
    """add_subtitles 실패 시 False를 반환해야 한다."""

    def test_returns_false_on_ffmpeg_failure(self, tmp_path):
        """add_subtitles FFmpeg 실패 시 False를 반환해야 한다 (현재 True를 반환하는 버그)."""
        video = tmp_path / "video.mp4"
        video.write_bytes(b"fake_mp4")
        srt = tmp_path / "subs.srt"
        srt.write_text("1\n00:00:00,000 --> 00:00:01,000\n테스트\n\n", encoding="utf-8")
        out = tmp_path / "out.mp4"

        def fake_run_fail(cmd, **kwargs):
            r = MagicMock()
            r.returncode = 1
            r.stderr = "FFmpeg error"
            return r

        with patch("subprocess.run", side_effect=fake_run_fail):
            result = composer.add_subtitles(video, srt, out)

        assert result is False, \
            "add_subtitles FFmpeg 실패 시 False를 반환해야 하는데 True를 반환함 (버그)"
