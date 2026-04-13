"""
shadow_mode.py — PreToolUse 훅: Shadow 모드 에이전트의 Write/Edit 차단
신규 에이전트 14일 수습 기간 중 실제 파일 수정 대신 cto에게 제안만 허용.
환경변수 CLAUDE_AGENT_NAME이 shadow 목록에 있으면 Write/Edit 차단.
"""
import json
import os
import sys
from pathlib import Path

sys.stdout = __import__("io").TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT = Path(os.environ.get("KAS_ROOT", Path(__file__).parent.parent.parent))
SHADOW_LIST_PATH = ROOT / ".claude" / "lifecycle" / "shadow_agents.json"


def load_shadow_agents() -> list[str]:
    """수습 중인 에이전트 목록 로드"""
    if not SHADOW_LIST_PATH.exists():
        return []
    try:
        data = json.loads(SHADOW_LIST_PATH.read_text(encoding="utf-8"))
        return data.get("agents", [])
    except Exception:
        return []


def main() -> None:
    agent = os.environ.get("CLAUDE_AGENT_NAME", "")
    tool = os.environ.get("CLAUDE_TOOL_NAME", "")

    if not agent or tool not in ("Write", "Edit"):
        return  # 차단 대상 아님

    shadow_agents = load_shadow_agents()
    if agent not in shadow_agents:
        return  # Shadow 모드 아님

    # 차단: cto에게 제안 안내
    print(f"⚠️ SHADOW MODE: {agent}는 수습 기간 중입니다.")
    print(f"   {tool} 도구 사용이 차단되었습니다.")
    print(f"   대신 cto에게 SendMessage로 변경 제안을 전달하세요.")
    print(f"   14일 수습 종료 후 eval ≥7 확인 시 Active 전환됩니다.")
    sys.exit(1)  # 훅 차단


if __name__ == "__main__":
    main()
