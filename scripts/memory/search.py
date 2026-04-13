"""
search.py — 에이전트 메모리 의미 검색 CLI
사용법: python scripts/memory/search.py {agent} "{query}" [--top-k 3]
예: python scripts/memory/search.py backend-engineer "FFmpeg 타임아웃"
"""
import sys
import io
import json
import sqlite3
import argparse
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

MEMORY_BASE = Path.home() / ".claude" / "agent-memory"
INDEX_PATH = MEMORY_BASE / "vector_index.db"

try:
    import sqlite_vss  # type: ignore
    HAS_VSS = True
except ImportError:
    HAS_VSS = False

try:
    from sentence_transformers import SentenceTransformer  # type: ignore
    MODEL = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")
    HAS_EMBED = True
except ImportError:
    HAS_EMBED = False


def search_memories(agent: str, query: str, top_k: int = 3) -> list[dict]:
    """의미 검색 또는 텍스트 LIKE 검색"""
    if not INDEX_PATH.exists():
        print(f"인덱스 없음: {INDEX_PATH}\n먼저 scripts/memory/build_vector_index.py를 실행하세요.")
        return []

    conn = sqlite3.connect(str(INDEX_PATH))

    results = []

    if HAS_VSS and HAS_EMBED:
        # 벡터 의미 검색
        if HAS_VSS:
            sqlite_vss.load(conn)
        embedding = MODEL.encode(query, show_progress_bar=False).tolist()
        rows = conn.execute("""
            SELECT m.agent, m.header, m.body, vss_distance_l2(v.embedding, ?) as dist
            FROM vss_memories v
            JOIN memories m ON v.rowid = m.id
            WHERE m.agent = ? OR ? = '*'
            ORDER BY dist ASC
            LIMIT ?
        """, (json.dumps(embedding), agent, agent, top_k)).fetchall()

        for row in rows:
            results.append({
                "agent": row[0], "header": row[1],
                "body": row[2], "score": round(1 / (1 + row[3]), 3)
            })
    else:
        # 텍스트 LIKE 검색 (fallback)
        like = f"%{query}%"
        rows = conn.execute("""
            SELECT agent, header, body
            FROM memories
            WHERE (agent = ? OR ? = '*') AND body LIKE ?
            LIMIT ?
        """, (agent, agent, like, top_k)).fetchall()

        for row in rows:
            results.append({"agent": row[0], "header": row[1], "body": row[2], "score": 1.0})

    conn.close()
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description="에이전트 메모리 의미 검색")
    parser.add_argument("agent", help="에이전트명 또는 '*' (전체)")
    parser.add_argument("query", help="검색어")
    parser.add_argument("--top-k", type=int, default=3, help="반환 결과 수")
    args = parser.parse_args()

    results = search_memories(args.agent, args.query, args.top_k)

    if not results:
        print(f"'{args.query}' 검색 결과 없음 (agent={args.agent})")
        return

    print(f"\n=== 검색 결과 [{args.agent}] '{args.query}' ===\n")
    for i, r in enumerate(results, 1):
        print(f"[{i}] {r['agent']} — {r['header']} (score={r['score']})")
        body_preview = r["body"][:200].replace("\n", " ")
        print(f"    {body_preview}...")
        print()


if __name__ == "__main__":
    main()
