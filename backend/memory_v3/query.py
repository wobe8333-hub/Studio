from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Literal

DEFAULT_RUN_ID = "965d3860-66e9-401d-b0ed-fd068186ff89"

STATE = Literal["ACTIVE", "DEPRECATED", "ARCHIVED"]
ORDER = Literal["asc", "desc"]


def _parse_iso_utc(s: str) -> datetime:
    # accepts "2025-01-01T00:00:00Z" or "+00:00"
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    dt = datetime.fromisoformat(s)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _age_days_from(collected_at: str) -> float:
    now = datetime.now(timezone.utc)
    last = _parse_iso_utc(collected_at)
    return (now - last).total_seconds() / 86400.0


def _root() -> Path:
    # project root 기준 고정 경로 (v3 산출물 SSOT)
    return Path("backend") / "output" / "memory_v3"


def _snapshots_dir() -> Path:
    return _root() / "snapshots"


def _governance_dir(run_id: str) -> Path:
    return _root() / "governance" / run_id


def _indexed_dir(run_id: str) -> Path:
    return _root() / "indexed" / run_id


def list_run_ids() -> List[str]:
    d = _snapshots_dir()
    if not d.exists():
        return []
    return sorted([p.stem for p in d.glob("*.json")])


def load_json(path: Path) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def query_memory(
    run_id: str = DEFAULT_RUN_ID,
    state: Optional[STATE] = None,
    has_valuable_failure: Optional[bool] = None,
    tag: Optional[str] = None,
    limit: int = 10,
    order: ORDER = "desc",
) -> Dict[str, Any]:
    # clamp limit
    if limit <= 0:
        limit = 10
    if limit > 100:
        limit = 100

    run_ids = [run_id] if run_id else list_run_ids()

    items: List[Dict[str, Any]] = []

    for rid in run_ids:
        snapshot_path = _snapshots_dir() / f"{rid}.json"
        if not snapshot_path.exists():
            continue

        gov_dir = _governance_dir(rid)
        state_summary_path = gov_dir / "state_summary.json"
        if not state_summary_path.exists():
            # Step4가 없는 run은 Step5 조회대상 제외(일관성)
            continue

        snapshot = load_json(snapshot_path)
        state_summary = load_json(state_summary_path)

        collected_at = snapshot.get("collected_at")
        if not collected_at:
            continue

        st = state_summary.get("state")
        if st not in ("ACTIVE", "DEPRECATED", "ARCHIVED"):
            continue

        tags = snapshot.get("tags") or []
        if not isinstance(tags, list):
            tags = []

        vf = (snapshot.get("verify_summary") or {}).get("valuable_failure", None)

        age_days = state_summary.get("age_days")
        if age_days is None:
            age_days = _age_days_from(collected_at)

        item = {
            "run_id": rid,
            "state": st,
            "collected_at": collected_at,
            "age_days": float(age_days),
            "tags": [str(x) for x in tags],
            "valuable_failure": vf if (vf is True or vf is False) else None,
            "paths": {
                "snapshot": str(snapshot_path.resolve()),
                "indexed": str(_indexed_dir(rid).resolve()),
                "governance": str(gov_dir.resolve()),
            },
        }

        # filters
        if state and item["state"] != state:
            continue
        if has_valuable_failure is True and item["valuable_failure"] is not True:
            continue
        if has_valuable_failure is False and item["valuable_failure"] is not False:
            continue
        if tag and tag not in item["tags"]:
            continue

        items.append(item)

    # sort by collected_at
    items.sort(key=lambda x: x["collected_at"], reverse=(order == "desc"))

    items = items[:limit]

    return {
        "reference_only": True,
        "query": {
            "run_id": run_id,
            "state": state,
            "has_valuable_failure": has_valuable_failure,
            "tag": tag,
            "limit": limit,
            "order": order,
        },
        "count": len(items),
        "items": items,
    }
