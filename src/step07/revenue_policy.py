from src.core.config import (
    CHANNEL_RPM_INITIAL,
    CHANNEL_RPM_PROXY,
    CHANNELS_DIR,
    REVENUE_TARGET_PER_CHANNEL,
)
from src.core.ssot import json_exists, now_iso, read_json, write_json

CHANNEL_RPM_FLOOR = {
    "CH1": 5000, "CH2": 4000, "CH3": 2800,
    "CH4": 2500, "CH5": 2500, "CH6": 2800, "CH7": 2800,
}

def get_revenue_policy(channel_id: str) -> dict:
    policy_path = CHANNELS_DIR / channel_id / "revenue_policy.json"
    if json_exists(policy_path):
        return read_json(policy_path)
    policy = {
        "channel_id": channel_id,
        "policy_version": "v1.0",
        "effective_from": now_iso()[:7],
        "revenue_target_net": REVENUE_TARGET_PER_CHANNEL,
        "target_duration_range_sec": [660, 780],
        "midroll_count_target": 3,
        "midroll_positions_ratio": [0.35, 0.65, 0.85],
        "midroll_buffer_before_sec": 30,
        "rpm_proxy": CHANNEL_RPM_PROXY[channel_id],
        "rpm_initial": CHANNEL_RPM_INITIAL[channel_id],
        "rpm_floor": CHANNEL_RPM_FLOOR[channel_id],
        "fallback_policy": {
            "rpm_drop": "트렌드 콘텐츠 비중 +10%p",
            "safety_risk": "해당 topic DEPRECATED",
        },
    }
    write_json(policy_path, policy)
    return policy
