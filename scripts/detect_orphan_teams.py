#!/usr/bin/env python3
"""
고아 팀(Orphan Team) 탐지 유틸.
~/.claude/teams/ 디렉토리를 스캔하여 data/exec/team_lifecycle.json과 대조,
24시간 이상 활성 상태인 미션팀을 탐지하고 경고를 출력한다.
cron 후보 또는 SessionStart 훅에서 호출 가능.
실행: python scripts/detect_orphan_teams.py [--hours 24]
"""
from __future__ import annotations

import argparse
import io
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

# Windows cp949 콘솔에서 한글 출력 보장
if hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT = Path(__file__).parent.parent
TEAMS_DIR = Path.home() / ".claude" / "teams"
LIFECYCLE_FILE = ROOT / "data" / "exec" / "team_lifecycle.json"


def load_lifecycle() -> dict[str, dict]:
    """team_lifecycle.json에서 팀 생성/종료 기록 로드."""
    if not LIFECYCLE_FILE.exists():
        return {}
    try:
        records = json.loads(LIFECYCLE_FILE.read_text(encoding="utf-8-sig"))
        # team_name 키로 인덱싱
        return {r["team_name"]: r for r in records if isinstance(r, dict)}
    except Exception:
        return {}


def get_active_teams() -> list[str]:
    """~/.claude/teams/ 디렉토리에 존재하는 팀 목록 반환."""
    if not TEAMS_DIR.exists():
        return []
    return [d.name for d in TEAMS_DIR.iterdir() if d.is_dir()]


def is_standing_team(team_name: str) -> bool:
    """상설팀이나 감사팀은 고아 판정에서 제외."""
    return team_name.startswith("kas-weekly-ops") or team_name.startswith("weekly-audit-")


def detect_orphans(threshold_hours: int = 24) -> list[dict]:
    """
    threshold_hours 이상 활성 상태인 미션팀을 탐지.
    반환: [{"team_name": ..., "created_at": ..., "age_hours": ..., "has_lifecycle": ...}]
    """
    active_teams = get_active_teams()
    lifecycle = load_lifecycle()
    now = datetime.now(timezone.utc)
    orphans = []

    for team_name in active_teams:
        # 상설팀·감사팀 제외
        if is_standing_team(team_name):
            continue

        record = lifecycle.get(team_name)
        if record and record.get("deleted_at"):
            # 이미 종료된 팀인데 디렉토리가 남아 있는 경우
            orphans.append({
                "team_name": team_name,
                "created_at": record.get("created_at"),
                "age_hours": None,
                "has_lifecycle": True,
                "issue": "TeamDelete 완료됐지만 ~/.claude/teams/ 디렉토리 잔존",
            })
            continue

        # lifecycle 기록이 없거나 종료되지 않은 경우
        created_at_str = record.get("created_at") if record else None
        age_hours = None

        if created_at_str:
            try:
                created_at = datetime.fromisoformat(created_at_str)
                if created_at.tzinfo is None:
                    created_at = created_at.replace(tzinfo=timezone.utc)
                age_hours = (now - created_at).total_seconds() / 3600
            except ValueError:
                pass

        if age_hours is None or age_hours >= threshold_hours:
            orphans.append({
                "team_name": team_name,
                "created_at": created_at_str,
                "age_hours": round(age_hours, 1) if age_hours is not None else "알 수 없음",
                "has_lifecycle": record is not None,
                "issue": f"{threshold_hours}h 이상 활성" if age_hours else "lifecycle 기록 없음",
            })

    return orphans


def main(threshold_hours: int = 24) -> None:
    orphans = detect_orphans(threshold_hours)

    if not orphans:
        print(f"[OK] 고아 팀 없음 (기준: {threshold_hours}h 초과 활성 미션팀)")
        return

    print(f"[WARN] 고아 팀 {len(orphans)}개 감지:")
    for o in orphans:
        age_str = f"{o['age_hours']}h" if o["age_hours"] != "알 수 없음" else "나이 알 수 없음"
        lifecycle_str = "lifecycle 기록 있음" if o["has_lifecycle"] else "lifecycle 기록 없음"
        print(f"  ! {o['team_name']} — {age_str} | {lifecycle_str} | {o['issue']}")

    print()
    print("처리 방법:")
    print("  1. 미션 중이면: cto/ceo가 SendMessage(*,'shutdown_request') → TeamDelete 실행")
    print("  2. 이미 완료된 팀이면: TeamDelete 호출로 ~/.claude/teams/{team_name}/ 정리")
    print("  3. lifecycle 기록이 없으면: data/exec/team_lifecycle.json 수동 기록 후 TeamDelete")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="KAS 고아 팀 탐지")
    parser.add_argument("--hours", type=int, default=24, help="고아 판정 기준 시간 (기본 24h)")
    args = parser.parse_args()
    main(threshold_hours=args.hours)
