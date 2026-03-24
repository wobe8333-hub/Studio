from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Optional

_KEY_RE = re.compile(r"(AIza[0-9A-Za-z\-_]{20,})")

def _repo_root() -> Path:
    # backend/knowledge_v1/secrets.py -> repo_root
    return Path(__file__).resolve().parents[2]

def load_youtube_api_key() -> str:
    """
    우선순위:
    1) ENV YOUTUBE_API_KEY
    2) backend/.env (YOUTUBE_API_KEY=...)
    3) repo_root/Youtube_API_key.txt (파일 내에서 AIza... 토큰 추출)
    """
    # 1) ENV
    k = (os.getenv("YOUTUBE_API_KEY", "") or "").strip()
    if k:
        return k

    # 2) backend/.env
    env_path = _repo_root() / "backend" / ".env"
    if env_path.exists():
        try:
            # python-dotenv 사용 (이미 requirements.txt에 포함)
            try:
                from dotenv import load_dotenv
                # 기존 환경변수 덮어쓰지 않도록 override=False
                load_dotenv(dotenv_path=env_path, override=False)
                k = (os.getenv("YOUTUBE_API_KEY", "") or "").strip()
                if k:
                    return k
            except ImportError:
                # dotenv가 없으면 수동 파싱
                txt = env_path.read_text(encoding="utf-8", errors="ignore")
                for line in txt.splitlines():
                    line = line.strip()
                    if line.startswith("#") or "=" not in line:
                        continue
                    key, val = line.split("=", 1)
                    if key.strip() == "YOUTUBE_API_KEY":
                        k = val.strip().strip('"').strip("'")
                        if k:
                            return k
        except Exception:
            pass

    # 3) Youtube_API_key.txt
    p = _repo_root() / "Youtube_API_key.txt"
    if p.exists():
        txt = p.read_text(encoding="utf-8", errors="ignore")
        m = _KEY_RE.search(txt)
        if m:
            return m.group(1).strip()

    raise RuntimeError("YOUTUBE_API_KEY not found in ENV, backend/.env, or Youtube_API_key.txt")

def redact_text(text: str) -> str:
    if not text:
        return text
    return _KEY_RE.sub("AIza***REDACTED***", text)

def safe_str(obj) -> str:
    try:
        return redact_text(str(obj))
    except Exception:
        return "<?>"

