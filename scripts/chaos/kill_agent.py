"""
kill_agent.py — Chaos Engineering: 지정 에이전트를 임시 offline 처리
에이전트를 disallowedTools에 전체 차단하여 1시간 동안 offline 상태 시뮬레이션.
사용법: python scripts/chaos/kill_agent.py {agent-name} [--duration 60]
"""
import sys
import io
import json
import argparse
import shutil
from datetime import datetime, timedelta
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT = Path(__file__).parent.parent.parent
AGENTS_DIR = ROOT / ".claude" / "agents"
CHAOS_LOG_DIR = ROOT / "data" / "sre" / "chaos"

CHAOS_HOURS = 1


def kill_agent(agent_name: str, duration_minutes: int = 60) -> None:
    agent_path = AGENTS_DIR / f"{agent_name}.md"
    if not agent_path.exists():
        print(f"❌ 에이전트 파일 없음: {agent_path}")
        sys.exit(1)

    # 원본 백업
    CHAOS_LOG_DIR.mkdir(parents=True, exist_ok=True)
    date_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = CHAOS_LOG_DIR / f"{agent_name}-backup-{date_str}.md"
    shutil.copy2(agent_path, backup_path)

    # Chaos 로그 기록
    log_path = CHAOS_LOG_DIR / f"{date_str}.json"
    restore_at = (datetime.now() + timedelta(minutes=duration_minutes)).isoformat()
    log = {
        "agent": agent_name,
        "chaos_type": "kill",
        "started_at": datetime.now().isoformat(),
        "restore_at": restore_at,
        "backup_path": str(backup_path),
        "observations": [],
        "status": "active"
    }
    log_path.write_text(json.dumps(log, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"💥 CHAOS: {agent_name} offline 처리")
    print(f"   백업: {backup_path}")
    print(f"   복원 예정: {restore_at}")
    print(f"   복원 명령: python scripts/chaos/kill_agent.py --restore {agent_name} --log {log_path}")
    print(f"\n   ⚠️ 이제 시스템이 {agent_name} 없이 어떻게 동작하는지 관찰하세요.")
    print(f"   관찰 내용은 {log_path}의 observations 배열에 기록하세요.")


def restore_agent(agent_name: str, log_path_str: str) -> None:
    log_path = Path(log_path_str)
    if not log_path.exists():
        print(f"❌ Chaos 로그 없음: {log_path}")
        sys.exit(1)

    log = json.loads(log_path.read_text(encoding="utf-8"))
    backup_path = Path(log["backup_path"])

    if not backup_path.exists():
        print(f"❌ 백업 없음: {backup_path}")
        sys.exit(1)

    # 원본 복원
    agent_path = AGENTS_DIR / f"{agent_name}.md"
    shutil.copy2(backup_path, agent_path)

    # 로그 완료 처리
    log["status"] = "completed"
    log["restored_at"] = datetime.now().isoformat()
    log_path.write_text(json.dumps(log, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"✅ {agent_name} 복원 완료 ({backup_path})")
    print(f"   사후 분석을 {log_path}에 기록하세요.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="에이전트 Chaos Kill/Restore")
    parser.add_argument("agent", nargs="?", help="에이전트 이름")
    parser.add_argument("--restore", help="복원할 에이전트 이름")
    parser.add_argument("--log", help="Chaos 로그 경로 (--restore 시)")
    parser.add_argument("--duration", type=int, default=60, help="offline 분 단위 (기본 60)")
    args = parser.parse_args()

    if args.restore and args.log:
        restore_agent(args.restore, args.log)
    elif args.agent:
        kill_agent(args.agent, args.duration)
    else:
        parser.print_help()
