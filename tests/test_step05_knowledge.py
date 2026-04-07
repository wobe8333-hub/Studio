"""Step05 knowledge — 3단계 지식 수집 파이프라인 테스트."""

import pytest
from unittest.mock import patch, MagicMock

from src.step05.knowledge.knowledge_package import (
    KnowledgePackage, build_empty_package, package_to_dict,
)


class TestKnowledgePackage:
    """KnowledgePackage 스키마 테스트."""

    def test_build_empty_package(self):
        pkg = build_empty_package("금리 인하", "economy", "CH1")
        assert pkg.topic == "금리 인하"
        assert pkg.category == "economy"
        assert pkg.channel_id == "CH1"
        assert pkg.core_facts == []
        assert pkg.confidence_score == 0.0

    def test_package_to_dict(self):
        pkg = build_empty_package("테스트", "science", "CH6")
        pkg.core_facts = ["팩트 1", "팩트 2"]
        pkg.confidence_score = 0.75
        d = package_to_dict(pkg)
        assert isinstance(d, dict)
        assert d["topic"] == "테스트"
        assert d["confidence_score"] == 0.75
        assert len(d["core_facts"]) == 2

    def test_source_entry(self):
        from src.step05.knowledge.knowledge_package import SourceEntry
        s = SourceEntry(url="https://example.com", title="테스트", source_type="web")
        assert s.reliability == "MED"


class TestStage1Research:
    """Stage 1 AI 초벌 리서치 테스트 (mock)."""

    @patch("src.step05.knowledge.stage1_research._gemini_deep_research")
    @patch("src.step05.knowledge.stage1_research.search_topic")
    @patch("src.step05.knowledge.stage1_research.research_topic")
    def test_stage1_with_mocks(self, mock_perplexity, mock_tavily, mock_gemini):
        """모든 API mock 시 stage1_research가 동작하는지 확인."""
        mock_tavily.return_value = {
            "results": [{"title": "뉴스", "url": "http://a.com", "content": "금리가 하락했다. 경제에 영향을 미친다."}],
            "answer": "금리 인하는 경제 성장을 촉진합니다.",
            "ok": True,
        }
        mock_perplexity.return_value = {"summary": "금리 인하 핵심 정보", "citations": [], "ok": True}
        mock_gemini.return_value = {"facts": ["팩트 1", "팩트 2", "팩트 3"], "ok": True}

        from src.step05.knowledge.stage1_research import stage1_research
        pkg = build_empty_package("금리 인하", "economy", "CH1")
        result = stage1_research(pkg)

        assert result.stage1_ok is True
        assert len(result.core_facts) > 0
        assert result.confidence_score > 0

    def test_stage1_graceful_failure(self):
        """모든 API 실패 시도 crash 없이 처리되는지 확인."""
        from src.step05.knowledge.stage1_research import stage1_research
        with patch("src.step05.knowledge.stage1_research.search_topic", side_effect=Exception("API down")):
            with patch("src.step05.knowledge.stage1_research.research_topic", side_effect=Exception("API down")):
                with patch("src.step05.knowledge.stage1_research._gemini_deep_research", side_effect=Exception("API down")):
                    pkg = build_empty_package("테스트", "history", "CH7")
                    result = stage1_research(pkg)
                    assert isinstance(result, KnowledgePackage)


class TestStage3Factcheck:
    """Stage 3 팩트체크 테스트."""

    @patch("src.step05.knowledge.stage3_factcheck._gemini_factcheck")
    def test_stage3_with_facts(self, mock_factcheck):
        """팩트가 있을 때 Stage 3 실행 확인."""
        mock_factcheck.return_value = {
            "verified_facts": ["검증된 팩트 1", "검증된 팩트 2"],
            "flagged": [],
            "ok": True,
        }
        from src.step05.knowledge.stage3_factcheck import stage3_factcheck
        pkg = build_empty_package("테스트 주제", "science", "CH6")
        pkg.core_facts = ["원본 팩트 1", "원본 팩트 2"]
        pkg.confidence_score = 0.5

        result = stage3_factcheck(pkg)
        assert result.stage3_ok is True
        assert len(result.core_facts) > 0
        assert result.confidence_score > 0.5


