import json, hashlib, time
from pathlib import Path
from src.core.ssot import read_json, write_json, json_exists
from src.core.config import CACHE_DIR
from src.quota.gemini_quota import record_cache_hit, record_cache_miss

CACHE_FILE = CACHE_DIR / "gemini_cache.json"
HIT_LOG    = CACHE_DIR / "cache_hit_log.jsonl"
TTL_HOURS  = 24
CACHEABLE_TYPES = ["system_prompt", "style_template", "affiliate_insert_template"]

def _load_cache() -> dict:
    if not json_exists(CACHE_FILE):
        return {}
    return read_json(CACHE_FILE)

def _save_cache(cache: dict) -> None:
    write_json(CACHE_FILE, cache)

def _make_key(prompt_type: str, content: str) -> str:
    return hashlib.sha256(f"{prompt_type}::{content}".encode()).hexdigest()[:16]

def get(prompt_type: str, content: str):
    if prompt_type not in CACHEABLE_TYPES:
        return None
    cache = _load_cache()
    key   = _make_key(prompt_type, content)
    entry = cache.get(key)
    if not entry:
        record_cache_miss(); return None
    if time.time() - entry["created_at"] > TTL_HOURS * 3600:
        del cache[key]; _save_cache(cache); record_cache_miss(); return None
    record_cache_hit(cost_saved_krw=entry.get("cost_saved_krw", 0.0))
    with open(HIT_LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps({"key": key, "type": prompt_type, "ts": time.time()}) + "\n")
    return entry["response"]

def set(prompt_type: str, content: str, response: str, cost_krw: float = 0.0) -> None:
    if prompt_type not in CACHEABLE_TYPES:
        return
    cache = _load_cache()
    key   = _make_key(prompt_type, content)
    cache[key] = {
        "prompt_type": prompt_type, "created_at": time.time(),
        "response": response, "cost_saved_krw": cost_krw,
    }
    _save_cache(cache)

def invalidate_expired() -> int:
    cache = _load_cache()
    expired = [k for k, v in cache.items()
               if time.time() - v["created_at"] > TTL_HOURS * 3600]
    for k in expired:
        del cache[k]
    _save_cache(cache)
    return len(expired)

