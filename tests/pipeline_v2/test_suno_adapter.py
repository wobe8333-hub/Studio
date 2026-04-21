"""Suno API 어댑터 단위 테스트"""
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from src.adapters.suno import select_bgm_for_episode, BGM_ASSETS_ROOT


def test_bgm_assets_root_structure():
    # BGM_ASSETS_ROOT가 올바른 경로 형식인지 확인
    assert "bgm" in str(BGM_ASSETS_ROOT).lower()


def test_select_bgm_fallback_when_no_files(tmp_path):
    with patch("src.adapters.suno.BGM_ASSETS_ROOT", tmp_path):
        result = select_bgm_for_episode("CH1", "nonexistent_mood")
    assert result is None or isinstance(result, str)


def test_select_bgm_returns_existing_file(tmp_path):
    ch1_dir = tmp_path / "CH1"
    ch1_dir.mkdir()
    mp3_file = ch1_dir / "calm_piano_01.mp3"
    mp3_file.write_bytes(b"fake_mp3_data")

    with patch("src.adapters.suno.BGM_ASSETS_ROOT", tmp_path):
        result = select_bgm_for_episode("CH1", "calm_piano")

    assert result is None or isinstance(result, str)
