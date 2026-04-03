"""채널 레지스트리 — 활성 채널 목록 (런치 페이즈 기준)."""
from loguru import logger
from src.core.config import (
    CHANNEL_CATEGORIES,
    CHANNEL_CATEGORY_KO,
    CHANNEL_IDS,
    CHANNEL_LAUNCH_PHASE,
    CHANNEL_RPM_PROXY,
    CHANNEL_MONTHLY_TARGET,
    CHANNEL_SHORTS_TARGET,
    REVENUE_TARGET_PER_CHANNEL,
    GLOBAL_DIR,
)
from src.core.ssot import write_json, now_iso

# 7채널 순서 (론칭 우선순위 순)
_ORDER = ("CH1", "CH2", "CH3", "CH4", "CH5", "CH6", "CH7")

_CHANNEL_AFFILIATE = {
    "CH1": {
        "product": "증권사 계좌 개설 CPA",
        "click_rate_initial": 0.003,
        "click_rate_growth": 0.008,
        "purchase_conversion_rate": 0.20,
    },
    "CH2": {
        "product": "부동산 강의 / 청약 앱 CPA",
        "click_rate_initial": 0.004,
        "click_rate_growth": 0.009,
        "purchase_conversion_rate": 0.15,
    },
    "CH3": {
        "product": "심리학 도서 CPS",
        "click_rate_initial": 0.003,
        "click_rate_growth": 0.008,
        "purchase_conversion_rate": 0.10,
    },
    "CH4": {
        "product": "미스터리 도서 / 공포 OTT CPA",
        "click_rate_initial": 0.005,
        "click_rate_growth": 0.012,
        "purchase_conversion_rate": 0.10,
    },
    "CH5": {
        "product": "밀리터리 도서 / 전쟁사 게임 CPS",
        "click_rate_initial": 0.004,
        "click_rate_growth": 0.010,
        "purchase_conversion_rate": 0.12,
    },
    "CH6": {
        "product": "과학 키트 / 온라인 강의 CPA",
        "click_rate_initial": 0.004,
        "click_rate_growth": 0.010,
        "purchase_conversion_rate": 0.15,
    },
    "CH7": {
        "product": "역사 도서 / 역사 여행 CPS",
        "click_rate_initial": 0.004,
        "click_rate_growth": 0.010,
        "purchase_conversion_rate": 0.15,
    },
}


def create_registry() -> None:
    """data/global/channel_registry.json 생성 (STEP00 global_init)."""
    GLOBAL_DIR.mkdir(parents=True, exist_ok=True)
    channels = [
        {
            "channel_id": ch,
            "category": CHANNEL_CATEGORIES.get(ch, ""),
            "category_ko": CHANNEL_CATEGORY_KO.get(ch, ""),
            "launch_phase": CHANNEL_LAUNCH_PHASE[ch],
            "youtube_channel_id": CHANNEL_IDS.get(ch, "") or "",
            "status": "PLANNED",
            "rpm_proxy": CHANNEL_RPM_PROXY.get(ch, 0),
            "revenue_target_monthly": REVENUE_TARGET_PER_CHANNEL,
            "monthly_longform_target": CHANNEL_MONTHLY_TARGET.get(ch, 10),
            "monthly_shorts_target": CHANNEL_SHORTS_TARGET.get(ch, 30),
        }
        for ch in _ORDER
    ]
    write_json(
        GLOBAL_DIR / "channel_registry.json",
        {
            "schema_version": "2.0",
            "created_at": now_iso(),
            "total_channels": 7,
            "channels": channels,
            "total_revenue_target_monthly": REVENUE_TARGET_PER_CHANNEL * 7,
        },
    )
    logger.info("[STEP00] channel_registry.json 생성 완료 (7채널)")


def get_channel(channel_id: str) -> dict:
    """스타일·수익 정책용 채널 메타(카테고리, 티어, 제휴 파라미터)."""
    rpm = CHANNEL_RPM_PROXY.get(channel_id, 0)
    rpm_tier = "HIGH" if rpm >= 5000 else "MID" if rpm >= 3500 else "LOW"
    return {
        "category": CHANNEL_CATEGORIES.get(channel_id, ""),
        "category_ko": CHANNEL_CATEGORY_KO.get(channel_id, ""),
        "rpm_tier": rpm_tier,
        "affiliate": dict(_CHANNEL_AFFILIATE.get(channel_id, {})),
    }


def get_active_channels(month_number: int) -> list:
    """month_number에 해당 런치 단계까지 활성화된 채널 ID 목록."""
    active = [
        ch for ch in _ORDER
        if CHANNEL_LAUNCH_PHASE[ch] <= month_number
    ]
    logger.debug(f"[STEP00] 활성 채널 (월차={month_number}): {active}")
    return active
