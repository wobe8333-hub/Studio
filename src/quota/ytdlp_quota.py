# 기존 복사 파일(backend\knowledge_v1\keyword_sources\ytdlp_channels.py)의
# yt-dlp 수집 로직을 유지하면서 아래 상수와 함수를 파일 상단에 추가한다.
# 이미 존재하면 해당 상수·함수만 추가/덮어쓰고 나머지 로직은 유지한다.
import random
import time

from loguru import logger

_request_count    = 0
_last_request_time= 0.0

RPM_LIMIT         = 30
SLEEP_INTERVAL_SEC= 2
SLEEP_EVERY_N     = 10
RETRY_WAIT_SEC    = 300

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/118.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Edge/120.0.0.0 Safari/537.36",
]

def get_random_user_agent() -> str:
    return random.choice(USER_AGENTS)

def throttle() -> None:
    global _request_count, _last_request_time
    _request_count += 1
    elapsed = time.time() - _last_request_time
    min_interval = 60.0 / RPM_LIMIT
    if elapsed < min_interval:
        time.sleep(min_interval - elapsed)
    if _request_count % SLEEP_EVERY_N == 0:
        time.sleep(SLEEP_INTERVAL_SEC)
    _last_request_time = time.time()

def on_block_detected() -> None:
    logger.warning(f"[STEP00] YTDLP_BLOCK: {RETRY_WAIT_SEC}초 대기 후 재시도")
    time.sleep(RETRY_WAIT_SEC)

def get_ytdlp_opts(channel_id: str = "") -> dict:
    return {
        "quiet": True, "no_warnings": True, "extract_flat": True,
        "user_agent": get_random_user_agent(),
        "sleep_interval": SLEEP_INTERVAL_SEC,
        "max_sleep_interval": SLEEP_INTERVAL_SEC * 2,
        "ignoreerrors": True,
    }

