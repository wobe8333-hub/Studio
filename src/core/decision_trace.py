from pathlib import Path
from src.core.ssot import read_json, write_json, now_iso, json_exists

def append_trace(trace_path: Path, event: str, detail: dict) -> None:
    data = {}
    if json_exists(trace_path):
        data = read_json(trace_path)
    if "events" not in data:
        data["events"] = []
    data["events"].append({
        "timestamp": now_iso(),
        "event": event,
        "detail": detail,
    })
    write_json(trace_path, data)

def get_trace(trace_path: Path) -> dict:
    if not json_exists(trace_path):
        return {"events": []}
    return read_json(trace_path)

