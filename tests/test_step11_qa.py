"""Step11 QA 게이트 — 프레임 추출 시간 계산 테스트."""
import subprocess
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest


def _load_qa_gate():
    import importlib.util, sys, types
    if "google.generativeai" not in sys.modules:
        import google as _g
        m = types.ModuleType("google.generativeai")
        sys.modules["google.generativeai"] = m
        setattr(_g, "generativeai", m)
    for mod_name in ["src.core.ssot", "src.core.config"]:
        if mod_name not in sys.modules:
            fake = types.ModuleType(mod_name)
            fake.read_json = lambda p: {}
            fake.write_json = lambda p, d: None
            fake.json_exists = lambda p: False
            fake.now_iso = lambda: "2026-01-01T00:00:00"
            fake.get_run_dir = lambda ch, run: Path("/tmp/fake")
            fake.GEMINI_API_KEY = "fake_key"
            fake.GEMINI_TEXT_MODEL = "gemini-2.0-flash"
            sys.modules[mod_name] = fake
    spec = importlib.util.spec_from_file_location(
        "qa_gate",
        Path(__file__).parent.parent / "src" / "step11" / "qa_gate.py",
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


qa_gate = _load_qa_gate()


class TestGeminiVisionFrameExtraction:
    """_gemini_vision_qa의 프레임 추출 시간 계산이 실제 영상 길이 기반이어야 한다."""

    def test_ffprobe_called_for_duration(self, tmp_path):
        """_gemini_vision_qa가 ffprobe를 호출하여 실제 영상 길이를 측정해야 한다."""
        video = tmp_path / "video.mp4"
        video.write_bytes(b"fake_mp4")

        subprocess_calls = []

        def fake_run(cmd, **kwargs):
            subprocess_calls.append(list(cmd))
            r = MagicMock()
            r.returncode = 0
            r.stdout = "720.0"
            r.stderr = ""
            return r

        with patch("subprocess.run", side_effect=fake_run):
            qa_gate._gemini_vision_qa(video)

        cmds_flat = [str(c) for calls in subprocess_calls for c in calls]
        assert any("ffprobe" in c for c in cmds_flat), \
            "ffprobe를 호출하지 않음 — 실제 영상 길이를 측정해야 한다"

    def test_frame_seek_beyond_108s_for_720s_video(self, tmp_path):
        """720초 영상에서 50% 이상 위치의 프레임이 200초 이후에서 추출되어야 한다.
        (기존 버그: 50*1.2 = 60초, 수정 후: 50/100*720 = 360초)"""
        video = tmp_path / "video.mp4"
        video.write_bytes(b"fake_mp4")

        ffmpeg_ss_values = []

        def smart_run(cmd, **kwargs):
            cmd_list = list(cmd)
            r = MagicMock()
            r.returncode = 0
            r.stderr = ""
            if "ffprobe" in str(cmd_list):
                r.stdout = "720.0"
            else:
                r.stdout = ""
                # -ss 값 캡처
                if "-ss" in cmd_list:
                    ss_idx = cmd_list.index("-ss")
                    ffmpeg_ss_values.append(float(cmd_list[ss_idx + 1]))
            return r

        with patch("subprocess.run", side_effect=smart_run):
            qa_gate._gemini_vision_qa(video)

        assert ffmpeg_ss_values, "ffmpeg -ss 호출이 없음"
        # 720초 영상에서 최소 하나의 프레임은 200초 이후여야 함
        assert any(s > 200 for s in ffmpeg_ss_values), \
            f"720초 영상에서 모든 프레임이 200초 이전: {ffmpeg_ss_values} (버그: pct*1.2 고정값)"
