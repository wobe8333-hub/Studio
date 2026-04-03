"""Step08 — SD XL + LoRA 이미지 생성 테스트 (mock)."""

import sys
import importlib.util
import types
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path

# step08/__init__.py genai 우회 — 직접 파일 로드 후 sys.modules 등록
def _load_and_register(module_key: str, rel_path: str):
    if module_key in sys.modules:
        return sys.modules[module_key]
    spec = importlib.util.spec_from_file_location(module_key, Path(rel_path))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[module_key] = mod
    spec.loader.exec_module(mod)
    _register_parents(module_key, mod)
    return mod

def _register_parents(module_key: str, mod):
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

# google.generativeai 미설치 환경 대응 — 가짜 모듈 사전 등록
# 실제 google 네임스페이스 패키지를 먼저 임포트하여 보존 (google.api_core 등 충돌 방지)
if "google.generativeai" not in sys.modules:
    import google as _google_pkg  # 설치된 실제 google 네임스페이스 패키지 확보
    _genai_mock = types.ModuleType("google.generativeai")
    _genai_mock.configure = MagicMock()
    _genai_mock.GenerativeModel = MagicMock()
    _genai_mock.GenerationConfig = MagicMock()
    sys.modules["google.generativeai"] = _genai_mock
    setattr(_google_pkg, "generativeai", _genai_mock)

# character_manager를 먼저 직접 로드해야 sd_generator 로드 시 __init__ 우회 가능
_char_mod     = _load_and_register("src.step08.character_manager", "src/step08/character_manager.py")
_sd_gen_mod   = _load_and_register("src.step08.sd_generator",      "src/step08/sd_generator.py")
_scene_mod    = _load_and_register("src.step08.scene_composer",    "src/step08/scene_composer.py")
_motion_mod   = _load_and_register("src.step08.motion_engine",     "src/step08/motion_engine.py")


class TestSDGenerator:
    """sd_generator.py 테스트."""

    def test_detect_gpu_returns_bool(self):
        """GPU 감지가 bool을 반환하는지 확인."""
        from src.step08.sd_generator import _detect_gpu
        result = _detect_gpu()
        assert isinstance(result, bool)

    def test_generate_scene_images_no_gpu(self, tmp_path, sample_script_dict):
        """GPU 없을 때 이미지 생성 시도 확인 (Gemini 폴백 성공 mock)."""
        sections = [
            {"id": 1, "animation_prompt": "경제 설명", "character_directions": {"expression": "happy", "pose": "explaining"}},
            {"id": 2, "animation_prompt": "금리 인하", "character_directions": {"expression": "thinking", "pose": "standing"}},
        ]
        from src.step08.sd_generator import generate_scene_images

        # Gemini 폴백이 성공하도록 mock — 파일 생성 시뮬레이션
        def _fake_gemini(prompt, out_path):
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_bytes(b"fake_png")
            return True

        with patch("src.step08.sd_generator._generate_gemini_image", side_effect=_fake_gemini):
            results = generate_scene_images("CH1", sections, tmp_path, use_gpu=False)

        assert isinstance(results, list)
        assert len(results) == len(sections)

    def test_generate_scene_images_returns_list(self, tmp_path):
        """generate_scene_images가 list를 반환하는지 확인 (모든 섹션 실패 → 빈 리스트)."""
        sections = [
            {"id": 1, "animation_prompt": "test", "character_directions": {}},
        ]
        from src.step08.sd_generator import generate_scene_images

        with patch("src.step08.sd_generator._generate_gemini_image", return_value=False):
            results = generate_scene_images("CH1", sections, tmp_path, use_gpu=False)

        assert isinstance(results, list)
        # 모두 실패 시 빈 리스트 반환
        assert len(results) == 0

    def test_generate_scene_images_all_channels(self, tmp_path):
        """7채널 모두 generate_scene_images 호출 가능 확인 (Gemini 성공 mock)."""
        sections = [{"id": 1, "animation_prompt": "test", "character_directions": {}}]
        from src.step08.sd_generator import generate_scene_images

        def _fake_gemini(prompt, out_path):
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_bytes(b"fake_png")
            return True

        with patch("src.step08.sd_generator._generate_gemini_image", side_effect=_fake_gemini):
            for ch in ["CH1", "CH2", "CH3", "CH4", "CH5", "CH6", "CH7"]:
                results = generate_scene_images(ch, sections, tmp_path / ch, use_gpu=False)
                assert isinstance(results, list)


class TestSceneComposer:
    """scene_composer.py 테스트."""

    def test_compose_scene_no_images(self, tmp_path):
        """이미지 파일 없을 때 compose_scene이 crash 없이 처리되는지 확인."""
        from src.step08.scene_composer import compose_scene
        char_path = tmp_path / "char.png"
        bg_path = tmp_path / "bg.png"
        out_path = tmp_path / "out.png"
        # 파일 없는 상태로 호출 — 예외 없이 bool 반환
        result = compose_scene(char_path, bg_path, "테스트 자막", out_path)
        assert isinstance(result, bool)


class TestMotionEngine:
    """motion_engine.py 테스트."""

    def test_batch_create_returns_list(self, tmp_path):
        """batch_create_motion_clips가 list를 반환하는지 확인."""
        from src.step08.motion_engine import batch_create_motion_clips
        # 빈 이미지 리스트 → 빈 결과
        results = batch_create_motion_clips([], tmp_path)
        assert isinstance(results, list)
        assert len(results) == 0

    def test_create_motion_clip_no_ffmpeg(self, tmp_path):
        """FFmpeg 실패 시 False 반환 확인."""
        from src.step08.motion_engine import create_motion_clip
        img = tmp_path / "fake.png"
        img.write_bytes(b"not_an_image")
        out = tmp_path / "out.mp4"
        # subprocess.run을 mock — FFmpeg가 실패하더라도 예외 없이 bool 반환
        with patch("src.step08.motion_engine.subprocess.run",
                   return_value=MagicMock(returncode=1, stderr="ffmpeg error")):
            result = create_motion_clip(img, out, duration_sec=1.0)
        assert isinstance(result, bool)
        assert result is False
