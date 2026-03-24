from __future__ import annotations
import json
from pathlib import Path
from typing import Dict, List

from backend.knowledge_v1.keyword_sources.keyword_sources import RawKeyword

def load_snapshot_keywords(*, store_root: Path, cycle_id: str, category: str) -> List[RawKeyword]:
    p = store_root / "snapshots" / cycle_id / f"keywords_{category}_raw.jsonl"
    if not p.exists():
        return []
    out: List[RawKeyword] = []
    with open(p, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            out.append(RawKeyword(**row))
    return out

