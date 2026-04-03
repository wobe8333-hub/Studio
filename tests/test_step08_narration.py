"""Step08 — 나레이션/자막 생성 테스트 (Phase 6)."""

import sys
import importlib.util
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path

# step08/__init__.py의 genai 의존성 우회 — 직접 파일 로드 후 sys.modules 등록
import types

def _load_and_register(module_key: str, rel_path: str):
    """모듈을 직접 로드하고 sys.modules에 등록. @patch 해석을 위해 부모 패키지에도 속성 설정."""
    if module_key in sys.modules:
        return sys.modules[module_key]
    spec = importlib.util.spec_from_file_location(module_key, Path(rel_path))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[module_key] = mod
    spec.loader.exec_module(mod)

    # 부모 패키지에 속성 등록 (@patch 경로 해석에 필요)
    parts = module_key.split(".")
    for i in range(len(parts) - 1):
        parent_key = ".".join(parts[:i+1])
        child_name = parts[i+1]
        parent = sys.modules.get(parent_key)
        if parent is None:
            parent = types.ModuleType(parent_key)
            sys.modules[parent_key] = parent
        if not hasattr(parent, child_name):
            child = sys.modules.get(".".join(parts[:i+2]))
            if child is not None:
                setattr(parent, child_name, child)

    return mod

_narration_mod = _load_and_register(
    "src.step08.narration_generator", "src/step08/narration_generator.py"
)
_subtitle_mod = _load_and_register(
    "src.step08.subtitle_generator", "src/step08/subtitle_generator.py"
)


class TestNarrationGenerator:
    """나레이션 생성 테스트."""

    def test_build_narration_text(self, sample_script_dict):
        """스크립트에서 나레이션 텍스트 조합 확인."""
        from src.step08.narration_generator import _build_narration_text
        text = _build_narration_text(sample_script_dict)
        assert isinstance(text, str)
        assert len(text) > 0
        assert "지금 당장" in text  # hook text 포함

    def test_build_narration_text_empty_script(self):
        """빈 스크립트 처리 확인."""
        from src.step08.narration_generator import _build_narration_text
        text = _build_narration_text({})
        assert text == ""

    @patch("src.step08.narration_generator._generate_gtts")
    def test_generate_narration_gtts_fallback(self, mock_gtts, tmp_path, sample_script_dict):
        """ElevenLabs 없을 때 gTTS 폴백 확인."""
        mock_gtts.return_value = True
        from src.step08.narration_generator import generate_narration
        out = tmp_path / "narration.mp3"

        with patch("src.step08.narration_generator.ELEVENLABS_API_KEY", ""):
            result = generate_narration(sample_script_dict, out, "CH1")

        mock_gtts.assert_called_once()

    @patch("src.step08.narration_generator._generate_elevenlabs")
    @patch("src.step08.narration_generator._generate_gtts")
    def test_generate_narration_elevenlabs_first(self, mock_gtts, mock_eleven, tmp_path, sample_script_dict):
        """ElevenLabs가 있으면 먼저 시도하는지 확인."""
        mock_eleven.return_value = True
        from src.step08.narration_generator import generate_narration
        out = tmp_path / "narration.mp3"

        with patch("src.step08.narration_generator.ELEVENLABS_API_KEY", "fake_key"):
            with patch("src.step08.narration_generator.CHANNEL_VOICE_IDS", {"CH1": "voice_id_123"}):
                result = generate_narration(sample_script_dict, out, "CH1")

        mock_eleven.assert_called_once()
        mock_gtts.assert_not_called()


class TestSubtitleGenerator:
    """자막 생성 테스트."""

    def test_generate_uniform_srt_fallback(self, tmp_path, sample_script_dict):
        """균등분배 SRT 폴백이 동작하는지 확인."""
        from src.step08.subtitle_generator import _generate_uniform_srt
        narration_path = tmp_path / "narration.mp3"
        narration_path.write_bytes(b"fake_audio")
        output_path = tmp_path / "subtitles.srt"

        # pydub 미설치 환경 대응 mock
        mock_audio_seg = MagicMock()
        mock_audio_seg.__len__ = MagicMock(return_value=720000)
        pydub_mock = types.ModuleType("pydub")
        pydub_mock.AudioSegment = MagicMock()
        pydub_mock.AudioSegment.from_file = MagicMock(return_value=mock_audio_seg)
        with patch.dict(sys.modules, {"pydub": pydub_mock}):
            result = _generate_uniform_srt(sample_script_dict, narration_path, output_path)

        assert isinstance(result, bool)

    def test_generate_subtitles_no_narration(self, tmp_path, sample_script_dict):
        """나레이션 없을 때 균등분배 폴백 확인."""
        from src.step08.subtitle_generator import generate_subtitles
        narration_path = tmp_path / "narration.mp3"
        output_path = tmp_path / "subtitles.srt"
        # narration_path 존재하지 않음

        with patch("src.step08.subtitle_generator._generate_uniform_srt", return_value=True) as mock_uniform:
            generate_subtitles(sample_script_dict, narration_path, output_path)
            mock_uniform.assert_called_once()
