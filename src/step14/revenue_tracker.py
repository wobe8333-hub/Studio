"""STEP 14 — 수익 다각화 트래킹."""
from loguru import logger

from src.core.config import (
    CHANNEL_CATEGORIES,
    CHANNELS_DIR,
    GLOBAL_DIR,
    REVENUE_TARGET_PER_CHANNEL,
    REVENUE_TARGET_TOTAL,
)
from src.core.ssot import json_exists, now_iso, read_json, write_json

_ALL_CHANNELS = list(CHANNEL_CATEGORIES.keys())


def update_revenue_monthly(
    channel_id: str,
    month_str: str,
    adsense_krw: float,
    affiliate_krw: float,
    operating_cost: float,
) -> dict:
    ch_dir = CHANNELS_DIR / channel_id
    ch_dir.mkdir(parents=True, exist_ok=True)
    path = ch_dir / "revenue_monthly.json"
    data = read_json(path) if json_exists(path) else {
        "schema_version": "2.0",
        "channel_id": channel_id,
        "monthly_records": {},
    }
    net = adsense_krw + affiliate_krw - operating_cost
    total_rev = adsense_krw + affiliate_krw
    target_achieved = net >= REVENUE_TARGET_PER_CHANNEL

    data["monthly_records"][month_str] = {
        "month": month_str,
        "adsense_krw": adsense_krw,
        "affiliate_krw": affiliate_krw,
        "operating_cost": operating_cost,
        "total_revenue": total_rev,
        "net_profit": net,
        "mix_ratio": {
            "adsense": round(adsense_krw / (total_rev + 0.001), 2),
            "affiliate": round(affiliate_krw / (total_rev + 0.001), 2),
        },
        "target_achieved": target_achieved,
        "target_2m_achieved": target_achieved,
        "updated_at": now_iso(),
    }
    data["net_profit"] = net
    data["updated_at"] = now_iso()
    write_json(path, data)
    logger.info(f"[STEP14] {channel_id} {month_str} net={net:,.0f}원 (목표={REVENUE_TARGET_PER_CHANNEL:,}원)")
    return data


def get_total_revenue(month_str: str) -> dict:
    total_net = 0.0
    by_ch = {}
    channels_hit = 0

    for ch in _ALL_CHANNELS:
        path = CHANNELS_DIR / ch / "revenue_monthly.json"
        if not json_exists(path):
            by_ch[ch] = {"net_profit": 0, "target_achieved": False, "rpm_stage": "INITIAL"}
            continue
        rec = read_json(path).get("monthly_records", {}).get(month_str, {})
        net = rec.get("net_profit", 0.0)
        hit = rec.get("target_achieved", False)
        by_ch[ch] = {"net_profit": net, "target_achieved": hit, "rpm_stage": "INITIAL"}
        total_net += net
        if hit:
            channels_hit += 1

    result = {
        "month_id": month_str,
        "revenue_target_per_channel": REVENUE_TARGET_PER_CHANNEL,
        "revenue_target_total": REVENUE_TARGET_TOTAL,
        "by_channel": by_ch,
        "channels_achieved_target": channels_hit,
        "total_net_profit": total_net,
        "gap_to_total_target": max(0, REVENUE_TARGET_TOTAL - total_net),
        "achievement_rate": round(total_net / REVENUE_TARGET_TOTAL * 100, 1),
    }
    rev_dir = GLOBAL_DIR / "revenue"
    rev_dir.mkdir(parents=True, exist_ok=True)
    write_json(rev_dir / f"revenue_aggregate_{month_str}.json", result)
    return result
