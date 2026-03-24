"""
Metrics Store - v6-Step8 observability

원칙:
- runs/{run_id}/reports/metrics.json에 단일 저장
- manifest 기반 최소 지표 수집 (retry/lock/human_intervention)
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional
from datetime import datetime

from backend.utils.run_manager import get_run_dir, load_run_manifest, get_runs_root


def _now_iso() -> str:
    return datetime.utcnow().isoformat() + "Z"


def get_reports_dir(run_id: str, base_dir: Optional[Path] = None) -> Path:
    run_dir = get_run_dir(run_id, base_dir)
    reports = run_dir / "reports"
    reports.mkdir(parents=True, exist_ok=True)
    return reports


def load_metrics(run_id: str, base_dir: Optional[Path] = None) -> Dict[str, Any]:
    path = get_reports_dir(run_id, base_dir) / "metrics.json"
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def save_metrics(run_id: str, metrics: Dict[str, Any], base_dir: Optional[Path] = None) -> Path:
    path = get_reports_dir(run_id, base_dir) / "metrics.json"
    path.write_text(json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def collect_min_metrics(run_id: str, llm_cost_estimate: float = 0.0, base_dir: Optional[Path] = None) -> Dict[str, Any]:
    """
    현재 코드에서 신뢰 가능한 최소 지표만 수집.
    비용 추정은 외부에서 전달(또는 0)로 두고, 나중에 정밀화한다.
    """
    manifest = load_run_manifest(run_id, base_dir)
    steps = manifest.get("steps", {}) or {}

    retry_count = 0
    lock_count = 0
    human_intervention_count = 0

    for _, s in steps.items():
        if isinstance(s, dict):
            retry_count += int(s.get("retry_count", 0) or 0)
            lock_count += int(s.get("lock_count", 0) or 0)
            human_intervention_count += int(s.get("human_intervention_count", 0) or 0)

    metrics = load_metrics(run_id, base_dir)
    metrics.setdefault("created_at", _now_iso())
    metrics["updated_at"] = _now_iso()

    total_runtime_sec = float(manifest.get("total_runtime_sec", 0.0) or 0.0)

    metrics.update({
        "run_id": run_id,
        "total_runtime_sec": total_runtime_sec,
        "llm_cost_estimate": float(llm_cost_estimate or 0.0),
        "retry_count": int(retry_count),
        "lock_count": int(lock_count),
        "human_intervention_count": int(human_intervention_count),
    })

    save_metrics(run_id, metrics, base_dir)
    return metrics


def latest_run_id(base_dir: Optional[Path] = None) -> Optional[str]:
    runs_root = get_runs_root(base_dir)
    if not runs_root.exists():
        return None
    dirs = [p for p in runs_root.iterdir() if p.is_dir()]
    if not dirs:
        return None
    dirs.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return dirs[0].name

