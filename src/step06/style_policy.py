from src.core.ssot import (read_json, write_json, json_exists,
                             sha256_dict, now_iso, get_run_dir)
from src.core.config import CHANNELS_DIR, MEMORY_DIR, CHANNEL_CATEGORIES, KAS_ROOT
from src.step00.channel_registry import get_channel

CHANNEL_ANIMATION_STYLE = {
    "CH1": "comparison", "CH2": "process", "CH3": "metaphor",
    "CH4": "comparison", "CH5": "process",
}
CHANNEL_HOOK_DIRECTION = {
    "CH1": "경제적 손실 공포 + 기회 제시",
    "CH2": "건강 위협 사실 + 해결책 예고",
    "CH3": "행동 패턴 충격 사실 + 변화 약속",
    "CH4": "부동산 손실 위험 + 기회 포착 방법",
    "CH5": "AI 충격 사실 + 활용 방법 약속",
}
RENDER_TOOL_MAP = {
    "metaphor": "gemini", "process": "manim",
    "comparison": "manim", "timeline": "manim", "hybrid": "hybrid",
}

def _get_preferred_mode(channel_id: str) -> str:
    bias_file = MEMORY_DIR / "topic_priority_bias.json"
    if not json_exists(bias_file): return "curiosity"
    bias = read_json(bias_file)
    weights = bias.get("title_mode_weights", {})
    return max(weights, key=weights.get) if weights else "curiosity"

def build_style_policy(channel_id: str, topic: dict, month_number: int) -> dict:
    ch          = get_channel(channel_id)
    anim_style  = CHANNEL_ANIMATION_STYLE.get(channel_id, "process")
    render_tool = RENDER_TOOL_MAP.get(anim_style, "manim")
    rpm_stage   = "INITIAL" if month_number <= 3 else "STABLE"
    rpm_tier    = ch.get("rpm_tier", "HIGH")
    aff         = ch.get("affiliate", {})
    click_rate  = aff.get("click_rate_growth" if rpm_stage == "STABLE" else "click_rate_initial", 0.003)
    purchase_rate = aff.get("purchase_conversion_rate", 0.0)

    from src.step07.revenue_policy import get_revenue_policy
    revenue_policy = get_revenue_policy(channel_id)
    policy_ref     = f"data/channels/{channel_id}/revenue_policy.json"

    pilot_file    = KAS_ROOT / "data" / "global" / "manim_pilot" / "manim_pilot_report.json"
    pilot_version = "v1.0"
    if json_exists(pilot_file):
        pilot_data    = read_json(pilot_file)
        pilot_version = pilot_data.get("prompt_version", "v1.0")

    from src.step03.algorithm_policy import get_algorithm_policy
    algo            = get_algorithm_policy(channel_id)
    upload_timing   = algo.get("upload_timing_rules", {})
    preferred_days  = upload_timing.get("preferred_days", ["화","목","토"])
    preferred_hours = upload_timing.get("preferred_hours_kst", [18])

    style_policy = {
        "channel_id": channel_id,
        "run_id": "",
        "policy_version": "v1.0",
        "created_at": now_iso(),
        "style_policy_fingerprint": "",
        "channel_style_id": f"kas_{channel_id.lower()}_v1",
        "positioning": "복잡한 개념을 애니메이션으로 쉽게 보여주는 채널",
        "tone": ch.get("category", ""),
        "hook_direction": CHANNEL_HOOK_DIRECTION.get(channel_id, ""),
        "thumbnail_style": "",
        "category_rpm_tier": rpm_tier,
        "animation_style": anim_style,
        "animation_complexity": "moderate",
        "render_tool": render_tool,
        "is_trending": topic.get("is_trending", False),
        "trend_topic_ref": topic.get("original_trend", {}).get("video_id"),
        "trend_reinterpretation": topic.get("reinterpreted_title") if topic.get("is_trending") else None,
        "preferred_title_mode": _get_preferred_mode(channel_id),
        "affiliate_product_ref": aff.get("product", ""),
        "affiliate_click_rate_applied": click_rate,
        "affiliate_purchase_rate_applied": purchase_rate,
        "upload_scheduled_datetime": "",
        "step07_policy_ref": policy_ref,
        "step03_policy_ref": f"data/channels/{channel_id}/algorithm_policy.json",
        "manim_pilot_version": pilot_version,
    }
    style_policy["style_policy_fingerprint"] = sha256_dict(style_policy)
    write_json(CHANNELS_DIR / channel_id / "style_policy_master.json", style_policy)
    return style_policy
