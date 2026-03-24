from __future__ import annotations
import json, platform, subprocess, sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

def _safe_git_commit(repo_root: Path) -> Optional[str]:
    try:
        r = subprocess.run(["git","rev-parse","HEAD"], cwd=str(repo_root),
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        return r.stdout.strip() if r.returncode == 0 else None
    except Exception:
        return None

def main() -> int:
    out, version = None, None
    args = sys.argv[1:]
    i = 0
    while i < len(args):
        if args[i] == "--out":
            out = args[i+1]; i+=2
        elif args[i] == "--version":
            version = args[i+1]; i+=2
        else:
            return 2
    if not out:
        return 2
    repo_root = Path(__file__).resolve().parents[2]
    info = {
        "version": version,
        "build_utc": _utc_now_iso(),
        "python_version": sys.version.split()[0],
        "platform": platform.platform(),
        "git_commit": _safe_git_commit(repo_root),
    }
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    Path(out).write_text(json.dumps(info, ensure_ascii=False, indent=2), encoding="utf-8")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
