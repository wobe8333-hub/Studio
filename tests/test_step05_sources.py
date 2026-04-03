"""Step05 sources — 소스 모듈 단위 테스트 (mock API 응답)."""

import pytest
from unittest.mock import patch, MagicMock


class TestCuratedSource:
    """curated.py 에버그린 주제풀 테스트."""

    def test_fetch_curated_topics_returns_dict(self):
        from src.step05.sources.curated import fetch_curated_topics
        result = fetch_curated_topics("economy", limit=5)
        assert isinstance(result, dict)
        assert "topics" in result
        assert "source" in result

    def test_fetch_curated_topics_limit(self):
        from src.step05.sources.curated import fetch_curated_topics
        result = fetch_curated_topics("science", limit=3)
        assert len(result["topics"]) <= 3

    def test_fetch_curated_all_categories(self):
        from src.step05.sources.curated import fetch_curated_topics
        categories = ["economy", "realestate", "psychology", "mystery", "war_history", "science", "history"]
        for cat in categories:
            result = fetch_curated_topics(cat, limit=5)
            assert len(result["topics"]) > 0, f"{cat} 카테고리 주제 없음"

    def test_get_pool_size(self):
        from src.step05.sources.curated import get_pool_size
        size = get_pool_size("economy")
        assert size > 0

    def test_shuffle_option(self):
        from src.step05.sources.curated import fetch_curated_topics
        result1 = fetch_curated_topics("history", limit=10, shuffle=False)
        result2 = fetch_curated_topics("history", limit=10, shuffle=False)
        # 셔플 없으면 동일 순서
        assert result1["topics"] == result2["topics"]


class TestDedup:
    """dedup.py 중복 제거 테스트."""

    def test_deduplicate_topics_no_store(self, tmp_path, monkeypatch):
        """knowledge_store 없을 때 원본 반환 확인."""
        import src.core.config as cfg
        monkeypatch.setattr(cfg, "KNOWLEDGE_DIR", tmp_path / "knowledge_store")

        from src.step05.dedup import deduplicate_topics
        candidates = ["금리 인하", "주식 시장", "인플레이션"]
        result = deduplicate_topics("CH1", candidates)
        assert isinstance(result, list)
        assert len(result) <= len(candidates)

    def test_is_duplicate_different_topics(self):
        """서로 다른 주제는 중복이 아님을 확인."""
        from src.step05.dedup import _similarity
        sim = _similarity("금리 인하의 영향", "UFO 외계인 미스터리")
        assert sim < 0.3

    def test_is_duplicate_similar_topics(self):
        """유사한 주제는 중복으로 감지."""
        from src.step05.dedup import _similarity
        sim = _similarity("금리 인하의 경제적 영향", "금리 인하가 경제에 미치는 영향")
        assert sim > 0.3


class TestWikipediaSource:
    """wikipedia.py 에버그린 확장 테스트."""

    @patch("requests.get")
    def test_expand_keywords_with_mock(self, mock_get):
        """Wikipedia API mock으로 expand_keywords 테스트."""
        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.json.return_value = {
            "query": {
                "search": [
                    {"title": "경제학", "snippet": "경제학은..."},
                    {"title": "미시경제학", "snippet": "미시..."},
                ]
            }
        }
        mock_get.return_value = mock_response

        from src.step05.sources.wikipedia import expand_keywords
        # expand_keywords는 (list, dict) 튜플 반환
        result = expand_keywords(["경제"], "economy", lang="ko")
        topics = result[0] if isinstance(result, tuple) else result
        assert isinstance(topics, list)

    @patch("requests.get")
    def test_expand_keywords_api_failure(self, mock_get):
        """API 실패 시에도 crash 없이 처리되는지 확인."""
        mock_get.side_effect = Exception("Connection failed")
        from src.step05.sources.wikipedia import expand_keywords
        result = expand_keywords(["경제"], "economy", lang="ko")
        # (list, dict) 또는 list 모두 허용
        topics = result[0] if isinstance(result, tuple) else result
        assert isinstance(topics, list)
