import uuid
from pathlib import Path
from src.core.ssot import read_json, write_json, now_iso, json_exists
from src.core.config import RUNS_DIR

def create_run_id() -> str:
    return now_iso()[:10].replace("-", "") + "_" + uuid.uuid4().hex[:8]

def init_manifest(channel_id: str, run_id: str, topic: str) -> dict:
    run_dir = RUNS_DIR / channel_id / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    manifest = {
        "schema_version": "1.0",
        "channel_id": channel_id,
        "run_id": run_id,
        "topic": topic,
        "created_at": now_iso(),
        "status": "INIT",
        "steps_completed": [],
        "steps_failed": [],
        "failure_type": None,
        "failure_detail": None,
        "resume_from": None,
    }
    write_json(run_dir / "manifest.json", manifest)
    return manifest

def load_manifest(channel_id: str, run_id: str) -> dict:
    p = RUNS_DIR / channel_id / run_id / "manifest.json"
    if not json_exists(p):
        raise FileNotFoundError(f"manifest.json not found: {channel_id}/{run_id}")
    return read_json(p)

def update_manifest(channel_id: str, run_id: str, **kwargs) -> dict:
    p = RUNS_DIR / channel_id / run_id / "manifest.json"
    data = read_json(p)
    data.update(kwargs)
    data["updated_at"] = now_iso()
    write_json(p, data)
    return data

def mark_step_done(channel_id: str, run_id: str, step: str) -> None:
    data = load_manifest(channel_id, run_id)
    if step not in data["steps_completed"]:
        data["steps_completed"].append(step)
    update_manifest(channel_id, run_id, **data)

def mark_step_failed(channel_id: str, run_id: str,
                     step: str, failure_type: str, detail: str) -> None:
    data = load_manifest(channel_id, run_id)
    if step not in data["steps_failed"]:
        data["steps_failed"].append(step)
    data["status"] = "FAILED"
    data["failure_type"] = failure_type
    data["failure_detail"] = detail
    data["resume_from"] = step
    update_manifest(channel_id, run_id, **data)

