#!/usr/bin/env python3
"""
SessionEnd 훅 — 세션 종료 시 로그 순환 + 비용 집계.
hooks.log 순환 (10MB 초과 시) + gemini_quota_daily.json 비용 집계.
async: true — 비차단 실행.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).parent.parent.parent
HOOKS_LOG = ROOT / ".claude" / "agent-logs" / "hooks.log"
QUOTA_PATH = ROOT / "data" / "global" / "quota" / "gemini_quota_daily.json"
SESSION_LOG = ROOT / "data" / "global" / "session_history.json"

MAX_LOG_SIZE_BYTES = 10 * 1024 * 1024  # 10MB


def rotate_log() -> None:
    """hooks.log 10MB 초과 시 순환."""
    if not HOOKS_LOG.exists():
        return
    if HOOKS_LOG.stat().st_size > MAX_LOG_SIZE_BYTES:
        archive = HOOKS_LOG.with_suffix(".log.1")
        HOOKS_LOG.rename(archive)
        HOOKS_LOG.touch()


def collect_cost_summary() -> dict:
    """gemini_quota_daily.json에서 당일 비용 집계."""
    if not QUOTA_PATH.exists():
        return {}
    try:
        with open(QUOTA_PATH, encoding="utf-8-sig") as f:
            quota = json.load(f)
        return {
            "total_cost_usd": quota.get("total_cost_usd", 0.0),
            "request_count": quota.get("request_count", 0),
        }
    except Exception:
        return {}


def log_session_end() -> None:
    """세션 종료 이력 기록."""
    try:
        SESSION_LOG.parent.mkdir(parents=True, exist_ok=True)
        if SESSION_LOG.exists():
            with open(SESSION_LOG, encoding="utf-8-sig") as f:
                history = json.load(f)
        else:
            history = {"schema_version": "1.0", "sessions": []}

        cost = collect_cost_summary()
        history.setdefault("sessions", []).append({
            "ended_at": datetime.now(timezone.utc).isoformat(),
            "cost_summary": cost,
        })
        history["sessions"] = history["sessions"][-100:]

        with open(SESSION_LOG, "w", encoding="utf-8") as f:
            json.dump(history, f, ensure_ascii=True, indent=2)
    except Exception:
        pass


def main() -> None:
    rotate_log()
    log_session_end()


if __name__ == "__main__":
    main()
