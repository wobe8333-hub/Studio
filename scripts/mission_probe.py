#!/usr/bin/env python3
"""
KAS Mission Probe -- SessionStart 훅에서 자동 실행.
HITL 미해결 신호와 FAILED 실행을 감지하여 사용자에게 /mission 실행을 권고한다.
async: true 비차단 실행으로 세션 시작 지연 없음.
"""
from __future__ import annotations

import io
import json
import pathlib
import sys

# Windows cp949 콘솔에서 한글 출력 보장
if hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT = pathlib.Path(__file__).parent.parent


def check_hitl_signals() -> list[dict]:
    f = ROOT / "data/global/notifications/hitl_signals.json"
    if not f.exists():
        return []
    try:
        signals = json.loads(f.read_text(encoding="utf-8-sig"))
        return [s for s in signals if not s.get("resolved", False)]
    except Exception:
        return []


def check_failed_runs() -> list[str]:
    runs = ROOT / "runs"
    if not runs.exists():
        return []
    failed: list[str] = []
    for m in runs.rglob("manifest.json"):
        try:
            data = json.loads(m.read_text(encoding="utf-8-sig"))
            if data.get("run_state") == "FAILED":
                failed.append(str(m.parent))
        except Exception:
            continue
    return failed


def main() -> None:
    unresolved = check_hitl_signals()
    failed = check_failed_runs()

    if not unresolved and not failed:
        print("[mission-probe] OK -- HITL 없음, 실패 런 없음")
        return

    print("=" * 50)
    print("[MISSION-TRIGGER] 자동 감지된 이슈가 있습니다!")
    print("=" * 50)

    if unresolved:
        print(f"\n[!] HITL 미해결 신호: {len(unresolved)}건")
        for s in unresolved[:3]:
            print(f"   - [{s.get('type', '?')}] {str(s.get('message', ''))[:80]}")

    if failed:
        print(f"\n[X] FAILED 실행: {len(failed)}건")
        for fp in failed[:3]:
            print(f"   - {fp}")

    print("\n-> '/mission' 을 실행하여 이슈를 해결하세요.")
    print("=" * 50)


if __name__ == "__main__":
    main()
