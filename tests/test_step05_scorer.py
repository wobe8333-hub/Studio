"""Step05 — 트렌드 점수화 알고리즘 테스트."""

import pytest
from src.step05.scorer import score_topic


def test_score_topic_returns_dict():
    """score_topic()이 올바른 dict 구조를 반환하는지 확인."""
    result = score_topic(
        topic="금리 인하",
        category="economy",
        trends_score=0.7,
        news_score=0.6,
        community_score=0.5,
    )
    assert isinstance(result, dict)
    assert "topic" in result
    assert "score" in result
    assert "grade" in result
    assert "category" in result
    assert "breakdown" in result


def test_score_range():
    """점수가 0~100 범위인지 확인."""
    result = score_topic("테스트 주제", "science", 0.5, 0.5, 0.5)
    assert 0 <= result["score"] <= 100


def test_grade_auto_high_score():
    """높은 점수(70+)는 'auto' 등급이어야 함."""
    result = score_topic("초인기 주제", "economy", 1.0, 1.0, 1.0)
    assert result["grade"] == "auto"


def test_grade_review_mid_score():
    """중간 점수(55~69)는 'review' 등급이어야 함."""
    # economy: fit=0.7, revenue=1.0, urgency=1.0(days<=3)
    # interest = trends*0.5 = 0.4*0.5 = 0.2 → interest_score = 0.2*40 = 8
    # total = 8 + 17.5 + 20 + 15 = 60.5 → review (55~69)
    result = score_topic("중간 주제", "economy", 0.4, 0.0, 0.0, days_since_trending=1)
    assert result["grade"] == "review"


def test_grade_rejected_low_score():
    """낮은 점수(<55)는 'rejected' 등급이어야 함."""
    result = score_topic("비인기 주제", "history", 0.0, 0.0, 0.0)
    assert result["grade"] == "rejected"


def test_grade_values_are_valid():
    """grade 값이 허용된 3개 중 하나여야 함."""
    for trends in [0.0, 0.5, 1.0]:
        result = score_topic("주제", "economy", trends, 0.0, 0.0)
        assert result["grade"] in ("auto", "review", "rejected"), \
            f"unexpected grade: {result['grade']} (score={result['score']})"


def test_score_topic_all_categories():
    """7개 카테고리 모두에 대해 점수화가 동작하는지 확인."""
    categories = ["economy", "realestate", "psychology", "mystery", "war_history", "science", "history"]
    for cat in categories:
        result = score_topic(f"{cat} 테스트 주제", cat, 0.5, 0.5, 0.5)
        assert result["category"] == cat
        assert result["grade"] in ("auto", "review", "rejected")


def test_breakdown_keys_present():
    """breakdown에 4개 구성요소가 모두 있어야 함."""
    result = score_topic("주제", "economy", 0.5, 0.5, 0.5)
    assert set(result["breakdown"].keys()) == {"interest", "fit", "revenue", "urgency"}


def test_score_topic_without_external_scores():
    """외부 점수 없이도 동작하는지 확인 (에버그린 주제)."""
    result = score_topic("에버그린 주제", "science", 0.0, 0.0, 0.0)
    assert isinstance(result["score"], float)
    assert result["grade"] in ("auto", "review", "rejected")
