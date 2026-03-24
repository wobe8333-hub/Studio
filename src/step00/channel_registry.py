"""채널 레지스트리 — 활성 채널 목록 (런치 페이즈 기준)."""
from src.core.config import (
    CHANNEL_CATEGORIES,
    CHANNEL_IDS,
    CHANNEL_LAUNCH_PHASE,
    CHANNEL_RPM_PROXY,
    GLOBAL_DIR,
)
from src.core.ssot import write_json, now_iso

_ORDER = ("CH1", "CH2", "CH3", "CH4", "CH5")

_CHANNEL_AFFILIATE = {
    "CH1": {
        "product": "증권사 계좌 개설 CPA",
        "click_rate_initial": 0.003,
        "click_rate_growth": 0.008,
        "purchase_conversion_rate": 0.20,
    },
    "CH2": {
        "product": "건강기능식품 CPS",
        "click_rate_initial": 0.003,
        "click_rate_growth": 0.008,
        "purchase_conversion_rate": 0.07,
    },
    "CH3": {
        "product": "심리학 도서 CPS",
        "click_rate_initial": 0.003,
        "click_rate_growth": 0.008,
        "purchase_conversion_rate": 0.10,
    },
    "CH4": {
        "product": "부동산 강의 CPS",
        "click_rate_initial": 0.003,
        "click_rate_growth": 0.008,
        "purchase_conversion_rate": 0.08,
    },
    "CH5": {
        "product": "AI 강의 CPS",
        "click_rate_initial": 0.003,
        "click_rate_growth": 0.008,
        "purchase_conversion_rate": 0.08,
    },
}


def create_registry() -> None:
    """data/global/channel_registry.json 생성 (STEP00 global_init)."""
    GLOBAL_DIR.mkdir(parents=True, exist_ok=True)
    channels = [
        {
            "channel_id": ch,
            "category": CHANNEL_CATEGORIES.get(ch, ""),
            "launch_phase": CHANNEL_LAUNCH_PHASE[ch],
            "youtube_channel_id": CHANNEL_IDS.get(ch, "") or "",
        }
        for ch in _ORDER
    ]
    write_json(
        GLOBAL_DIR / "channel_registry.json",
        {
            "schema_version": "1.0",
            "created_at": now_iso(),
            "total_channels": 5,
            "channels": channels,
        },
    )


def get_channel(channel_id: str) -> dict:
    """스타일·수익 정책용 채널 메타(카테고리, 티어, 제휴 파라미터)."""
    rpm = CHANNEL_RPM_PROXY.get(channel_id, 0)
    rpm_tier = "HIGH" if rpm >= 5000 else "MID"
    return {
        "category": CHANNEL_CATEGORIES.get(channel_id, ""),
        "rpm_tier": rpm_tier,
        "affiliate": dict(_CHANNEL_AFFILIATE.get(channel_id, {})),
    }


def get_active_channels(month_number: int) -> list:
    """month_number에 해당 런치 단계까지 활성화된 채널 ID 목록."""
    return [
        ch for ch in _ORDER
        if CHANNEL_LAUNCH_PHASE[ch] <= month_number
    ]
