import hashlib
import json
import os
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import filelock


def read_json(path: Path) -> dict:
    with open(path, "r", encoding="utf-8-sig") as f:
        return json.load(f)

def write_json(path: Path, data: dict, indent: int = 2) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lock = filelock.FileLock(str(path) + ".lock")
    with lock:
        # ensure_ascii=True: 한국어를 \uXXXX 이스케이프로 저장
        # → PowerShell 5.1 ConvertFrom-Json이 인코딩 무관하게 파싱 성공
        # → Python read_json은 \uXXXX를 자동으로 원문 복원
        # 원자적 쓰기: 임시 파일에 쓴 뒤 rename → 부분 쓰기로 인한 파일 손상 방지
        fd, tmp_path = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8-sig", newline="\n") as f:
                json.dump(data, f, ensure_ascii=True, indent=indent)
            os.replace(tmp_path, path)
        except Exception:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
            raise

def json_exists(path: Path) -> bool:
    return path.exists() and path.stat().st_size > 0

def parse_json_safe(path: Path) -> Optional[dict]:
    try:
        return read_json(path)
    except Exception:
        return None

def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()

def sha256_dict(data: dict) -> str:
    import copy
    cleaned = _remove_volatile(copy.deepcopy(data))
    serialized = json.dumps(cleaned, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(serialized.encode()).hexdigest()

def _remove_volatile(data: Any) -> Any:
    VOLATILE_KEYS = {"created_at", "updated_at", "assessed_at", "qa_timestamp"}
    if isinstance(data, dict):
        return {k: _remove_volatile(v) for k, v in data.items()
                if k not in VOLATILE_KEYS}
    if isinstance(data, list):
        return [_remove_volatile(i) for i in data]
    return data

def now_iso() -> str:
    return datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")

def get_run_dir(channel_id: str, run_id: str) -> Path:
    from src.core.config import RUNS_DIR
    return RUNS_DIR / channel_id / run_id

def get_channel_dir(channel_id: str) -> Path:
    from src.core.config import CHANNELS_DIR
    return CHANNELS_DIR / channel_id

