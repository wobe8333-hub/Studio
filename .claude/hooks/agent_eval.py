"""
agent_eval.py — SubagentStop 훅: 에이전트 세션 종료 시 golden test 자동 채점
LLM-as-judge 패턴. 점수 < 7 3연속 → cto 알림 (data/global/notifications/hitl_signals.json)
"""
import json
import os
import sys
import random
import logging
from datetime import datetime
from pathlib import Path

# Windows 인코딩 안전 처리
sys.stdout = __import__("io").TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT = Path(os.environ.get("KAS_ROOT", Path(__file__).parent.parent.parent))
EVALS_DIR = ROOT / ".claude" / "evals"
RESULTS_DIR = ROOT / "data" / "ops" / "evals"
HITL_PATH = ROOT / "data" / "global" / "notifications" / "hitl_signals.json"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def load_golden_tests(agent_name: str) -> list[dict]:
    """에이전트별 golden.jsonl 로드"""
    golden_path = EVALS_DIR / agent_name / "golden.jsonl"
    if not golden_path.exists():
        return []
    tests = []
    with open(golden_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                tests.append(json.loads(line))
    return tests


def score_output(test: dict, session_summary: str) -> dict:
    """
    LLM-as-judge 채점 (현재: 규칙 기반 휴리스틱 — Gemini API 연동 시 교체 예정)
    실제 배포 시: Gemini API로 세션 요약 vs judge_criteria 비교
    """
    score = 7  # 기본 점수

    criteria = test.get("judge_criteria", "")
    expected_tools = test.get("expected_tools", [])

    # 기대 도구 사용 체크 (세션 요약에서 도구명 탐색)
    tool_hits = sum(1 for t in expected_tools if t.lower() in session_summary.lower())
    if expected_tools:
        tool_ratio = tool_hits / len(expected_tools)
        score += int(tool_ratio * 2)  # 최대 +2

    # SSOT 준수 여부
    if "ssot" in criteria.lower() and "read_json" not in session_summary.lower():
        score -= 1

    # 역할 경계 준수 (금지 경로 접근 감지)
    if "web/" in session_summary and "backend-engineer" in test.get("id", ""):
        score -= 2

    score = max(0, min(10, score))

    return {
        "test_id": test["id"],
        "score": score,
        "criteria": criteria,
        "notes": f"tool_hits={tool_hits}/{len(expected_tools)}"
    }


def check_regression(agent_name: str, new_score: int) -> bool:
    """최근 3회 점수 확인 → 연속 < 7이면 True"""
    result_dir = RESULTS_DIR / agent_name
    if not result_dir.exists():
        return False

    results = sorted(result_dir.glob("*.json"), reverse=True)[:3]
    recent_scores = [new_score]

    for r in results[:2]:
        try:
            data = json.loads(r.read_text(encoding="utf-8"))
            recent_scores.append(data.get("score", 10))
        except Exception:
            pass

    return all(s < 7 for s in recent_scores) and len(recent_scores) >= 3


def write_hitl_signal(agent_name: str, avg_score: float) -> None:
    """cto 에스컬레이션 HITL 신호 기록"""
    if not HITL_PATH.parent.exists():
        return

    try:
        if HITL_PATH.exists():
            signals = json.loads(HITL_PATH.read_text(encoding="utf-8"))
            if not isinstance(signals, list):
                signals = []
        else:
            signals = []

        seq = len(signals) + 1
        today = datetime.now().strftime("%Y-%m-%d")
        signals.append({
            "id": f"hitl-{today}-{seq:03d}",
            "type": "eval_regression",
            "severity": "medium",
            "triggered_by": "agent-evaluator",
            "escalated_to": "cto",
            "message": f"{agent_name} eval 점수 3연속 <7 (최근 평균 {avg_score:.1f}) — 에이전트 검토 필요",
            "resolved": False,
            "created_at": datetime.now().isoformat()
        })

        HITL_PATH.write_text(json.dumps(signals, ensure_ascii=False, indent=2), encoding="utf-8")
        logger.info(f"HITL 신호 기록: eval_regression for {agent_name}")
    except Exception as e:
        logger.warning(f"HITL 신호 기록 실패: {e}")


def run_eval(agent_name: str) -> None:
    """에이전트 eval 실행 진입점"""
    tests = load_golden_tests(agent_name)
    if not tests:
        logger.info(f"{agent_name}: golden.jsonl 없음 — eval 스킵")
        return

    # 랜덤 1건 선택
    test = random.choice(tests)

    # 세션 요약 (현재는 환경변수 또는 stdin에서 받음 — 향후 hook context 연동)
    session_summary = os.environ.get("CLAUDE_SESSION_SUMMARY", "")

    result = score_output(test, session_summary)
    result["agent"] = agent_name
    result["timestamp"] = datetime.now().isoformat()

    # 결과 저장
    result_dir = RESULTS_DIR / agent_name
    result_dir.mkdir(parents=True, exist_ok=True)
    date_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    result_path = result_dir / f"{date_str}.json"
    result_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    logger.info(f"Eval [{agent_name}] test={test['id']} score={result['score']}/10")

    # Regression 체크
    if check_regression(agent_name, result["score"]):
        recent_scores = [result["score"]]
        for r in sorted(result_dir.glob("*.json"), reverse=True)[:2]:
            try:
                data = json.loads(r.read_text(encoding="utf-8"))
                recent_scores.append(data.get("score", 10))
            except Exception:
                pass
        avg = sum(recent_scores) / len(recent_scores)
        write_hitl_signal(agent_name, avg)
        logger.warning(f"REGRESSION: {agent_name} 3연속 <7 → cto 에스컬레이션")


if __name__ == "__main__":
    # SubagentStop 훅에서 CLAUDE_AGENT_NAME 환경변수 또는 stdin으로 에이전트명 전달
    agent = os.environ.get("CLAUDE_AGENT_NAME", "")
    if not agent and len(sys.argv) > 1:
        agent = sys.argv[1]

    if agent:
        run_eval(agent)
    else:
        logger.info("CLAUDE_AGENT_NAME 미설정 — eval 스킵 (non-agent context)")
