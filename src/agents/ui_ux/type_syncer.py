"""supabase_schema.sql 컬럼 정보를 TypeScript 타입으로 변환한다."""
import re
from pathlib import Path
from loguru import logger

_SQL_TO_TS: dict = {
    "TEXT": "string",
    "VARCHAR": "string",
    "INT": "number",
    "INTEGER": "number",
    "BIGINT": "number",
    "REAL": "number",
    "FLOAT": "number",
    "SERIAL": "number",
    "NUMERIC": "number",
    "BOOL": "boolean",
    "BOOLEAN": "boolean",
    "TIMESTAMPTZ": "string",
    "TIMESTAMP": "string",
    "DATE": "string",
    "UUID": "string",
    "JSONB": "Record<string, unknown>",
    "JSON": "Record<string, unknown>",
    "TEXT[]": "string[]",
    "INT[]": "number[]",
}


def extract_columns_from_sql(sql_content: str, table_name: str) -> list:
    """SQL에서 특정 테이블의 컬럼 정보를 추출한다.

    Returns:
        [{"name": str, "sql_type": str}] 리스트
    """
    pattern = rf"CREATE TABLE(?:\s+IF NOT EXISTS)?\s+{re.escape(table_name)}\s*\((.*?)\);"
    match = re.search(pattern, sql_content, re.DOTALL | re.IGNORECASE)
    if not match:
        return []

    columns = []
    _skip = {"PRIMARY", "FOREIGN", "UNIQUE", "CHECK", "CONSTRAINT"}
    for line in match.group(1).split("\n"):
        line = line.strip().rstrip(",")
        if not line or any(line.upper().startswith(s) for s in _skip):
            continue
        col_match = re.match(r"(\w+)\s+([\w\[\]]+)", line)
        if col_match:
            columns.append({
                "name": col_match.group(1),
                "sql_type": col_match.group(2).upper(),
            })
    return columns


def sql_type_to_ts(sql_type: str) -> str:
    """SQL 데이터 타입을 TypeScript 타입 문자열로 변환한다."""
    return _SQL_TO_TS.get(sql_type.upper(), "unknown")


def _to_pascal_case(name: str) -> str:
    """snake_case 테이블명을 PascalCase로 변환한다. pipeline_runs → PipelineRuns"""
    return "".join(word.capitalize() for word in name.split("_"))


def generate_ts_interface(table_name: str, columns: list) -> str:
    """컬럼 목록으로 TypeScript interface 문자열을 생성한다."""
    lines = [f"export interface {_to_pascal_case(table_name)} {{"]
    for col in columns:
        ts_type = sql_type_to_ts(col["sql_type"])
        lines.append(f"  {col['name']}: {ts_type};")
    lines.append("}")
    return "\n".join(lines)
