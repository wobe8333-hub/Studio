"""
daily_digest.py — 매일 18:00 cron 실행: 일일 운영 요약 → Slack 전송
내용: 처리된 미션·HITL 건수·월간 예산 사용률·eval regression 경고
"""
import sys
import io
import json
import os
import urllib.request
from datetime import datetime, date
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT = Path(os.environ.get("KAS_ROOT", Path(__file__).parent.parent))
TODAY = date.today().isoformat()
MONTH = date.today().strftime("%Y%m")


def load_json_safe(path: Path, default=None):
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        pass
    return default


def get_hitl_summary() -> dict:
    """오늘 HITL 신호 통계"""
    signals = load_json_safe(ROOT / "data" / "global" / "notifications" / "hitl_signals.json", [])
    if isinstance(signals, dict):
        signals = signals.get("signals", [])

    today_signals = [s for s in signals if str(s.get("created_at", ""))[:10] == TODAY]
    unresolved = [s for s in today_signals if not s.get("resolved", False)]
    return {"total": len(today_signals), "unresolved": len(unresolved)}


def get_budget_summary() -> dict:
    """이번 달 API 비용 사용률"""
    cost_data = load_json_safe(ROOT / "data" / "ops" / "agent_cost.json", {})
    summary = cost_data.get("monthly_summary", {}).get(MONTH, {})
    current = float(summary.get("total_cost_usd", 0.0))
    limit = float(os.environ.get("BUDGET_LIMIT_USD", "50.0"))
    return {"current_usd": current, "limit_usd": limit, "pct": round(current / limit * 100, 1)}


def get_eval_regressions() -> list[str]:
    """최근 eval regression 에이전트 목록"""
    regressions = []
    evals_dir = ROOT / "data" / "ops" / "evals"
    if not evals_dir.exists():
        return regressions

    for agent_dir in evals_dir.iterdir():
        results = sorted(agent_dir.glob("*.json"), reverse=True)[:3]
        scores = []
        for r in results:
            try:
                data = json.loads(r.read_text(encoding="utf-8"))
                scores.append(data.get("score", 10))
            except Exception:
                pass
        if len(scores) >= 3 and all(s < 7 for s in scores):
            regressions.append(agent_dir.name)

    return regressions


def get_routing_summary() -> dict:
    """이번 달 비용 라우팅 절감액"""
    routing = load_json_safe(ROOT / "data" / "ops" / "routing.json", {})
    stats = routing.get("monthly_stats", {}).get(MONTH, {})
    return {
        "haiku_calls": stats.get("haiku_calls", 0),
        "sonnet_calls": stats.get("sonnet_calls", 0),
        "savings_usd": round(stats.get("estimated_savings_usd", 0.0), 2)
    }


def build_message() -> str:
    hitl = get_hitl_summary()
    budget = get_budget_summary()
    regressions = get_eval_regressions()
    routing = get_routing_summary()

    budget_emoji = "🟢" if budget["pct"] < 60 else ("🟡" if budget["pct"] < 85 else "🔴")
    regression_text = (
        f"⚠️ eval regression: {', '.join(regressions)}" if regressions
        else "✅ eval regression 없음"
    )

    return (
        f"*📊 Loomix 일일 운영 요약 ({TODAY})*\n\n"
        f"🚨 HITL: 오늘 {hitl['total']}건 (미해결 {hitl['unresolved']}건)\n"
        f"{budget_emoji} API 예산: ${budget['current_usd']:.2f}/${budget['limit_usd']} "
        f"({budget['pct']}%)\n"
        f"💰 cost-router 절감: ${routing['savings_usd']} "
        f"(Haiku {routing['haiku_calls']}건 | Sonnet {routing['sonnet_calls']}건)\n"
        f"{regression_text}\n\n"
        f"→ 대시보드: http://localhost:7002"
    )


def send_to_slack(message: str) -> None:
    webhook_url = os.environ.get("SLACK_WEBHOOK_URL", "")
    if not webhook_url:
        print("SLACK_WEBHOOK_URL 미설정 — stdout 출력")
        print(message)
        return

    try:
        payload = json.dumps({"text": message}).encode("utf-8")
        req = urllib.request.Request(
            webhook_url,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=5):
            pass
        print(f"✅ Slack 전송 완료: {TODAY}")
    except Exception as e:
        print(f"⚠️ Slack 전송 실패: {e}")
        print(message)


if __name__ == "__main__":
    msg = build_message()
    send_to_slack(msg)
