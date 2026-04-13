"""
ab_router.py — PreToolUse 훅: 에이전트 invocation에 A/B 프롬프트 variant 확률적 적용
.claude/experiments/{exp-id}/config.json 로드 후 traffic_split에 따라 variant 선택.
"""
import json
import os
import random
import sys
from pathlib import Path

sys.stdout = __import__("io").TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT = Path(os.environ.get("KAS_ROOT", Path(__file__).parent.parent.parent))
EXPERIMENTS_DIR = ROOT / ".claude" / "experiments"
RESULTS_DIR = ROOT / "data" / "ops" / "experiments"


def get_active_experiments(agent: str) -> list[dict]:
    """해당 에이전트에 적용 가능한 활성 실험 목록"""
    if not EXPERIMENTS_DIR.exists():
        return []

    experiments = []
    from datetime import datetime, date
    today = date.today()

    for exp_dir in EXPERIMENTS_DIR.iterdir():
        config_path = exp_dir / "config.json"
        if not config_path.exists():
            continue
        try:
            config = json.loads(config_path.read_text(encoding="utf-8"))
            if config.get("agent") != agent:
                continue
            if not config.get("active", True):
                continue
            # 30일 초과 실험 자동 종료
            start = date.fromisoformat(config.get("start_date", str(today)))
            if (today - start).days > 30:
                config["active"] = False
                config_path.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")
                continue
            experiments.append({**config, "exp_id": exp_dir.name})
        except Exception:
            pass

    return experiments


def select_variant(config: dict) -> str:
    """traffic_split 기반 variant 선택 (A 또는 B)"""
    split = config.get("traffic_split", 50)
    return "a" if random.randint(1, 100) <= split else "b"


def main() -> None:
    agent = os.environ.get("CLAUDE_AGENT_NAME", "")
    if not agent:
        return

    experiments = get_active_experiments(agent)
    if not experiments:
        return

    # 첫 번째 활성 실험 적용
    exp = experiments[0]
    exp_id = exp["exp_id"]
    variant = select_variant(exp)

    variant_path = EXPERIMENTS_DIR / exp_id / f"variant_{variant}.prompt"
    if not variant_path.exists():
        return

    variant_content = variant_path.read_text(encoding="utf-8").strip()
    if variant_content:
        print(f"\n🧪 A/B 실험 [{exp_id}] variant={variant.upper()} 적용\n")
        print(f"추가 지시: {variant_content[:200]}...")

    # 결과 집계 (추후 eval_metric으로 채점)
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    result_path = RESULTS_DIR / f"{exp_id}.json"
    try:
        result = json.loads(result_path.read_text(encoding="utf-8")) if result_path.exists() else {
            "exp_id": exp_id, "agent": agent, "a_count": 0, "b_count": 0
        }
        result[f"{variant}_count"] = result.get(f"{variant}_count", 0) + 1
        result_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass


if __name__ == "__main__":
    main()
