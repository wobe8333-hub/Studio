"""pytest 공통 픽스처 — mock API, 테스트 데이터, 임시 디렉토리."""

import sys
import types
import pytest
import tempfile
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

# ── 외부 의존성 사전 mock 등록 ──────────────────────────────────────────────
# google.generativeai: step08 → script_generator 임포트 체인을 통해 필요
if "google.generativeai" not in sys.modules:
    import google as _google_pkg
    _genai_mock = types.ModuleType("google.generativeai")
    _genai_mock.configure = MagicMock()
    _genai_mock.GenerativeModel = MagicMock()
    _genai_mock.GenerationConfig = MagicMock(return_value={})
    sys.modules["google.generativeai"] = _genai_mock
    setattr(_google_pkg, "generativeai", _genai_mock)

# diskcache: gemini_cache 임포트 체인을 통해 필요
if "diskcache" not in sys.modules:
    _dc_mock = types.ModuleType("diskcache")
    _dc_mock.Cache = MagicMock(return_value=MagicMock(
        get=MagicMock(return_value=None),
        set=MagicMock(),
        expire=MagicMock(return_value=0),
    ))
    sys.modules["diskcache"] = _dc_mock

# sentry_sdk: pipeline.py 임포트에 필요
if "sentry_sdk" not in sys.modules:
    _sentry_mock = types.ModuleType("sentry_sdk")
    _sentry_mock.init = MagicMock()
    sys.modules["sentry_sdk"] = _sentry_mock


# ── src.step08 패키지 사전 임포트 ─────────────────────────────────────────────
# test_step08_narration.py 등이 _load_and_register()에서 가짜 src.step08 부모를
# sys.modules에 등록하기 전에 실제 패키지를 먼저 올려둔다.
# (conftest.py는 모든 테스트 모듈 로드 전에 실행되므로 여기서 선점하는 것이 안전함)
try:
    import src.step08  # noqa: F401
except Exception:
    pass

# gemini_cache._CACHE 원본 참조 저장 (test_cache.py reload 후 복원용)
try:
    import src.cache.gemini_cache as _gemini_cache_mod
    _original_cache = _gemini_cache_mod._CACHE
except Exception:
    _gemini_cache_mod = None
    _original_cache = None


@pytest.fixture(autouse=True)
def _restore_gemini_cache_after_test():
    """각 테스트 후 gemini_cache._CACHE를 원본 mock으로 복원.

    test_cache.py가 importlib.reload()로 _CACHE를 MagicMock으로 교체하면
    이후 테스트에서 cache.get()이 None 대신 MagicMock을 반환하여
    test_e2e.py의 generate_script가 MagicMock을 JSON 직렬화하려다 실패한다.
    """
    yield
    if _gemini_cache_mod is not None and _original_cache is not None:
        _gemini_cache_mod._CACHE = _original_cache


@pytest.fixture
def tmp_dir(tmp_path):
    """임시 작업 디렉토리."""
    return tmp_path


@pytest.fixture
def sample_topic_dict():
    """샘플 트렌드 주제 dict."""
    return {
        "original_topic": "금리 인하의 경제적 영향",
        "reinterpreted_title": "금리 인하의 경제적 영향의 작동 원리와 내 돈에 미치는 영향",
        "category": "economy",
        "channel_id": "CH1",
        "is_trending": True,
        "score": 85.0,
        "grade": "auto",
        "topic_type": "trending",
        "trend_validity_days": 7,
    }


@pytest.fixture
def sample_script_dict():
    """샘플 스크립트 dict (CH1 경제)."""
    return {
        "channel_id": "CH1",
        "run_id": "test_run_001",
        "title_candidates": ["금리 인하의 비밀", "당신의 돈이 달라진다"],
        "hook": {
            "text": "지금 당장 이 영상을 보지 않으면 손해입니다!",
            "duration_estimate_sec": 20,
            "animation_preview_at_sec": 8,
        },
        "promise": "금리 인하가 내 지갑에 미치는 영향을 알아봅니다",
        "sections": [
            {
                "id": 0,
                "heading": "금리란 무엇인가",
                "narration_text": "금리는 돈을 빌리는 대가로 지불하는 비용입니다. " * 10,
                "animation_prompt": "animated chart showing interest rate",
                "animation_style": "comparison",
                "render_tool": "manim",
                "chapter_title": "금리 기초",
                "character_directions": {"expression": "explaining", "pose": "pointing"},
            }
        ] * 6,
        "affiliate_insert": {
            "click_rate_applied": 0.003,
            "purchase_rate_applied": 0.01,
        },
        "seo": {
            "primary_keyword": "금리",
            "secondary_keywords": ["인플레이션", "재테크"],
            "chapter_markers": ["00:00 인트로", "01:30 금리 기초", "03:00 영향", "05:00 전망", "07:00 결론"],
        },
        "cta": {"text": "구독과 좋아요 부탁드립니다!", "like_cta_at_sec": 55},
        "target_duration_sec": 720,
        "ai_label": "이 영상은 AI가 제작에 참여했습니다.",
        "financial_disclaimer": "본 영상은 교육 목적이며 투자 조언을 대체하지 않습니다.",
        "is_trending": True,
    }


@pytest.fixture
def mock_gemini():
    """Gemini API mock."""
    with patch("google.generativeai.GenerativeModel") as mock:
        mock_model = MagicMock()
        mock_resp = MagicMock()
        mock_resp.text = '{"title_candidates": ["테스트 제목"], "hook": {"text": "훅", "animation_preview_at_sec": 8}, "promise": "약속", "sections": [], "affiliate_insert": {"purchase_rate_applied": 0.01}, "ai_label": "AI 제작", "financial_disclaimer": "투자 주의"}'
        mock_model.generate_content.return_value = mock_resp
        mock.return_value = mock_model
        yield mock


@pytest.fixture
def mock_knowledge_dir(tmp_path, monkeypatch):
    """임시 knowledge_store 디렉토리."""
    knowledge_dir = tmp_path / "knowledge_store"
    knowledge_dir.mkdir()
    monkeypatch.setattr("src.core.config.KNOWLEDGE_DIR", knowledge_dir)
    return knowledge_dir


@pytest.fixture
def mock_channels_dir(tmp_path, monkeypatch):
    """임시 channels 디렉토리."""
    channels_dir = tmp_path / "channels"
    channels_dir.mkdir()
    for ch in ["CH1", "CH2", "CH3", "CH4", "CH5", "CH6", "CH7"]:
        (channels_dir / ch).mkdir()
    monkeypatch.setattr("src.core.config.CHANNELS_DIR", channels_dir)
    return channels_dir
