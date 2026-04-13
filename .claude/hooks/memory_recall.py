"""
memory_recall.py — SessionStart 훅: 에이전트 세션 시작 시 관련 교훈 자동 주입
에이전트명 + 현재 미션 키워드로 벡터 검색 후 상위 3개 교훈을 initialPrompt에 prepend.
"""
import sys
import io
import os
import json
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT = Path(os.environ.get("KAS_ROOT", Path(__file__).parent.parent.parent))

# scripts/memory/search.py 를 모듈로 사용
sys.path.insert(0, str(ROOT / "scripts"))

try:
    from memory.search import search_memories  # type: ignore
    HAS_SEARCH = True
except ImportError:
    HAS_SEARCH = False


def main() -> None:
    agent = os.environ.get("CLAUDE_AGENT_NAME", "")
    mission = os.environ.get("CLAUDE_INITIAL_PROMPT", "")[:200]  # 처음 200자

    if not agent or not mission or not HAS_SEARCH:
        return

    try:
        results = search_memories(agent, mission, top_k=3)
        if not results:
            return

        # 관련 교훈 출력 (Claude Code initialPrompt prepend로 자동 적용)
        print(f"\n📚 관련 과거 교훈 [{agent}]:")
        for r in results:
            preview = r["body"][:150].replace("\n", " ")
            print(f"  [{r['header']}] {preview}...")
        print()
    except Exception:
        pass  # 메모리 recall 실패는 미션 중단 사유 아님


if __name__ == "__main__":
    main()
