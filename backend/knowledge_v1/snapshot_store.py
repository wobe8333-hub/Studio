"""
스냅샷 저장소 SSOT (replay cache-only 시 fetch 결과 고정)

- cache_only=True 시 read_snapshot만 사용, 없으면 RuntimeError("SNAPSHOT_MISSING_IN_CACHE_ONLY")
- cache_only=False 시 네트워크 호출 후 write_snapshot 저장
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Dict, Optional

from backend.knowledge_v1.paths import get_repo_root, as_path

SNAPSHOTS_DIR_NAME = "snapshots"


def _snapshots_root() -> Path:
    return as_path(get_repo_root()) / "data" / "knowledge_v1_store" / "discovery" / SNAPSHOTS_DIR_NAME


def snapshot_key(input_hash: str, source_name: str, request_params: Dict[str, Any]) -> str:
    """결정적 스냅샷 키 (input_hash + source + params canonical JSON)."""
    canonical = json.dumps(request_params, sort_keys=True, ensure_ascii=False)
    raw = f"{input_hash}|{source_name}|{canonical}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:32]


def read_snapshot(key: str) -> Optional[Dict[str, Any]]:
    """스냅샷 읽기. 없으면 None."""
    root = _snapshots_root()
    path = root / f"{key}.json"
    if not path.exists() or not path.is_file():
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def write_snapshot(key: str, payload: Dict[str, Any]) -> Path:
    """스냅샷 저장. 반환: 저장된 파일 Path."""
    root = _snapshots_root()
    root.mkdir(parents=True, exist_ok=True)
    path = root / f"{key}.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    return path
