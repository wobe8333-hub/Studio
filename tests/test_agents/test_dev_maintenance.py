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


def test_run_tests_returns_passed_on_success(tmp_path, monkeypatch):
    """pytest가 0으로 종료되면 passed=True를 반환한다."""
    import subprocess

    monkeypatch.setattr(
        subprocess, "run",
        lambda *a, **kw: type("R", (), {"returncode": 0, "stdout": "2 passed", "stderr": ""})()
    )
    from src.agents.dev_maintenance.health_checker import run_tests
    result = run_tests(tmp_path)
    assert result["passed"] is True
    assert "passed" in result["output"]


def test_run_tests_returns_failed_on_error(tmp_path, monkeypatch):
    """pytest가 1로 종료되면 passed=False를 반환한다."""
    import subprocess

    monkeypatch.setattr(
        subprocess, "run",
        lambda *a, **kw: type("R", (), {"returncode": 1, "stdout": "", "stderr": "1 failed"})()
    )
    from src.agents.dev_maintenance.health_checker import run_tests
    result = run_tests(tmp_path)
    assert result["passed"] is False


def test_find_missing_types_detects_new_table(tmp_path):
    """SQL에 추가된 테이블이 types.ts에 없으면 반환한다."""
    sql = tmp_path / "schema.sql"
    sql.write_text(
        "CREATE TABLE channels (id TEXT);\nCREATE TABLE new_table (col INT);",
        encoding="utf-8"
    )
    # Supabase 생성 타입 파일 구조: "tablename: { Row: {...} }" 패턴
    types_ts = tmp_path / "types.ts"
    types_ts.write_text(
        "export type Database = { channels: { Row: { id: string } } }",
        encoding="utf-8"
    )

    from src.agents.dev_maintenance.schema_validator import find_missing_types
    missing = find_missing_types(sql, types_ts)

    assert "new_table" in missing
    assert "channels" not in missing


def test_find_missing_types_returns_empty_when_in_sync(tmp_path):
    """SQL과 types.ts가 일치하면 빈 리스트를 반환한다."""
    sql = tmp_path / "schema.sql"
    sql.write_text("CREATE TABLE channels (id TEXT);", encoding="utf-8")
    # Supabase 생성 타입 파일 구조: "tablename: { Row: {...} }" 패턴
    types_ts = tmp_path / "types.ts"
    types_ts.write_text(
        "export type Database = { channels: { Row: { id: string } } }",
        encoding="utf-8"
    )

    from src.agents.dev_maintenance.schema_validator import find_missing_types
    assert find_missing_types(sql, types_ts) == []


def test_dev_agent_run_returns_report(tmp_path, monkeypatch):
    """run()이 실패 수, health 결과, 스키마 불일치 수를 포함한 리포트를 반환한다."""
    import subprocess

    # FAILED 실행 1개 생성 — DevMaintenanceAgent.runs_dir = root/"runs" 이므로 runs/ 하위에 생성
    _write_manifest(tmp_path / "runs" / "CH1" / "run_001" / "manifest.json", "FAILED")

    # subprocess.run mock (pytest 성공)
    monkeypatch.setattr(
        subprocess, "run",
        lambda *a, **kw: type("R", (), {"returncode": 0, "stdout": "1 passed", "stderr": ""})()
    )

    # schema/types 파일 생성 (동기화 상태)
    sql_path = tmp_path / "scripts" / "supabase_schema.sql"
    sql_path.parent.mkdir(parents=True)
    sql_path.write_text("CREATE TABLE channels (id TEXT);", encoding="utf-8")
    types_path = tmp_path / "web" / "lib" / "types.ts"
    types_path.parent.mkdir(parents=True)
    # Supabase 생성 타입 파일 구조 반영 — schema_missing=[] 이 되도록 "tablename: { Row:" 패턴 사용
    types_path.write_text("channels: { Row: { id: string } }", encoding="utf-8")

    from src.agents.dev_maintenance import DevMaintenanceAgent
    agent = DevMaintenanceAgent(root=tmp_path)
    report = agent.run()

    assert "failed_runs" in report
    assert len(report["failed_runs"]) == 1
    assert "health" in report
    assert "schema_missing" in report
