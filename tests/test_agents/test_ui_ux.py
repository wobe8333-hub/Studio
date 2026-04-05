"""UI/UX Agent 테스트."""
from pathlib import Path
import pytest


def test_has_schema_changed_true_when_first_run(tmp_path):
    """상태 파일이 없으면 항상 변경됨으로 판정한다."""
    sql_path = tmp_path / "schema.sql"
    sql_path.write_text("CREATE TABLE channels (id TEXT);", encoding="utf-8")
    state_path = tmp_path / "schema_state.json"

    from src.agents.ui_ux.schema_watcher import has_schema_changed
    assert has_schema_changed(sql_path, state_path) is True


def test_has_schema_changed_false_when_unchanged(tmp_path):
    """이전과 동일한 SQL이면 변경 없음으로 판정한다."""
    sql_path = tmp_path / "schema.sql"
    sql_path.write_text("CREATE TABLE channels (id TEXT);", encoding="utf-8")

    from src.agents.ui_ux.schema_watcher import get_schema_hash, save_schema_hash, has_schema_changed
    state_path = tmp_path / "schema_state.json"
    save_schema_hash(sql_path, state_path)

    assert has_schema_changed(sql_path, state_path) is False


def test_extract_columns_from_sql_parses_types(tmp_path):
    """SQL CREATE TABLE에서 컬럼명과 타입을 올바르게 파싱한다."""
    sql_content = """
    CREATE TABLE channels (
        id TEXT,
        subscriber_count INT,
        is_active BOOL,
        created_at TIMESTAMPTZ
    );
    """
    from src.agents.ui_ux.type_syncer import extract_columns_from_sql
    columns = extract_columns_from_sql(sql_content, "channels")

    names = [c["name"] for c in columns]
    assert "id" in names
    assert "subscriber_count" in names
    assert "is_active" in names


def test_sql_type_to_ts_converts_correctly():
    """SQL 타입을 TypeScript 타입으로 올바르게 변환한다."""
    from src.agents.ui_ux.type_syncer import sql_type_to_ts
    assert sql_type_to_ts("TEXT") == "string"
    assert sql_type_to_ts("INT") == "number"
    assert sql_type_to_ts("BOOL") == "boolean"
    assert sql_type_to_ts("TIMESTAMPTZ") == "string"
    assert sql_type_to_ts("TEXT[]") == "string[]"


def test_uiux_agent_run_detects_schema_change(tmp_path):
    """스키마가 변경됐을 때 changed=True를 포함한 리포트를 반환한다."""
    sql_path = tmp_path / "scripts" / "supabase_schema.sql"
    sql_path.parent.mkdir(parents=True)
    sql_path.write_text("CREATE TABLE channels (id TEXT);", encoding="utf-8")

    types_path = tmp_path / "web" / "lib" / "types.ts"
    types_path.parent.mkdir(parents=True)
    types_path.write_text("export interface Channels { id: string; }", encoding="utf-8")

    from src.agents.ui_ux import UiUxAgent
    agent = UiUxAgent(root=tmp_path)
    report = agent.run()

    assert "schema_changed" in report
    assert report["schema_changed"] is True


def test_uiux_agent_run_no_change_after_save(tmp_path):
    """동일한 스키마로 두 번 실행하면 두 번째는 changed=False를 반환한다."""
    sql_path = tmp_path / "scripts" / "supabase_schema.sql"
    sql_path.parent.mkdir(parents=True)
    sql_path.write_text("CREATE TABLE channels (id TEXT);", encoding="utf-8")

    types_path = tmp_path / "web" / "lib" / "types.ts"
    types_path.parent.mkdir(parents=True)
    types_path.write_text("export interface Channels { id: string; }", encoding="utf-8")

    from src.agents.ui_ux import UiUxAgent
    agent = UiUxAgent(root=tmp_path)
    agent.run()        # 첫 번째 실행 — 해시 저장
    report = agent.run()  # 두 번째 실행 — 변경 없음

    assert report["schema_changed"] is False
