"""Video Style & Character Agent 테스트."""
import json
from pathlib import Path
import pytest


def _write_qa_result(path: Path, consistency_score: float) -> None:
    """테스트용 qa_result.json을 생성한다."""
    path.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "vision_qa": {"character_consistency_score": consistency_score},
        "overall_pass": consistency_score >= 0.7
    }
    path.write_text(json.dumps(data, ensure_ascii=True), encoding="utf-8-sig")


def test_check_character_drift_detects_low_score(tmp_path):
    """평균 일관성 점수 < 0.7 이면 drift_detected=True를 반환한다."""
    for i in range(5):
        _write_qa_result(
            tmp_path / "CH1" / f"run_{i:03d}" / "step11" / "qa_result.json",
            0.5
        )
    from src.agents.video_style.character_monitor import check_character_drift
    result = check_character_drift(tmp_path, "CH1")
    assert result["drift_detected"] is True
    assert result["avg_score"] < 0.7


def test_check_character_drift_no_drift_when_consistent(tmp_path):
    """평균 일관성 점수 >= 0.7 이면 drift_detected=False를 반환한다."""
    for i in range(5):
        _write_qa_result(
            tmp_path / "CH1" / f"run_{i:03d}" / "step11" / "qa_result.json",
            0.9
        )
    from src.agents.video_style.character_monitor import check_character_drift
    result = check_character_drift(tmp_path, "CH1")
    assert result["drift_detected"] is False


def test_check_manim_fallback_rate_calculates_average(tmp_path):
    """최근 10개 실행의 평균 Manim fallback_rate를 반환한다."""
    for i in range(5):
        report_path = tmp_path / "CH1" / f"run_{i:03d}" / "step08" / "manim_stability_report.json"
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(
            json.dumps({"fallback_rate": 0.6}, ensure_ascii=True), encoding="utf-8-sig"
        )
    from src.agents.video_style.style_optimizer import check_manim_fallback_rate
    rate = check_manim_fallback_rate(tmp_path, "CH1")
    assert abs(rate - 0.6) < 0.01


def test_video_style_agent_run_returns_report(tmp_path):
    """run()이 모든 채널의 드리프트 및 Manim 상태를 포함한 리포트를 반환한다."""
    # CH1 QA 결과 생성 — VideoStyleAgent.runs_dir = root/"runs" 이므로 runs/ 하위에 생성
    for i in range(3):
        _write_qa_result(
            tmp_path / "runs" / "CH1" / f"run_{i:03d}" / "step11" / "qa_result.json",
            0.85
        )

    # 채널 목록 상태 파일 생성
    import json as _json
    registry_path = tmp_path / "data" / "global" / "channel_registry.json"
    registry_path.parent.mkdir(parents=True, exist_ok=True)
    registry_path.write_text(
        _json.dumps([{"id": "CH1", "status": "active"}], ensure_ascii=True),
        encoding="utf-8-sig"
    )

    from src.agents.video_style import VideoStyleAgent
    agent = VideoStyleAgent(root=tmp_path)
    report = agent.run()

    assert "channels" in report
    assert "CH1" in report["channels"]
    assert "drift_detected" in report["channels"]["CH1"]
