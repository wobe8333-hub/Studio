import hashlib
from pathlib import Path
from typing import Dict, Iterable


def sha256_bytes(data: bytes) -> str:
    """SHA256 해시(hex) 계산."""
    h = hashlib.sha256()
    h.update(data)
    return h.hexdigest()


def sha256_file(path: Path) -> str:
    """파일 전체 SHA256 해시(hex) 계산."""
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
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

