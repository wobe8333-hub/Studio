"""
원인 즉시 확정: 최신 report의 mismatch_diff_path 내용 출력.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from backend.knowledge_v1.paths import get_repo_root, get_report_paths


def main() -> int:
    parser = argparse.ArgumentParser(description="Print latest replay mismatch diff")
    parser.add_argument("--latest", action="store_true", help="Use latest report (default)")
    parser.parse_args()
    repo_root = get_repo_root()
    report_paths = get_report_paths(repo_root)
    reports_dir = report_paths.gate_stats.parent
    cycle_reports = sorted(
        reports_dir.glob("discovery_cycle_*.json"),
        key=lambda p: p.stat().st_mtime,
    )
    if not cycle_reports:
        print("NO_MISMATCH_DIFF", flush=True)
        return 0
    latest = cycle_reports[-1]
    try:
        with open(latest, "r", encoding="utf-8") as f:
            report = json.load(f)
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr, flush=True)
        return 1
    governance = report.get("governance") or {}
    replay = governance.get("replay_verification") or {}
    diff_path_str = replay.get("mismatch_diff_path")
    if not diff_path_str:
        print("NO_MISMATCH_DIFF", flush=True)
        return 0
    diff_path = Path(diff_path_str)
    if not diff_path.exists():
        print(f"NO_MISMATCH_DIFF (file missing: {diff_path_str})", flush=True)
        return 0
    try:
        with open(diff_path, "r", encoding="utf-8") as f:
            diff_data = json.load(f)
        print(json.dumps(diff_data, ensure_ascii=False, indent=2), flush=True)
        return 0
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr, flush=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
