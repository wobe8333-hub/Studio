"""Dev & Maintenance Agent 테스트."""
import json
from pathlib import Path
import pytest


def _write_manifest(path: Path, run_state: str) -> None:
    """테스트용 manifest.json을 utf-8-sig 인코딩으로 생성한다."""
    path.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "run_id": path.parent.name,
        "channel_id": "CH1",
        "run_state": run_state,
        "error": "테스트 에러" if run_state == "FAILED" else ""
    }
    path.write_text(json.dumps(data, ensure_ascii=True), encoding="utf-8-sig")


def test_find_failed_runs_returns_only_failed(tmp_path):
    """FAILED 상태 manifest만 반환하고 COMPLETED는 무시한다."""
    _write_manifest(tmp_path / "CH1" / "run_001" / "manifest.json", "FAILED")
    _write_manifest(tmp_path / "CH1" / "run_002" / "manifest.json", "COMPLETED")

    from src.agents.dev_maintenance.log_monitor import find_failed_runs
    result = find_failed_runs(tmp_path)

    assert len(result) == 1
    assert result[0]["run_id"] == "run_001"
    assert result[0]["run_state"] == "FAILED"


def test_find_failed_runs_empty_when_no_runs(tmp_path):
    """runs 디렉토리가 비어있으면 빈 리스트를 반환한다."""
    from src.agents.dev_maintenance.log_monitor import find_failed_runs
    result = find_failed_runs(tmp_path)
    assert result == []
