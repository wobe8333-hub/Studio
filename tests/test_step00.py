"""Step00 — 채널 레지스트리 7채널 초기화 테스트."""

import pytest
from src.step00.channel_registry import get_channel, get_active_channels, _ORDER as _ALL_CHANNELS
from src.core.config import CHANNEL_CATEGORIES, CHANNEL_CATEGORY_KO


def test_all_channels_defined():
    """7개 채널이 모두 정의되어 있는지 확인."""
    assert len(_ALL_CHANNELS) == 7
    for ch in ["CH1", "CH2", "CH3", "CH4", "CH5", "CH6", "CH7"]:
        assert ch in _ALL_CHANNELS


def test_channel_categories_complete():
    """7채널 카테고리 매핑이 완전한지 확인."""
    expected = {
        "CH1": "economy",
        "CH2": "realestate",
        "CH3": "psychology",
        "CH4": "mystery",
        "CH5": "war_history",
        "CH6": "science",
        "CH7": "history",
    }
    for ch, cat in expected.items():
        assert CHANNEL_CATEGORIES[ch] == cat, f"{ch} 카테고리 불일치: {CHANNEL_CATEGORIES[ch]} != {cat}"


def test_channel_category_ko_complete():
    """한국어 카테고리명이 7채널 모두 정의되어 있는지 확인."""
    for ch in ["CH1", "CH2", "CH3", "CH4", "CH5", "CH6", "CH7"]:
        assert ch in CHANNEL_CATEGORY_KO
        assert len(CHANNEL_CATEGORY_KO[ch]) > 0


def test_get_channel_returns_dict():
    """get_channel()이 dict를 반환하는지 확인."""
    for ch in ["CH1", "CH2", "CH3", "CH4", "CH5", "CH6", "CH7"]:
        result = get_channel(ch)
        assert isinstance(result, dict)


def test_get_active_channels():
    """get_active_channels()가 리스트를 반환하는지 확인."""
    active = get_active_channels(month_number=1)
    assert isinstance(active, list)
    assert len(active) >= 1
