"""
rate_limiter.py — PreToolUse 훅: 에이전트당 세션 내 도구 호출 횟수 제한
무한 루프·maxTurns 미설정 상황 대비 safety net.
"""
import json
import os
import sys
from pathlib import Path

sys.stdout = __import__("io").TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT = Path(os.environ.get("KAS_ROOT", Path(__file__).parent.parent.parent))
RATE_LOG = ROOT / "data" / "ops" / "rate_limit_log.json"

# 에이전트별 세션당 최대 Write/Edit 호출 수 (과도한 파일 수정 방지)
WRITE_EDIT_LIMIT = int(os.environ.get("AGENT_WRITE_LIMIT", "50"))


def main() -> None:
    agent = os.environ.get("CLAUDE_AGENT_NAME", "")
    session_id = os.environ.get("CLAUDE_SESSION_ID", "unknown")
    tool = os.environ.get("CLAUDE_TOOL_NAME", "")

    if not agent or tool not in ("Write", "Edit"):
        return

    # 현재 세션 호출 수 추적
    try:
        log = json.loads(RATE_LOG.read_text(encoding="utf-8")) if RATE_LOG.exists() else {}
        session_key = f"{agent}:{session_id}"
        count = log.get(session_key, 0) + 1
        log[session_key] = count

        if count > WRITE_EDIT_LIMIT:
            print(
                f"⚠️ RATE LIMIT: {agent}가 이번 세션에서 {count}/{WRITE_EDIT_LIMIT}회 "
                f"Write/Edit 호출. maxTurns 설정을 확인하거나 cto에게 에스컬레이션하세요."
            )
            # 경고만, 차단하지 않음 (에이전트 자율성 존중)

        RATE_LOG.parent.mkdir(parents=True, exist_ok=True)
        RATE_LOG.write_text(json.dumps(log, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass


if __name__ == "__main__":
    main()
