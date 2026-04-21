"""메타데이터 자동 생성기 단위 테스트"""
import pytest
from src.pipeline_v2.episode_schema import EpisodeMeta
from src.pipeline_v2.meta_generator import generate_upload_meta, _extract_keywords


def _make_meta(channel_id: str = "CH1") -> EpisodeMeta:
    m = EpisodeMeta(episode_id="CH1_TEST_001", channel_id=channel_id, series_id="테스트시리즈", episode_index=1)
    m.features.duration_sec = 480
    return m


def test_extract_keywords_basic():
    script = "금리가 오르면 부동산이 떨어집니다. 금리 인상은 경제에 큰 영향을 줍니다. 경제가 침체되면 금리를 낮춥니다."
    kw = _extract_keywords(script, max_keywords=5)
    assert "금리" in kw
    assert len(kw) <= 5


def test_generate_upload_meta_structure():
    meta = _make_meta("CH1")
    script = "이것은 테스트 스크립트입니다. 금리와 경제에 관한 이야기를 다룹니다. " * 10
    result = generate_upload_meta(meta, "테스트 제목", script, ["thumb1.png", "thumb2.png", "thumb3.png"])

    assert "title" in result
    assert "description" in result
    assert "tags" in result
    assert "thumbnail_prompts" in result
    assert "category_id" in result
    assert len(result["tags"]) >= 5
    assert len(result["description"]) >= 100
    assert len(result["thumbnail_prompts"]) == 3


def test_generate_upload_meta_all_channels():
    script = "테스트 스크립트입니다. " * 20
    for ch in ["CH1", "CH2", "CH3", "CH4", "CH5", "CH6", "CH7"]:
        meta = _make_meta(ch)
        result = generate_upload_meta(meta, f"{ch} 테스트 영상", script, ["a.png", "b.png", "c.png"])
        assert result["category_id"].isdigit()
        assert len(result["tags"]) > 0


def test_card_timestamps_within_duration():
    meta = _make_meta("CH2")
    meta.features.duration_sec = 600
    script = "과학 이야기입니다. " * 20
    result = generate_upload_meta(meta, "과학 테스트", script, ["a.png", "b.png", "c.png"])
    for ts in result["card_timestamps"]:
        assert ts <= 600
