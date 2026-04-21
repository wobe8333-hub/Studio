"""STEP 16 — 월간 리스크 통제."""
from datetime import datetime

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


def _channel_risk(channel_id: str, month_str: str) -> dict:
    rev = CHANNELS_DIR / channel_id / "revenue_monthly.json"
    net = 0.0
    if json_exists(rev):
        net = read_json(rev).get("monthly_records", {}).get(month_str, {}).get("net_profit", 0.0)

    risks = []
    if net < REVENUE_TARGET_PER_CHANNEL:
        risks.append(f"순이익 미달: {net:,.0f}원 < {REVENUE_TARGET_PER_CHANNEL:,}원")

    return {
        "channel_id": channel_id,
        "month": month_str,
        "net_profit": net,
        "target": REVENUE_TARGET_PER_CHANNEL,
        "target_achieved": net >= REVENUE_TARGET_PER_CHANNEL,
        "risks": risks,
        "risk_level": "HIGH" if risks else "LOW",
    }


def run_step16(month_str: str = None) -> dict:
    if not month_str:
        month_str = datetime.utcnow().strftime("%Y-%m")

    ch_risks = {}
    total_net = 0.0

    for ch in _ALL_CHANNELS:
        r = _channel_risk(ch, month_str)
        ch_risks[ch] = r
        total_net += r["net_profit"]
        risk_dir = CHANNELS_DIR / ch / "risk"
        risk_dir.mkdir(parents=True, exist_ok=True)
        write_json(risk_dir / f"risk_dashboard_{month_str}.json", r)

    aggregate = {
        "schema_version": "2.0",
        "month": month_str,
        "total_net_profit_month": total_net,
        "target_total": REVENUE_TARGET_TOTAL,
        "target_total_achieved": total_net >= REVENUE_TARGET_TOTAL,
        "achievement_rate": round(total_net / REVENUE_TARGET_TOTAL * 100, 1),
        "channels": ch_risks,
        "generated_at": now_iso(),
    }
    risk_dir = GLOBAL_DIR / "risk"
    risk_dir.mkdir(parents=True, exist_ok=True)
    write_json(risk_dir / f"risk_aggregate_{month_str}.json", aggregate)
    logger.info(f"[STEP16] {month_str} total={total_net:,.0f}원 (목표={REVENUE_TARGET_TOTAL:,}원)")
    return aggregate
