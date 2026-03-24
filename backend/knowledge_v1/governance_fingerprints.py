"""
Governance Fingerprints - raw/canonical fingerprint 계산 SSOT

assets.jsonl / chunks.jsonl / gate_stats.json 에 대해
- raw 파일 SHA256
- canonical SHA256 (정규화/정렬/volatile 키 제거)
를 모두 계산한다.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set, Tuple

from backend.knowledge_v1.paths import (
    get_discovery_raw_assets_path,
    get_discovery_derived_chunks_path,
    get_gate_stats_path_from_repo_root,
)
from backend.knowledge_v1.store import load_jsonl


VOLATILE_DEFAULT_KEYS: Set[str] = {
    "created_at",
    "created_at_utc",
    "updated_at",
    "frozen_at",
}


def _sha256_bytes(data: bytes) -> str:
    h = hashlib.sha256()
    h.update(data)
    return h.hexdigest()


def _sha256_file(path: Path) -> Optional[str]:
    """
    파일 SHA256 해시 반환. 없으면 None.
    """
    path = Path(path)
    if not path.exists() or not path.is_file():
        return None
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            h.update(chunk)
    return h.hexdigest()


def _drop_volatile_keys(obj: Dict[str, Any], drop_keys: Set[str]) -> Dict[str, Any]:
    """
    상위 레벨에서 volatile 키 제거.
    (중첩 구조까지 재귀 제거는 필요 시 확장)
    """
    if not drop_keys:
        return dict(obj)
    return {k: v for k, v in obj.items() if k not in drop_keys}


def compute_canonical_jsonl_sha(
    path: Path,
    sort_keys: Optional[Sequence[str]] = None,
    drop_keys: Optional[Set[str]] = None,
) -> Tuple[int, Optional[str]]:
    """
    JSONL 파일에 대한 canonical SHA256 계산.

    규칙:
      1) 각 레코드에서 volatile 키 제거
      2) sort_keys=True 로 JSON 직렬화 (key 정렬)
      3) 지정 sort_keys 기준으로 레코드 정렬 후 join → SHA256

    Returns:
        (record_count, canonical_sha256 or None)
    """
    path = Path(path)
    if drop_keys is None:
        drop_keys = VOLATILE_DEFAULT_KEYS

    if not path.exists() or not path.is_file():
        return 0, None

    records: List[Tuple[Tuple[Any, ...], str]] = []
    count = 0

    for row in load_jsonl(path):
        if not isinstance(row, dict):
            continue
        count += 1
        clean = _drop_volatile_keys(row, drop_keys)
        serialized = json.dumps(
            clean,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        if sort_keys:
            key_tuple: Tuple[Any, ...] = tuple(clean.get(k) for k in sort_keys)
        else:
            key_tuple = (serialized,)
        records.append((key_tuple, serialized))

    if not records:
        return 0, None

    records.sort(key=lambda x: x[0])
    combined = "\n".join(serialized for _, serialized in records)
    return count, _sha256_bytes(combined.encode("utf-8"))


def compute_canonical_json_sha(
    path: Path,
    drop_keys: Optional[Set[str]] = None,
) -> Optional[str]:
    """
    JSON 단일 파일(gate_stats 등)에 대한 canonical SHA256 계산.

    규칙:
      - volatile 키 제거
      - sort_keys=True JSON 직렬화 후 SHA256
    """
    from backend.knowledge_v1.io.json_io import load_json  # 지연 임포트

    path = Path(path)
    if drop_keys is None:
        drop_keys = VOLATILE_DEFAULT_KEYS

    if not path.exists() or not path.is_file():
        return None

    data = load_json(path)
    if isinstance(data, dict):
        data = _drop_volatile_keys(data, drop_keys)

    serialized = json.dumps(
        data,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return _sha256_bytes(serialized.encode("utf-8"))


def compute_replay_fingerprints(repo_root: Path) -> Dict[str, Any]:
    """
    V7 replay를 위한 raw/canonical fingerprint 및 카운트 계산.

    - assets.jsonl / chunks.jsonl: JSONL canonical + raw 파일 SHA
    - gate_stats.json: JSON canonical + raw 파일 SHA
    """
    repo_root = Path(repo_root)

    assets_path = get_discovery_raw_assets_path()
    chunks_path = get_discovery_derived_chunks_path()
    gate_stats_path = get_gate_stats_path_from_repo_root(repo_root)

    # raw 파일 SHA
    assets_sha256 = _sha256_file(assets_path)
    chunks_sha256 = _sha256_file(chunks_path)
    gate_stats_sha256 = _sha256_file(gate_stats_path)

    # canonical SHA + 카운트
    assets_count, assets_canonical_sha256 = compute_canonical_jsonl_sha(
        assets_path,
        sort_keys=("asset_id", "chunk_id"),
    )
    chunks_count, chunks_canonical_sha256 = compute_canonical_jsonl_sha(
        chunks_path,
        sort_keys=("chunk_id", "asset_id"),
    )
    gate_stats_canonical_sha256 = compute_canonical_json_sha(gate_stats_path)

    if (
        assets_sha256 is None
        and chunks_sha256 is None
        and gate_stats_sha256 is None
    ):
        raise RuntimeError("REPLAY_FINGERPRINT_ALL_NONE")

    return {
        "paths": {
            "assets_path": str(assets_path),
            "chunks_path": str(chunks_path),
            "gate_stats_path": str(gate_stats_path),
        },
        "raw": {
            "assets_sha256": assets_sha256,
            "chunks_sha256": chunks_sha256,
            "gate_stats_sha256": gate_stats_sha256,
        },
        "canonical": {
            "assets_canonical_sha256": assets_canonical_sha256,
            "chunks_canonical_sha256": chunks_canonical_sha256,
            "gate_stats_canonical_sha256": gate_stats_canonical_sha256,
        },
        "counts": {
            "assets_lines": assets_count,
            "chunks_lines": chunks_count,
        },
    }

