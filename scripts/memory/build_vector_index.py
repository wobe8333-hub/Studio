"""
build_vector_index.py — MEMORY.md → SQLite 벡터 인덱스 빌드 (numpy 기반)
에이전트별 ~/.claude/agent-memory/{agent}/MEMORY.md를 임베딩하여
의미 검색 가능한 SQLite DB로 변환.

의존성: sentence-transformers (numpy는 자동 포함)
설치: pip install sentence-transformers
sqlite-vss는 Windows 미지원 → numpy 코사인 유사도로 대체
"""
import sys
import io
import json
import sqlite3
import re
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

MEMORY_BASE = Path.home() / ".claude" / "agent-memory"
INDEX_PATH = MEMORY_BASE / "vector_index.db"

try:
    from sentence_transformers import SentenceTransformer  # type: ignore
    MODEL = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")
    HAS_EMBED = True
    print("✅ sentence-transformers 로드 완료 (다국어 MiniLM-L12)")
except (ImportError, OSError, Exception) as _e:
    HAS_EMBED = False
    print(f"⚠️ sentence-transformers 로드 실패 ({type(_e).__name__}) — 텍스트 검색 모드로 fallback")


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
    """DB 스키마 초기화 — embedding은 JSON TEXT로 저장"""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS memories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            agent TEXT NOT NULL,
            header TEXT,
            body TEXT NOT NULL,
            source TEXT,
            embedding TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()


def build_index() -> int:
    """전체 MEMORY.md 파일을 인덱싱"""
    if not MEMORY_BASE.exists():
        print(f"메모리 디렉토리 없음: {MEMORY_BASE}")
        print("에이전트 MEMORY.md가 생성되면 다시 실행하세요.")
        return 0

    MEMORY_BASE.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(INDEX_PATH))
    init_db(conn)

    # 기존 데이터 초기화 (재빌드)
    conn.execute("DELETE FROM memories")
    conn.commit()

    total = 0
    for agent_dir in sorted(MEMORY_BASE.iterdir()):
        if not agent_dir.is_dir():
            continue
        memory_path = agent_dir / "MEMORY.md"
        if not memory_path.exists():
            continue

        chunks = parse_memory_file(memory_path)
        for chunk in chunks:
            embedding_json = None
            if HAS_EMBED:
                try:
                    vec = MODEL.encode(chunk["body"], show_progress_bar=False).tolist()
                    embedding_json = json.dumps(vec)
                except Exception as e:
                    print(f"  임베딩 실패 ({chunk['agent']}): {e}")

            conn.execute(
                "INSERT INTO memories (agent, header, body, source, embedding) VALUES (?,?,?,?,?)",
                (chunk["agent"], chunk["header"], chunk["body"],
                 chunk["source"], embedding_json)
            )
            total += 1

    conn.commit()
    conn.close()

    mode = "의미 벡터" if HAS_EMBED else "텍스트"
    print(f"✅ {mode} 인덱스 빌드 완료: {total}건 → {INDEX_PATH}")
    return total


if __name__ == "__main__":
    build_index()
