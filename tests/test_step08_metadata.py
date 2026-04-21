"""Step08 metadata_generator — chapter_markers description 삽입 테스트."""
import json
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest


def _load_metadata_generator():
    import importlib.util, sys, types

    # 구 SDK 모킹 (하위 호환)
    if "google.generativeai" not in sys.modules:
        import google as _g
        m = types.ModuleType("google.generativeai")
        m.configure = lambda **kw: None
        m.GenerativeModel = MagicMock()
        m.GenerationConfig = MagicMock()
        sys.modules["google.generativeai"] = m
        setattr(_g, "generativeai", m)

    # gemini_quota 모킹
    if "src.quota.gemini_quota" not in sys.modules:
        fake = types.ModuleType("src.quota.gemini_quota")
        fake.throttle_if_needed = lambda: None
        fake.record_request = lambda: None
        sys.modules["src.quota.gemini_quota"] = fake

    spec = importlib.util.spec_from_file_location(
        "metadata_generator",
        Path(__file__).parent.parent / "src" / "step08" / "metadata_generator.py",
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _make_mock_genai_client(tag_text: str = "태그1, 태그2, 태그3"):
    """google.genai.Client 모킹 헬퍼 — patch 컨텍스트 안에서 사용."""
    mock_resp = MagicMock()
    mock_resp.text = tag_text
    mock_client = MagicMock()
    mock_client.models.generate_content.return_value = mock_resp
    return mock_client


meta_gen = _load_metadata_generator()


class TestChapterMarkersInDescription:
    """generate_metadata가 chapter_markers를 description에 삽입해야 한다."""

    def _make_script_with_chapters(self) -> dict:
        return {
            "title_candidates": ["테스트 제목"],
            "seo": {
                "description_first_2lines": "설명 첫 두 줄 내용입니다.",
                "chapter_markers": [
                    {"time": "00:00", "title": "인트로"},
                    {"time": "01:30", "title": "본론 시작"},
                    {"time": "04:00", "title": "핵심 내용"},
                    {"time": "07:30", "title": "결론"},
                    {"time": "10:00", "title": "마무리"},
                ],
            },
            "affiliate_insert": {"text": "관련 링크"},
            "financial_disclaimer": "투자 주의 문구",
            "ai_label": "AI 제작 참여",
            "sections": [],
            "video_spec": {},
            "target_duration_sec": 720,
        }

    def test_chapter_markers_in_description_file(self, tmp_path):
        """description.txt에 00:00 형식의 챕터 마커가 포함되어야 한다."""
        script = self._make_script_with_chapters()
        topic = {"title": "테스트 주제"}

        mock_client = _make_mock_genai_client("태그1, 태그2, 태그3")
        with patch("google.genai.Client", return_value=mock_client):
            meta_gen.generate_metadata("CH1", "run_CH1_test", script, tmp_path, topic)

        desc_path = tmp_path / "description.txt"
        assert desc_path.exists(), "description.txt가 생성되지 않음"

        content = desc_path.read_text(encoding="utf-8")
        assert "00:00" in content, \
            "description.txt에 챕터 마커(00:00)가 없음 — generate_metadata가 chapter_markers를 삽입해야 한다"
        assert "인트로" in content, "챕터 마커 제목 '인트로'가 description에 없음"

    def test_description_without_chapters_still_works(self, tmp_path):
        """chapter_markers가 없는 스크립트도 정상 처리되어야 한다."""
        script = {
            "title_candidates": ["제목"],
            "seo": {"description_first_2lines": "설명"},
            "affiliate_insert": {"text": ""},
            "financial_disclaimer": "",
            "ai_label": "AI 제작",
            "sections": [],
            "video_spec": {},
            "target_duration_sec": 720,
        }
        topic = {"title": "주제"}

        mock_client = _make_mock_genai_client("태그1, 태그2")
        with patch("google.genai.Client", return_value=mock_client):
            meta_gen.generate_metadata("CH1", "run_CH1_test", script, tmp_path, topic)

        assert (tmp_path / "description.txt").exists()
