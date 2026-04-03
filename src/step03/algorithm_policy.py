from pathlib import Path
from src.core.ssot import read_json, write_json, json_exists, now_iso
from src.core.config import CHANNELS_DIR, CHANNEL_HOOK_DIRECTION

CHANNEL_AUDIENCE = {
    "CH1": {"primary_age_range": "30~50대", "primary_gender": "남성",
            "peak_viewing_hours_kst": [19, 20, 21]},
    "CH2": {"primary_age_range": "30~50대", "primary_gender": "전반",
            "peak_viewing_hours_kst": [20, 21, 22]},
    "CH3": {"primary_age_range": "20~40대", "primary_gender": "전반",
            "peak_viewing_hours_kst": [14, 15, 16, 17]},
    "CH4": {"primary_age_range": "20~40대", "primary_gender": "전반",
            "peak_viewing_hours_kst": [21, 22, 23]},
    "CH5": {"primary_age_range": "25~45대", "primary_gender": "남성",
            "peak_viewing_hours_kst": [14, 15, 16]},
    "CH6": {"primary_age_range": "20~40대", "primary_gender": "전반",
            "peak_viewing_hours_kst": [15, 16, 17]},
    "CH7": {"primary_age_range": "20~50대", "primary_gender": "전반",
            "peak_viewing_hours_kst": [20, 21, 22]},
}
CHANNEL_UPLOAD_DAYS = {
    "CH1": ["화", "목", "토"],
    "CH2": ["월", "수", "금"],
    "CH3": ["토", "일"],
    "CH4": ["금", "토"],
    "CH5": ["토", "일"],
    "CH6": ["화", "목", "토"],
    "CH7": ["수", "토"],
}
def get_algorithm_policy(channel_id: str) -> dict:
    policy_path = CHANNELS_DIR / channel_id / "algorithm_policy.json"
    if json_exists(policy_path):
        return read_json(policy_path)
    policy = {
        "channel_id": channel_id,
        "policy_version": "v1.0",
        "created_at": now_iso(),
        "audience_profile": CHANNEL_AUDIENCE[channel_id],
        "browse_entry_conditions": {
            "ctr_threshold": 5.5, "avp_threshold": 45.0,
            "avd_threshold_sec": 280, "impression_volume_min": 8000,
        },
        "search_seo_rules": {
            "title_keyword_position": "앞 15자 이내",
            "title_length_range": [20, 40],
            "description_first_2lines_keyword": True,
            "chapter_markers_required": True,
            "chapter_min_count": 5,
            "tags_count_target": 15,
        },
        "upload_timing_rules": {
            "preferred_days": CHANNEL_UPLOAD_DAYS[channel_id],
            "preferred_hours_kst": CHANNEL_AUDIENCE[channel_id]["peak_viewing_hours_kst"],
        },
        "hook_rules": {
            "hook_duration_max_sec": 25,
            "hook_direction": CHANNEL_HOOK_DIRECTION[channel_id],
            "animation_preview_required": True,
            "animation_preview_position_sec": 10,
            "avd_target_at_30sec_pct": 82,
        },
        "trend_response_rules": {
            "trend_detection_to_upload_hours": 72,
            "trend_validity_days": 7,
            "trending_ratio_target": 0.60,
            "backlog_override_trending_ratio": 0.40,
        },
        "retention_rules": {
            "open_loop_positions": [0.25, 0.50, 0.75],
            "midroll_buffer_sec": 30,
            "chapter_visual_cue": True,
        },
        "community_signal_rules": {
            "pinned_comment_required": True,
            "like_cta_position_sec": 55,
            "comment_prompt_type": "질문형",
        },
    }
    write_json(policy_path, policy)
    return policy
