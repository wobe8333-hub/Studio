from loguru import logger

from src.core.config import (
    CHANNEL_CATEGORIES,
    CHANNELS_DIR,
    GLOBAL_DIR,
    KNOWLEDGE_DIR,
    MEMORY_DIR,
    RUNS_DIR,
)
from src.core.ssot import now_iso, write_json
from src.step00.channel_registry import create_registry

_ALL_CHANNELS = list(CHANNEL_CATEGORIES.keys())


def _ensure_channel_dirs() -> None:
    """7채널 디렉토리 구조 초기화"""
    for ch in _ALL_CHANNELS:
        for sub in ("monthly_plan", "risk"):
            (CHANNELS_DIR / ch / sub).mkdir(parents=True, exist_ok=True)
        (KNOWLEDGE_DIR / ch).mkdir(parents=True, exist_ok=True)
        (RUNS_DIR / ch).mkdir(parents=True, exist_ok=True)
    logger.info("[STEP00] 7채널 디렉토리 구조 초기화 완료")


def create_review_capacity_policy() -> None:
    path = GLOBAL_DIR / "review_capacity_policy.json"
    if path.exists():
        return
    data = {
        "schema_version": "2.0",
        "created_at": now_iso(),
        "total_channels": 7,
        "daily_capacity_per_person": 3,
        "monthly_capacity_estimate": 90,
        "review_required_monthly_max": 74,
        "capacity_sufficient": True,
        "trend_review_sla_hours": 24,
        "normal_review_sla_hours": 48,
        "production_upload_buffer_days": 3,
        "backlog_trigger_count": 7,
        "backlog_action": "trending_ratio 60% → 40% 임시 축소",
        "backlog_recovery_condition": "pending_review < 3",
        "72h_upload_feasibility": "생성(Day0) + review(24h) + 스케줄(24h) = 48h 이내 달성 가능",
    }
    write_json(path, data)


def create_api_quota_policy() -> None:
    path = GLOBAL_DIR / "api_quota_policy.json"
    if path.exists():
        return
    data = {
        "schema_version": 2,
        "created_at": now_iso(),
        "youtube_data_api": {
            "daily_quota_limit": 10000,
            "daily_quota_warning_threshold": 8000,
            "daily_quota_block_threshold": 9500,
            "quota_tracking_file": "data/global/quota/youtube_quota_daily.json",
            "upload_daily_limit": 7,
            "search_calls_per_channel_per_day": 2,
            "search_calls_max_per_day_total": 14,
            "quota_exceeded_action": "스케줄 익일로 이연 + decision_trace 기록",
            "multi_channel_distribution_rule": "채널별 순차 업로드 (동시 업로드 금지)",
            "peak_day_buffer": 1500,
            "analytics_api_separate": True,
            "analytics_quota_limit": 50000,
        },
        "gemini_api": {
            "tier": "paid",
            "rpm_limit": 1000,
            "rpm_target_max": 50,
            "rpm_safety_margin": 0.95,
            "requests_per_video": 15,
            "max_parallel_videos": 3,
            "sequential_mode_threshold_rpm": 800,
            "retry_policy": {
                "max_retries": 3,
                "backoff_strategy": "exponential",
                "initial_wait_sec": 2,
                "max_wait_sec": 60,
                "retry_on_status": [429, 503, 500],
            },
            "cache_policy": {
                "enabled": True,
                "cache_ttl_hours": 24,
                "cacheable_requests": ["system_prompt", "style_template", "affiliate_insert_template"],
                "cache_store": "data/global/cache/diskcache",
                "cache_type": "diskcache",
            },
            "image_generation": {
                "daily_limit": 500,
                "daily_warning_threshold": 400,
                "images_per_video_max": 15,
                "batch_size": 3,
                "batch_interval_sec": 2,
            },
        },
        "ytdlp": {
            "requests_per_minute_limit": 30,
            "sleep_interval_sec": 2,
            "sleep_interval_requests": 10,
            "user_agent_rotation": True,
            "user_agent_pool_size": 5,
            "retry_on_block": True,
            "retry_wait_min": 300,
            "concurrent_channels_limit": 2,
            "daily_trend_collection_limit_per_channel": 2,
        },
        "quota_alert_rules": {
            "youtube_80pct": "WARN + decision_trace 기록",
            "youtube_95pct": "BLOCK 업로드 + 익일 이연",
            "gemini_rpm_80pct": "순차 처리 전환",
            "gemini_image_daily_80pct": "이미지 생성 품질 하향 + WARN",
            "ytdlp_block_detected": "30분 대기 후 재시도",
        },
    }
    write_json(path, data)


def create_memory_store() -> None:
    path = MEMORY_DIR / "topic_priority_bias.json"
    if path.exists():
        return

    MEMORY_DIR.mkdir(parents=True, exist_ok=True)

    write_json(path, {
        "updated_at": now_iso(),
        "title_mode_weights": {"authority": 0.35, "curiosity": 0.45, "benefit": 0.20},
        "channel_performance_index": {
            ch: {"avg_ctr_level": "TARGET", "avg_avp": 0.0, "avg_views": 0}
            for ch in _ALL_CHANNELS
        },
        "trend_response_patterns": [],
        "topic_blacklist_by_channel": {ch: [] for ch in _ALL_CHANNELS},
        "winning_animation_patterns": [],
    })

    write_json(MEMORY_DIR / "winning_animation_patterns.json", {
        "updated_at": now_iso(),
        "high_avp_patterns": [],
        "low_avp_patterns": [],
    })

    write_json(MEMORY_DIR / "content_sustainability_index.json", {
        "updated_at": now_iso(),
        "by_channel": {
            ch: {
                "topics_produced": 0,
                "topics_available_estimate": 200,
                "depletion_risk": "LOW",
                "refresh_eligible_topics": [],
            }
            for ch in _ALL_CHANNELS
        },
        "total_topics_produced": 0,
        "sustainability_horizon_months": 24,
    })


def run_global_init() -> None:
    logger.info("[STEP 00] 전역 초기화 시작... (7채널)")
    GLOBAL_DIR.mkdir(parents=True, exist_ok=True)
    _ensure_channel_dirs()
    create_registry()
    create_review_capacity_policy()
    create_api_quota_policy()
    create_memory_store()
    logger.info("[STEP 00] 전역 초기화 완료")

if __name__ == "__main__":
    run_global_init()
