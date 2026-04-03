import time
from loguru import logger
from src.core.ssot import read_json, write_json, now_iso, json_exists
from src.core.config import QUOTA_DIR

QUOTA_FILE        = QUOTA_DIR / "gemini_quota_daily.json"
RPM_LIMIT         = 1000
RPM_TARGET_MAX    = 50
RPM_WARNING       = 800
IMAGE_DAILY_LIMIT = 500
IMAGE_WARNING     = 400
SCORING_DAILY_LIMIT = 1000  # 주제 점수화용 쿼터 (Phase 3 추가)

_request_times: list = []  # 인메모리 캐시 (프로세스 재시작 후 파일에서 복원)


def _init_quota_file() -> dict:
    data = {
        "date": now_iso()[:10],
        "total_requests": 0,
        "rpm_peak": 0.0,
        "rpm_timestamps": [],  # 최근 60초 타임스탬프 (프로세스 재시작 복원용)
        "images_generated": 0,
        "scoring_calls": 0,
        "cache_hits": 0,
        "cache_misses": 0,
        "cache_hit_rate": 0.0,
        "retry_count": 0,
        "sequential_mode_activations": 0,
        "cost_saved_by_cache_krw": 0.0,
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


def _current_rpm() -> float:
    """현재 RPM 계산 — 인메모리 캐시 우선, 비어있으면 파일에서 복원"""
    global _request_times
    cutoff = time.time() - 60
    _request_times = [t for t in _request_times if t > cutoff]
    # 프로세스 재시작으로 메모리가 비어있으면 파일에서 복원
    if not _request_times:
        persisted = get_quota().get("rpm_timestamps", [])
        _request_times = [t for t in persisted if t > cutoff]
    return len(_request_times)


def record_request() -> None:
    global _request_times
    now = time.time()
    _request_times.append(now)
    data = get_quota()
    data["total_requests"] += 1
    rpm = _current_rpm()
    if rpm > data["rpm_peak"]:
        data["rpm_peak"] = rpm
    # 최근 60초 타임스탬프만 파일에 유지 (재시작 시 복원용)
    cutoff = now - 60
    data["rpm_timestamps"] = [t for t in _request_times if t > cutoff]
    write_json(QUOTA_FILE, data)


def throttle_if_needed() -> None:
    rpm = _current_rpm()
    if rpm >= RPM_TARGET_MAX:
        time.sleep(60.0 / RPM_TARGET_MAX)
    if rpm >= RPM_WARNING:
        data = get_quota()
        data["sequential_mode_activations"] += 1
        write_json(QUOTA_FILE, data)
        logger.warning(f"[GEMINI] SEQUENTIAL_MODE: rpm={rpm}")


def record_image(count: int = 1) -> bool:
    data = get_quota()
    if data["images_generated"] + count > IMAGE_DAILY_LIMIT:
        logger.error(f"[GEMINI] IMAGE_LIMIT EXCEEDED ({data['images_generated']}/{IMAGE_DAILY_LIMIT})")
        return False
    data["images_generated"] += count
    write_json(QUOTA_FILE, data)
    return True


def record_scoring(count: int = 1) -> bool:
    """주제 점수화(scoring) API 호출 기록 (Phase 3 추가)"""
    data = get_quota()
    if data.get("scoring_calls", 0) + count > SCORING_DAILY_LIMIT:
        logger.warning(f"[GEMINI] SCORING_LIMIT EXCEEDED ({data.get('scoring_calls', 0)}/{SCORING_DAILY_LIMIT})")
        return False
    data["scoring_calls"] = data.get("scoring_calls", 0) + count
    write_json(QUOTA_FILE, data)
    return True


def record_cache_hit(cost_saved_krw: float = 0.0) -> None:
    data = get_quota()
    data["cache_hits"] += 1
    total = data["cache_hits"] + data["cache_misses"]
    data["cache_hit_rate"] = data["cache_hits"] / total if total > 0 else 0.0
    data["cost_saved_by_cache_krw"] += cost_saved_krw
    write_json(QUOTA_FILE, data)


def record_cache_miss() -> None:
    data = get_quota()
    data["cache_misses"] += 1
    total = data["cache_hits"] + data["cache_misses"]
    data["cache_hit_rate"] = data["cache_hits"] / total if total > 0 else 0.0
    write_json(QUOTA_FILE, data)


def record_retry() -> None:
    data = get_quota()
    data["retry_count"] += 1
    write_json(QUOTA_FILE, data)