class TestCategoryEnricher:
    """카테고리별 보강 테스트."""

    def test_enrich_by_category_all_categories(self):
        """7개 카테고리 모두 보강 함수가 crash 없이 실행되는지 확인."""
        from src.step05.knowledge.category_enricher import enrich_by_category

        categories = ["economy", "realestate", "psychology", "mystery", "war_history", "science", "history"]
        for cat in categories:
            pkg = build_empty_package(f"{cat} 주제", cat, "CH1")
            # crash 없어야 함
            result = enrich_by_category(pkg)
            assert isinstance(result, KnowledgePackage)


class TestCollectLayer2YouTubeKeywords:
    """Layer2 YouTube 수집이 keywords를 사용하는지 검증."""

    def test_layer2_uses_keywords_not_raw_titles(self):
        """YouTube raw 제목 대신 정제된 keywords가 수집 결과에 포함되어야 함."""
        from unittest.mock import patch
        from src.step05.trend_collector import _collect_layer2

        mock_yt = {
            "configured": True,
            "topics": ["[한국경제TV LIVE] 금리 인상 긴급 분석", "주식 전망 #shorts"],
            "keywords": ["금리", "주식"],
            "scores": {"금리": 0.9, "주식": 0.7},
        }
        mock_rss = ({"금리": 0.5}, [])  # fetch_news_context 반환 형식

        with patch("src.step05.sources.youtube_trending.fetch_youtube_trending",
                   return_value=mock_yt), \
             patch("src.step05.sources.rss.fetch_news_context",
                   return_value=mock_rss):
            result = _collect_layer2("economy")

        # raw 제목이 포함되면 안 됨
        assert "[한국경제TV LIVE] 금리 인상 긴급 분석" not in result["topics"]
        assert "#shorts" not in " ".join(result["topics"])

        # 정제된 키워드가 포함되어야 함
        assert "금리" in result["topics"] or "주식" in result["topics"]

        # YouTube scores가 news_scores에 반영되어야 함
        assert result["news_scores"].get("금리") == 0.9 or \
               result["news_scores"].get("주식") == 0.7

    def test_layer2_news_scores_enable_interest_calculation(self):
        """news_scores가 있으면 interest_score가 0보다 커야 함."""
        from unittest.mock import patch
        from src.step05.trend_collector import collect_trends

        mock_yt = {
            "configured": True,
            "topics": ["[라이브] 경제 뉴스"],
            "keywords": ["금리"],
            "scores": {"금리": 0.8},
        }
        mock_google = {"demand_score": {}, "pytrends_available": False, "error": None}

        with patch("src.step05.sources.youtube_trending.fetch_youtube_trending",
                   return_value=mock_yt), \
             patch("src.step05.sources.google_trends.fetch_trends_scores",
                   return_value=mock_google), \
             patch("src.step05.sources.naver.fetch_naver_trends",
                   return_value={"topics": []}), \
             patch("src.step05.sources.reddit.fetch_reddit_topics",
                   return_value={"configured": False}), \
             patch("src.step05.sources.community.fetch_community_topics",
                   return_value={"topics": []}), \
             patch("src.step05.trend_collector.deduplicate_topics",
                   side_effect=lambda ch, topics, **kw: topics):

            results = collect_trends("CH1", "economy", limit=5)

        # 금리 주제가 수집됐으면 점수가 0보다 높아야 함
        matched = [r for r in results if r.get("topic") == "금리"]
        if matched:
            assert matched[0]["score"] > 52.5, \
                f"interest_score 연결 안 됨: score={matched[0]['score']}"
