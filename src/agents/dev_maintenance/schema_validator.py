"""supabase_schema.sql ↔ web/lib/types.ts 불일치를 감지한다."""
import re
from pathlib import Path


def extract_table_names_from_sql(sql_path: Path) -> set:
    """SQL 파일에서 CREATE TABLE 문의 테이블명을 추출한다."""
    content = sql_path.read_text(encoding="utf-8")
    return set(re.findall(r"CREATE TABLE(?:\s+IF NOT EXISTS)?\s+(\w+)", content, re.IGNORECASE))


def extract_identifiers_from_types(types_path: Path) -> set:
    """types.ts에서 최상위 키 식별자를 추출한다."""
    content = types_path.read_text(encoding="utf-8")
    return set(re.findall(r"(\w+)\s*:", content))


def find_missing_types(sql_path: Path, types_path: Path) -> list:
    """SQL에는 있지만 types.ts에 정의가 없는 테이블 이름을 반환한다.

    Returns:
        정렬된 테이블명 리스트. 동기화 완료 시 빈 리스트.
    """
    sql_tables = extract_table_names_from_sql(sql_path)
    ts_identifiers = extract_identifiers_from_types(types_path)
    return sorted(sql_tables - ts_identifiers)
