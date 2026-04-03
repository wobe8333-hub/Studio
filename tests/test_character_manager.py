"""Step08 — 캐릭터 매니저 테스트 (Phase 5)."""

import sys
import importlib.util
from pathlib import Path
import pytest

# step08/__init__.py의 genai 의존성 우회
spec = importlib.util.spec_from_file_location(
    "character_manager",
    Path("src/step08/character_manager.py"),
)
_mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(_mod)
CHARACTER_PROFILES = _mod.CHARACTER_PROFILES
build_character_prompt = _mod.build_character_prompt
get_character_name = _mod.get_character_name
EXPRESSION_MODIFIERS = _mod.EXPRESSION_MODIFIERS
POSE_MODIFIERS = _mod.POSE_MODIFIERS


class TestCharacterManager:
    """채널별 캐릭터 관리 테스트."""

    def test_all_channels_have_profiles(self):
        """7채널 모두 캐릭터 프로필이 있는지 확인."""
        for ch in ["CH1", "CH2", "CH3", "CH4", "CH5", "CH6", "CH7"]:
            assert ch in CHARACTER_PROFILES
            profile = CHARACTER_PROFILES[ch]
            assert "name" in profile
            assert "base_prompt" in profile
            assert "seed" in profile

    def test_unique_seeds(self):
        """각 채널의 시드가 고유한지 확인 (캐릭터 일관성)."""
        seeds = [p["seed"] for p in CHARACTER_PROFILES.values()]
        assert len(seeds) == len(set(seeds)), "중복 시드 발견"

    def test_build_character_prompt_structure(self):
        """build_character_prompt()가 올바른 구조 반환 확인."""
        result = build_character_prompt("CH1", "happy", "pointing", "금리 설명")
        assert "positive" in result
        assert "negative" in result
        assert "seed" in result
        assert isinstance(result["positive"], str)
        assert len(result["positive"]) > 20

    def test_build_character_prompt_all_channels(self):
        """7채널 모두에 대해 프롬프트 생성 확인."""
        for ch in ["CH1", "CH2", "CH3", "CH4", "CH5", "CH6", "CH7"]:
            result = build_character_prompt(ch, "thinking", "explaining")
            assert len(result["positive"]) > 0

    def test_expression_modifiers_defined(self):
        """표정 수식어가 정의되어 있는지 확인."""
        required = ["happy", "surprised", "thinking", "sad", "excited", "curious", "explaining"]
        for expr in required:
            assert expr in EXPRESSION_MODIFIERS

    def test_pose_modifiers_defined(self):
        """포즈 수식어가 정의되어 있는지 확인."""
        required = ["standing", "pointing", "explaining", "sitting", "waving"]
        for pose in required:
            assert pose in POSE_MODIFIERS

    def test_get_character_name(self):
        """채널별 캐릭터 이름 반환 확인."""
        name = get_character_name("CH1")
        assert isinstance(name, str)
        assert len(name) > 0

    def test_unknown_channel_fallback(self):
        """미정의 채널 → CH1 폴백 확인."""
        result = build_character_prompt("CH99", "happy", "standing")
        # CH1 프로필로 폴백
        assert len(result["positive"]) > 0
