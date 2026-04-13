"""
budget_guard.py — PreToolUse 훅: 월간 API 예산 초과 시 비고위험 에이전트 차단
BUDGET_LIMIT_USD($50) 초과 시 HIGH 에이전트(ceo/cto/db-architect/qa-auditor/sre-engineer)만 허용.
나머지 차단 + ceo HITL 알림.
"""
import json
import os
import sys
from datetime import datetime
from pathlib import Path

sys.stdout = __import__("io").TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT = Path(os.environ.get("KAS_ROOT", Path(__file__).parent.parent.parent))
COST_PATH = ROOT / "data" / "ops" / "agent_cost.json"
HITL_PATH = ROOT / "data" / "global" / "notifications" / "hitl_signals.json"

BUDGET_LIMIT = float(os.environ.get("BUDGET_LIMIT_USD", "50.0"))

# 예산 초과 시에도 허용할 고중요도 에이전트
HIGH_PRIORITY_AGENTS = {
    "ceo", "cto", "db-architect", "qa-auditor", "sre-engineer",
    "security-engineer", "compliance-officer"
}


def get_monthly_cost() -> float:
    """이번 달 누적 API 비용 조회"""
    if not COST_PATH.exists():
        return 0.0
    try:
        data = json.loads(COST_PATH.read_text(encoding="utf-8"))
        month_key = datetime.now().strftime("%Y%m")
        summary = data.get("monthly_summary", {}).get(month_key, {})
        return float(summary.get("total_cost_usd", 0.0))
    except Exception:
        return 0.0


def write_hitl_budget_signal(current_cost: float) -> None:
    """예산 초과 ceo HITL 신호 기록 (중복 방지: 하루 1회)"""
    if not HITL_PATH.parent.exists():
        return
    try:
        signals = json.loads(HITL_PATH.read_text(encoding="utf-8")) if HITL_PATH.exists() else []
        if not isinstance(signals, list):
            signals = []

        today = datetime.now().strftime("%Y-%m-%d")
        # 오늘 이미 같은 유형 신호가 있으면 스킵
        if any(
            s.get("type") == "budget_exceeded" and s.get("created_at", "")[:10] == today
            for s in signals
        ):
            return

        signals.append({
            "id": f"hitl-{today}-budget",
            "type": "budget_exceeded",
            "severity": "high",
            "triggered_by": "budget-guard-hook",
            "escalated_to": "ceo",
            "message": f"월간 API 비용 ${current_cost:.2f} > ${BUDGET_LIMIT} 한도 초과. 비고위험 에이전트 차단 중.",
            "resolved": False,
            "created_at": datetime.now().isoformat()
        })
        HITL_PATH.write_text(json.dumps(signals, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass


def main() -> None:
    agent = os.environ.get("CLAUDE_AGENT_NAME", "")
    if not agent:
        return  # 에이전트 컨텍스트 아님

    current_cost = get_monthly_cost()
    if current_cost <= BUDGET_LIMIT:
        return  # 예산 범위 내

    if agent in HIGH_PRIORITY_AGENTS:
        return  # 고중요도 에이전트는 허용

    # 차단
    write_hitl_budget_signal(current_cost)
    print(f"🚫 BUDGET GUARD: 월간 API 비용 ${current_cost:.2f}가 한도 ${BUDGET_LIMIT}를 초과했습니다.")
    print(f"   {agent} 작업이 차단되었습니다.")
    print(f"   ceo HITL 승인 후 재개 가능합니다. (data/global/notifications/hitl_signals.json)")
    sys.exit(1)


if __name__ == "__main__":
    main()
