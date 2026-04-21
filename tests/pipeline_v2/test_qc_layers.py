"""QC 레이어 단위 테스트 (Layer 1~5)"""
import pytest
from unittest.mock import MagicMock, patch
from src.pipeline_v2.episode_schema import EpisodeMeta
from src.pipeline_v2.qc.layer1_character import (
    PASS_THRESHOLD,
    RETRY_THRESHOLD,
    compute_consistency_score,
)
from src.pipeline_v2.qc.layer3_sync import _srt_time_to_sec, _load_srt
from src.pipeline_v2.qc.layer5_meta import run_layer5, TITLE_MIN_LEN


def _make_meta(channel_id: str = "CH1") -> EpisodeMeta:
    return EpisodeMeta(episode_id="CH1_TEST_001", channel_id=channel_id, series_id="s1", episode_index=1)


# ── Layer 1 ──────────────────────────────────────────────────

@patch("src.pipeline_v2.qc.layer1_character._score_vision_gemini", return_value=0.9)
@patch("src.pipeline_v2.qc.layer1_character._score_clip_similarity", return_value=0.88)
@patch("src.pipeline_v2.qc.layer1_character._score_orb_matching", return_value=0.85)
def test_compute_consistency_score_pass(mock_orb, mock_clip, mock_vis):
    score, detail = compute_consistency_score("img.png", "ref.png")
    assert score >= PASS_THRESHOLD
    assert "vision" in detail
    assert "clip" in detail
    assert "orb" in detail
    assert "composite" in detail


@patch("src.pipeline_v2.qc.layer1_character._score_vision_gemini", return_value=0.6)
@patch("src.pipeline_v2.qc.layer1_character._score_clip_similarity", return_value=0.6)
@patch("src.pipeline_v2.qc.layer1_character._score_orb_matching", return_value=0.5)
def test_compute_consistency_score_fail(mock_orb, mock_clip, mock_vis):
    score, _ = compute_consistency_score("img.png", "ref.png")
    assert score < PASS_THRESHOLD


def test_composite_weight_formula():
    v, c, o = 0.9, 0.8, 0.7
    expected = 0.5 * v + 0.3 * c + 0.2 * o
    with patch("src.pipeline_v2.qc.layer1_character._score_vision_gemini", return_value=v), \
         patch("src.pipeline_v2.qc.layer1_character._score_clip_similarity", return_value=c), \
         patch("src.pipeline_v2.qc.layer1_character._score_orb_matching", return_value=o):
        score, _ = compute_consistency_score("a.png", "b.png")
    assert abs(score - expected) < 1e-6


# ── Layer 3 ──────────────────────────────────────────────────

def test_srt_time_to_sec_basic():
    assert _srt_time_to_sec("00:01:00,000") == 60.0
    assert _srt_time_to_sec("01:00:00,000") == 3600.0
    assert _srt_time_to_sec("00:00:30,500") == pytest.approx(30.5, abs=0.01)


def test_load_srt_missing_file(tmp_path):
    result = _load_srt(tmp_path / "nonexistent.srt")
    assert result == []


def test_load_srt_valid(tmp_path):
    srt = tmp_path / "test.srt"
    srt.write_text(
        "1\n00:00:01,000 --> 00:00:03,000\n안녕하세요\n\n"
        "2\n00:00:04,000 --> 00:00:06,000\n테스트입니다\n\n",
        encoding="utf-8",
    )
    entries = _load_srt(srt)
    assert len(entries) == 2
    assert entries[0]["text"] == "안녕하세요"
    assert entries[1]["start"] == pytest.approx(4.0)


# ── Layer 5 ──────────────────────────────────────────────────

def test_layer5_passes_complete_meta():
    meta = _make_meta()
    upload_meta = {
        "title": "금리가 오르면 어떻게 되나요? 경제 완전 정복",
        "description": "이 영상에서는 금리 인상이 경제에 미치는 영향을 쉽게 설명합니다. " * 5,
        "tags": ["경제", "금리", "인플레이션", "투자", "재테크", "주식", "부동산"],
        "thumbnail_prompts": ["variant1", "variant2", "variant3"],
        "category_id": "22",
    }
    result = run_layer5(meta, upload_meta)
    assert result["passed"] is True
    assert result["issues"] == []


def test_layer5_fails_short_title():
    meta = _make_meta()
    upload_meta = {
        "title": "경제",
        "description": "x" * 200,
        "tags": ["a", "b", "c", "d", "e"],
        "thumbnail_prompts": ["a", "b", "c"],
        "category_id": "22",
    }
    result = run_layer5(meta, upload_meta)
    assert not result["passed"]
    assert any("제목" in i for i in result["issues"])


def test_layer5_fails_no_thumbnails():
    meta = _make_meta()
    upload_meta = {
        "title": "경제 완전 정복 금리 인플레이션 투자 재테크",
        "description": "x" * 200,
        "tags": ["a", "b", "c", "d", "e"],
        "thumbnail_prompts": ["only_one"],
        "category_id": "22",
    }
    result = run_layer5(meta, upload_meta)
    assert not result["passed"]
    assert any("썸네일" in i for i in result["issues"])
