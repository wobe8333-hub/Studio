"""
build_vector_index.py — MEMORY.md → sqlite-vss 벡터 인덱스 빌드
에이전트별 ~/.claude/agent-memory/{agent}/MEMORY.md를 임베딩하여
의미 검색 가능한 SQLite DB로 변환.

의존성: sqlite-vss, sentence-transformers
설치: pip install sqlite-vss sentence-transformers
"""
import sys
import io
import os
import re
import json
import sqlite3
from pathlib import Path
from datetime import datetime

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

MEMORY_BASE = Path.home() / ".claude" / "agent-memory"
INDEX_PATH = MEMORY_BASE / "vector_index.db"

try:
    import sqlite_vss  # type: ignore
    HAS_VSS = True
except ImportError:
    HAS_VSS = False
    print("⚠️ sqlite-vss 미설치. 텍스트 검색 모드로 fallback.")

try:
    from sentence_transformers import SentenceTransformer  # type: ignore
    MODEL = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")
    HAS_EMBED = True
except ImportError:
    HAS_EMBED = False
    print("⚠️ sentence-transformers 미설치. 임베딩 없이 메타데이터만 저장.")


def parse_memory_file(path: Path) -> list[dict]:
    """MEMORY.md를 개별 교훈 단위로 파싱"""
    if not path.exists():
        return []

    content = path.read_text(encoding="utf-8", errors="replace")
    chunks = []

    # ## 날짜 세션 교훈 패턴으로 분할
    sections = re.split(r"\n## ", content)
    for section in sections[1:]:
        lines = section.strip().split("\n")
        header = lines[0] if lines else ""
        body = "\n".join(lines[1:]).strip()
        if body:
            chunks.append({
                "header": header,
                "body": body,
                "agent": path.parent.name,
                "source": str(path),
            })

    # 분할 불가 시 전체를 하나의 청크로
    if not chunks and content.strip():
        chunks.append({
            "header": "전체",
            "body": content.strip(),
            "agent": path.parent.name,
            "source": str(path),
        })

    return chunks


def init_db(conn: sqlite3.Connection) -> None:
    """DB 스키마 초기화"""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS memories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            agent TEXT NOT NULL,
            header TEXT,
            body TEXT NOT NULL,
            source TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    if HAS_VSS:
        sqlite_vss.load(conn)
        conn.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS vss_memories
            USING vss0(embedding(384))
        """)

    conn.commit()


def embed_text(text: str) -> list[float] | None:
    """텍스트 임베딩 생성"""
    if not HAS_EMBED:
        return None
    try:
        return MODEL.encode(text, show_progress_bar=False).tolist()
    except Exception as e:
        print(f"  임베딩 실패: {e}")
        return None


def build_index() -> int:
    """전체 MEMORY.md 파일을 인덱싱"""
    if not MEMORY_BASE.exists():
        print(f"메모리 디렉토리 없음: {MEMORY_BASE}")
        return 0

    conn = sqlite3.connect(str(INDEX_PATH))
    init_db(conn)

    total = 0
    for agent_dir in sorted(MEMORY_BASE.iterdir()):
        memory_path = agent_dir / "MEMORY.md"
        if not memory_path.exists():
            continue

        chunks = parse_memory_file(memory_path)
        for chunk in chunks:
            cursor = conn.execute(
                "INSERT INTO memories (agent, header, body, source) VALUES (?,?,?,?)",
                (chunk["agent"], chunk["header"], chunk["body"], chunk["source"])
            )
            row_id = cursor.lastrowid

            if HAS_VSS:
                embedding = embed_text(chunk["body"])
                if embedding:
                    conn.execute(
                        "INSERT INTO vss_memories(rowid, embedding) VALUES (?, ?)",
                        (row_id, json.dumps(embedding))
                    )
            total += 1

    conn.commit()
    conn.close()
    print(f"✅ 인덱스 빌드 완료: {total}건 → {INDEX_PATH}")
    return total


if __name__ == "__main__":
    build_index()
