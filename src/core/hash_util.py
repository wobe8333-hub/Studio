import hashlib
from pathlib import Path
from typing import Dict, Iterable
from src.core.ssot import sha256_file  # ssot.py의 구현 재사용 (중복 제거)


def sha256_bytes(data: bytes) -> str:
    """SHA256 해시(hex) 계산."""
    h = hashlib.sha256()
    h.update(data)
    return h.hexdigest()


def build_hash_map(root: Path, paths: Iterable[Path]) -> Dict[str, str]:
    """
    루트 기준 상대경로 -> sha256 맵 생성.
    """
    result: Dict[str, str] = {}
    for p in sorted({Path(p) for p in paths}):
        if not p.is_file():
            continue
        rel = p.relative_to(root)
        result[rel.as_posix()] = sha256_file(p)
    return result

