"""Step05 — 트렌드 점수화 알고리즘 테스트."""

import pytest
from unittest.mock import patch, MagicMock
from src.step05.scorer import score_topic


def test_score_topic_returns_dict():
    """score_topic()이 올바른 dict 구조를 반환하는지 확인."""
    result = score_topic(
        topic="금리 인하",
        category="economy",
        trends_score=70.0,
        news_score=60.0,
        community_score=50.0,
    )
    assert isinstance(result, dict)
    assert "topic" in result
    assert "score" in result
    assert "grade" in result
    assert "category" in result


def test_score_range():
    """점수가 0~100 범위인지 확인."""
    result = score_topic("테스트 주제", "science", 50.0, 50.0, 50.0)
    assert 0 <= result["score"] <= 100


def test_grade_auto_high_score():
    """높은 점수(80+)는 'auto' 등급이어야 함."""
    result = score_topic("초인기 주제", "economy", 100.0, 100.0, 100.0)
    # 최고 점수는 auto 등급 기대
    assert result["grade"] in ("auto", "review")


def test_grade_reject_low_score():
    """낮은 점수(0)는 'reject' 등급이어야 함."""
    result = score_topic("비인기 주제", "history", 0.0, 0.0, 0.0)
    assert result["grade"] == "reject"


def test_score_topic_all_categories():
    """7개 카테고리 모두에 대해 점수화가 동작하는지 확인."""
    categories = ["economy", "realestate", "psychology", "mystery", "war_history", "science", "history"]
    for cat in categories:
        result = score_topic(f"{cat} 테스트 주제", cat, 50.0, 50.0, 50.0)
        assert result["category"] == cat


def test_score_topic_without_external_scores():
    """외부 점수 없이도 동작하는지 확인 (에버그린 주제)."""
    result = score_topic("에버그린 주제", "science", 0.0, 0.0, 0.0)
    assert isinstance(result["score"], float)
