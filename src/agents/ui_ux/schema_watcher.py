"""supabase_schema.sql의 변경 여부를 SHA-256 해시로 감지한다."""
import hashlib
from pathlib import Path
from src.core.ssot import read_json, write_json


def get_schema_hash(sql_path: Path) -> str:
    """SQL 파일의 SHA-256 해시를 반환한다."""
    return hashlib.sha256(sql_path.read_bytes()).hexdigest()


def has_schema_changed(sql_path: Path, state_path: Path) -> bool:
    """이전 실행 대비 스키마 변경 여부를 확인한다.

    Returns:
        True if 변경됨 또는 최초 실행, False if 동일
    """
    current_hash = get_schema_hash(sql_path)
    try:
        state = read_json(state_path)
        return state.get("schema_hash") != current_hash
    except FileNotFoundError:
        return True


def save_schema_hash(sql_path: Path, state_path: Path) -> None:
    """현재 스키마 해시를 상태 파일에 저장한다."""
    write_json(state_path, {"schema_hash": get_schema_hash(sql_path)})
