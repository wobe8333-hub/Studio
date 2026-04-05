"""Analytics & Learning Agent 테스트."""
import pytest


def test_compute_algorithm_stage_algorithm_active():
    """views >= 100,000 이면 ALGORITHM-ACTIVE를 반환한다."""
    from src.agents.analytics_learning.kpi_analyzer import compute_algorithm_stage
    kpi = {"views": 150_000, "ctr": 4.0, "avg_view_percentage": 40.0, "browse_feed_percentage": 10.0}
    assert compute_algorithm_stage(kpi) == "ALGORITHM-ACTIVE"


def test_compute_algorithm_stage_browse_entry():
    """CTR>=5.5, AVP>=45, browse>=20 이면 BROWSE-ENTRY를 반환한다."""
    from src.agents.analytics_learning.kpi_analyzer import compute_algorithm_stage
    kpi = {"views": 5_000, "ctr": 5.8, "avg_view_percentage": 47.0, "browse_feed_percentage": 22.0}
    assert compute_algorithm_stage(kpi) == "BROWSE-ENTRY"


def test_compute_algorithm_stage_search_only():
    """CTR 4~5.5 이면 SEARCH-ONLY를 반환한다."""
    from src.agents.analytics_learning.kpi_analyzer import compute_algorithm_stage
    kpi = {"views": 1_000, "ctr": 4.5, "avg_view_percentage": 38.0, "browse_feed_percentage": 5.0}
    assert compute_algorithm_stage(kpi) == "SEARCH-ONLY"


def test_compute_algorithm_stage_pre_entry():
    """CTR < 4 이면 PRE-ENTRY를 반환한다."""
    from src.agents.analytics_learning.kpi_analyzer import compute_algorithm_stage
    kpi = {"views": 200, "ctr": 2.1, "avg_view_percentage": 30.0, "browse_feed_percentage": 0.0}
    assert compute_algorithm_stage(kpi) == "PRE-ENTRY"


def test_is_winning_true_when_both_criteria_met():
    from src.agents.analytics_learning.pattern_extractor import is_winning
    assert is_winning({"ctr": 6.5, "avg_view_percentage": 52.0}) is True


def test_is_winning_false_when_only_one_criterion_met():
    from src.agents.analytics_learning.pattern_extractor import is_winning
    assert is_winning({"ctr": 7.0, "avg_view_percentage": 45.0}) is False
    assert is_winning({"ctr": 5.0, "avg_view_percentage": 55.0}) is False


def test_update_winning_patterns_keeps_last_50(tmp_path):
    import json
    memory_path = tmp_path / "memory.json"
    existing = [{"run_id": f"run_{i:03d}", "ctr": 6.0, "avp": 51.0} for i in range(50)]
    memory_path.write_text(
        json.dumps({"winning_animation_patterns": existing}, ensure_ascii=True),
        encoding="utf-8-sig"
    )
    from src.agents.analytics_learning.pattern_extractor import update_winning_patterns
    update_winning_patterns(memory_path, {
        "run_id": "run_new", "channel_id": "CH1",
        "animation_style": "comparison", "ctr": 7.0, "avp": 55.0
    })
    from src.core.ssot import read_json
    updated = read_json(memory_path)
    patterns = updated["winning_animation_patterns"]
    assert len(patterns) == 50
    assert patterns[-1]["run_id"] == "run_new"


def test_promote_if_eligible_advances_stage(tmp_path):
    import json
    policy_path = tmp_path / "algorithm_policy.json"
    policy_path.write_text(
        json.dumps({"algorithm_stage": "PRE-ENTRY"}, ensure_ascii=True),
        encoding="utf-8-sig"
    )
    from src.agents.analytics_learning.phase_promoter import promote_if_eligible
    promoted = promote_if_eligible(policy_path, "SEARCH-ONLY")
    assert promoted is True
    from src.core.ssot import read_json
    assert read_json(policy_path)["algorithm_stage"] == "SEARCH-ONLY"


def test_promote_if_eligible_blocks_demotion(tmp_path):
    import json
    policy_path = tmp_path / "algorithm_policy.json"
    policy_path.write_text(
        json.dumps({"algorithm_stage": "BROWSE-ENTRY"}, ensure_ascii=True),
        encoding="utf-8-sig"
    )
    from src.agents.analytics_learning.phase_promoter import promote_if_eligible
    promoted = promote_if_eligible(policy_path, "SEARCH-ONLY")
    assert promoted is False
    from src.core.ssot import read_json
    assert read_json(policy_path)["algorithm_stage"] == "BROWSE-ENTRY"


def test_select_winner_returns_highest_ctr_mode():
    from src.agents.analytics_learning.ab_selector import select_winner
    variant = {"authority_ctr": 4.2, "curiosity_ctr": 6.8, "benefit_ctr": 3.5}
    assert select_winner(variant) == "curiosity"


def test_select_winner_defaults_to_curiosity_when_all_zero():
    from src.agents.analytics_learning.ab_selector import select_winner
    variant = {"authority_ctr": 0.0, "curiosity_ctr": 0.0, "benefit_ctr": 0.0}
    assert select_winner(variant) == "curiosity"
