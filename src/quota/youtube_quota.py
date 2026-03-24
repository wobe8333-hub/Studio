# STEP 00 — YouTube Data API v3 쿼터 관리
from src.core.ssot import read_json, write_json, now_iso, json_exists
from src.core.config import QUOTA_DIR
import logging

QUOTA_FILE       = QUOTA_DIR / "youtube_quota_daily.json"
DAILY_LIMIT      = 10000
WARNING_THRESHOLD= 8000
BLOCK_THRESHOLD  = 9500
UPLOAD_COST      = 1700

logger = logging.getLogger(__name__)

def _init_quota_file() -> dict:
    data = {
        "date": now_iso()[:10],
        "quota_used": 0,
        "quota_limit": DAILY_LIMIT,
        "quota_remaining": DAILY_LIMIT,
        "usage_by_operation": {
            "uploads": 0, "metadata_updates": 0,
            "thumbnail_sets": 0, "search_calls": 0, "other": 0,
        },
        "warning_triggered": False,
        "block_triggered": False,
        "deferred_jobs": [],
    }
    write_json(QUOTA_FILE, data)
    return data

def get_quota() -> dict:
    if not json_exists(QUOTA_FILE):
        return _init_quota_file()
    data = read_json(QUOTA_FILE)
    if data.get("date") != now_iso()[:10]:
        return _init_quota_file()
    return data

def consume(units: int, operation: str = "other") -> bool:
    data = get_quota()
    if data["quota_used"] + units > BLOCK_THRESHOLD:
        data["block_triggered"] = True
        write_json(QUOTA_FILE, data)
        logger.error(f"[STEP00] YOUTUBE_QUOTA_BLOCK: {data['quota_used']+units} > {BLOCK_THRESHOLD}")
        return False
    data["quota_used"] += units
    data["quota_remaining"] = data["quota_limit"] - data["quota_used"]
    op_key = operation if operation in data["usage_by_operation"] else "other"
    data["usage_by_operation"][op_key] += units
    if data["quota_used"] >= WARNING_THRESHOLD and not data["warning_triggered"]:
        data["warning_triggered"] = True
        logger.warning(f"[STEP00] YOUTUBE_QUOTA_WARNING: {data['quota_used']}/{DAILY_LIMIT}")
    write_json(QUOTA_FILE, data)
    return True

def can_upload() -> bool:
    return get_quota()["quota_remaining"] >= UPLOAD_COST

def defer_job(run_id: str, channel_id: str) -> None:
    data = get_quota()
    data["deferred_jobs"].append({
        "run_id": run_id, "channel_id": channel_id, "deferred_at": now_iso()
    })
    write_json(QUOTA_FILE, data)

