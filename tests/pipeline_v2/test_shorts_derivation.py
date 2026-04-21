"""쇼츠 자동 파생 단위 테스트"""
import pytest
from unittest.mock import MagicMock, patch
from src.pipeline_v2.shorts_derivation import _select_peak_segments, MIN_CLIP_SEC, MAX_CLIP_SEC, MAX_CLIPS


def test_select_peak_segments_with_peaks():
    peaks = [60, 180, 300, 420, 540]
    total_duration = 600.0
    segments = _select_peak_segments([], total_duration, peaks)
    assert len(segments) <= MAX_CLIPS
    for start, end in segments:
        assert start >= 0
        assert end <= total_duration
        assert end - start >= MIN_CLIP_SEC
        assert end - start <= MAX_CLIP_SEC


def test_select_peak_segments_no_peaks():
    segments = _select_peak_segments([], 600.0, [])
    assert len(segments) == MAX_CLIPS
    for start, end in segments:
        assert start >= 0
        assert end > start


def test_select_peak_segments_short_video():
    segments = _select_peak_segments([], 200.0, [50, 100])
    assert all(end <= 200.0 for _, end in segments)


def test_select_peak_segments_clips_at_max():
    peaks = list(range(60, 600, 60))
    segments = _select_peak_segments([], 600.0, peaks)
    assert len(segments) <= MAX_CLIPS
