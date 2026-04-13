"""
search.py — 에이전트 메모리 의미 검색 CLI (numpy 코사인 유사도)
사용법: python scripts/memory/search.py {agent} "{query}" [--top-k 3]
예: python scripts/memory/search.py backend-engineer "FFmpeg 타임아웃"
     python scripts/memory/search.py "*" "SSOT 위반"
sqlite-vss 없이 numpy 코사인 유사도로 작동 (Windows 완전 지원)
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
    from sentence_transformers import SentenceTransformer  # type: ignore
    import numpy as np  # type: ignore
    MODEL = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")
    HAS_EMBED = True
except (ImportError, OSError, Exception):
    HAS_EMBED = False


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """코사인 유사도 계산"""
    import numpy as np
    va = np.array(a, dtype=np.float32)
    vb = np.array(b, dtype=np.float32)
    dot = np.dot(va, vb)
    norm = np.linalg.norm(va) * np.linalg.norm(vb)
    if norm == 0:
        return 0.0
    return float(dot / norm)


def search_memories(agent: str, query: str, top_k: int = 3) -> list[dict]:
    """의미 검색 (벡터) 또는 텍스트 LIKE 검색"""
    if not INDEX_PATH.exists():
        print(f"인덱스 없음: {INDEX_PATH}")
        print("먼저 실행: python scripts/memory/build_vector_index.py")
        return []

    conn = sqlite3.connect(str(INDEX_PATH))

    if agent == "*":
        rows = conn.execute(
            "SELECT id, agent, header, body, embedding FROM memories"
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT id, agent, header, body, embedding FROM memories WHERE agent = ?",
            (agent,)
        ).fetchall()

    conn.close()

    if not rows:
        return []

    results = []

    if HAS_EMBED:
        # 벡터 코사인 유사도 검색
        query_vec = MODEL.encode(query, show_progress_bar=False).tolist()
        scored = []
        for row in rows:
            row_id, ag, header, body, emb_json = row
            if emb_json is None:
                continue
            try:
                emb = json.loads(emb_json)
                score = cosine_similarity(query_vec, emb)
                scored.append((score, ag, header, body))
            except Exception:
                continue

        scored.sort(key=lambda x: x[0], reverse=True)
        for score, ag, header, body in scored[:top_k]:
            results.append({
                "agent": ag, "header": header,
                "body": body, "score": round(score, 3)
            })
    else:
        # 텍스트 LIKE fallback
        for row in rows:
            _, ag, header, body, _ = row
            if query.lower() in body.lower():
                results.append({"agent": ag, "header": header, "body": body, "score": 1.0})
        results = results[:top_k]

    return results


def main() -> None:
    parser = argparse.ArgumentParser(description="에이전트 메모리 의미 검색")
    parser.add_argument("agent", help="에이전트명 또는 '*' (전체 검색)")
    parser.add_argument("query", help="검색어 (한국어 지원)")
    parser.add_argument("--top-k", type=int, default=3, help="반환 결과 수 (기본 3)")
    args = parser.parse_args()

    results = search_memories(args.agent, args.query, args.top_k)

    if not results:
        print(f"'{args.query}' 검색 결과 없음 (agent={args.agent})")
        return

    mode = "벡터 유사도" if HAS_EMBED else "텍스트 검색"
    print(f"\n=== [{mode}] {args.agent} | '{args.query}' ===\n")
    for i, r in enumerate(results, 1):
        print(f"[{i}] {r['agent']} — {r['header']} (score={r['score']})")
        body_preview = r["body"][:200].replace("\n", " ")
        print(f"    {body_preview}...")
        print()


if __name__ == "__main__":
    main()
