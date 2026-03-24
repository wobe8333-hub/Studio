"""
MemorySnapshotV3 저장 로직

기능:
- MemorySnapshotV3를 JSON 파일로 저장
- backend/output/memory_v3/snapshots/<run_id>.json
"""

import json
from pathlib import Path
from typing import Dict, Any

from backend.memory_v3.schema import MemorySnapshotV3


def save_snapshot(snapshot: MemorySnapshotV3, base_dir: Path = None) -> Path:
    """
    MemorySnapshotV3를 JSON 파일로 저장
    
    Args:
        snapshot: 저장할 MemorySnapshotV3 객체
        base_dir: 기본 디렉토리 (None이면 프로젝트 루트 기준)
    
    Returns:
        Path: 저장된 파일 경로
    """
    if base_dir is None:
        from backend.utils.run_manager import get_project_root
        project_root = get_project_root()
        output_dir = project_root / "backend" / "output"
    else:
        if base_dir.name == "backend":
            output_dir = base_dir / "output"
        else:
            output_dir = base_dir / "output" if (base_dir / "output").exists() else base_dir
    
    snapshots_dir = output_dir / "memory_v3" / "snapshots"
    snapshots_dir.mkdir(parents=True, exist_ok=True)
    
    snapshot_path = snapshots_dir / f"{snapshot.run_id}.json"
    
    # JSON 저장 (utf-8, ensure_ascii=False, indent=2)
    with open(snapshot_path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(snapshot.to_dict(), f, ensure_ascii=False, indent=2)
    
    return snapshot_path

