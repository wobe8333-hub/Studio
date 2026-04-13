"""
route_model.py — PreToolUse 훅: cost-router를 통한 모델 최적 선택 로깅
실제 model override는 Claude Code가 Agent() 호출 전 cost-router에 질의하는 방식.
이 훅은 라우팅 통계를 기록하고 고비용 패턴을 감지.
"""
import json
import os
import sys
from pathlib import Path
from datetime import datetime

sys.stdout = __import__("io").TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT = Path(os.environ.get("KAS_ROOT", Path(__file__).parent.parent.parent))
ROUTING_PATH = ROOT / "data" / "ops" / "routing.json"

# 모델별 입력 토큰 가격 ($/1M)
MODEL_PRICES = {
    "haiku": 0.25,
    "sonnet": 3.00,
    "opus": 15.00,
}

# 에이전트별 권장 모델 (cost-router 기본 매핑)
RECOMMENDED_MODEL = {
    "ceo": "sonnet", "cto": "opus", "db-architect": "opus", "qa-auditor": "sonnet",
    "backend-engineer": "sonnet", "frontend-engineer": "sonnet",
    "mlops-engineer": "sonnet", "media-engineer": "sonnet",
    "data-analyst": "haiku", "project-manager": "haiku", "customer-support": "haiku",
    "community-manager": "haiku", "content-moderator": "haiku",
    "documentation-writer": "haiku", "release-manager": "haiku",
    "performance-analyst": "haiku", "ux-auditor": "haiku", "finance-manager": "haiku",
    "legal-counsel": "haiku", "compliance-officer": "sonnet",
    "cost-router": "haiku",
    "agent-evaluator": "sonnet", "debate-facilitator": "sonnet",
    "partnerships-manager": "sonnet", "sales-manager": "sonnet",
}


def update_routing_stats(agent: str, model_used: str) -> None:
    """라우팅 통계 업데이트"""
    if not ROUTING_PATH.exists():
        return

    try:
        data = json.loads(ROUTING_PATH.read_text(encoding="utf-8"))
        month_key = datetime.now().strftime("%Y%m")

        if "monthly_stats" not in data:
            data["monthly_stats"] = {}
        if month_key not in data["monthly_stats"]:
            data["monthly_stats"][month_key] = {
                "haiku_calls": 0, "sonnet_calls": 0, "opus_calls": 0,
                "estimated_savings_usd": 0.0
            }

        stats = data["monthly_stats"][month_key]
        model_key = f"{model_used}_calls"
        if model_key in stats:
            stats[model_key] += 1

        # 비용 절감 추정: sonnet 대신 haiku 사용 시
        recommended = RECOMMENDED_MODEL.get(agent, "sonnet")
        if recommended == "haiku" and model_used == "haiku":
            # 평균 5K 토큰 절감 추정 (sonnet 대비)
            savings = 5000 / 1_000_000 * (MODEL_PRICES["sonnet"] - MODEL_PRICES["haiku"])
            stats["estimated_savings_usd"] = round(
                stats.get("estimated_savings_usd", 0.0) + savings, 4
            )

        data["last_updated"] = datetime.now().strftime("%Y-%m-%d")
        ROUTING_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception as e:
        # 라우팅 통계 실패는 파이프라인 중단 사유 아님
        pass


def main() -> None:
    agent = os.environ.get("CLAUDE_AGENT_NAME", "")
    model = os.environ.get("CLAUDE_MODEL", "sonnet").lower()

    if not agent:
        return

    recommended = RECOMMENDED_MODEL.get(agent)
    if not recommended:
        return

    update_routing_stats(agent, model)

    # 비용 초과 경고: opus를 필요 없이 사용하는 경우
    if model == "opus" and recommended in ("haiku", "sonnet"):
        print(
            f"💡 cost-router 권장: {agent}는 '{recommended}' 모델 사용을 권장합니다. "
            f"현재 '{model}' 사용 중 — 월간 비용 리뷰 시 검토됩니다."
        )


if __name__ == "__main__":
    main()
