"""STEP 13 — 변형 학습·정책 환류."""
import json, logging
from src.core.ssot import read_json, write_json, json_exists, now_iso, get_run_dir
from src.core.config import MEMORY_DIR

logger = logging.getLogger(__name__)

def run_step13(channel_id: str, run_id: str) -> dict:
    run_dir = get_run_dir(channel_id, run_id)
    s11=run_dir/"step11"; s12=run_dir/"step12"; s08=run_dir/"step08"
    qa     = read_json(s11/"qa_result.json")                      if json_exists(s11/"qa_result.json")                      else {}
    kpi    = read_json(s12/"kpi_48h.json")                        if json_exists(s12/"kpi_48h.json")                        else {}
    alg    = read_json(s12/"algorithm_stage_assessment.json")     if json_exists(s12/"algorithm_stage_assessment.json")     else {}
    script = read_json(s08/"script.json")                         if json_exists(s08/"script.json")                         else {}

    ctr   = kpi.get("ctr"); avp=kpi.get("avg_view_percentage"); views=kpi.get("views",0)
    stage = alg.get("algorithm_stage","PRE-ENTRY")

    MEMORY_DIR.mkdir(parents=True, exist_ok=True)
    with open(MEMORY_DIR/"run_history.jsonl","a",encoding="utf-8") as f:
        f.write(json.dumps({
            "run_id":run_id,"channel_id":channel_id,"recorded_at":now_iso(),
            "topic":script.get("hook",{}).get("text","")[:50],
            "is_trending":script.get("is_trending",False),
            "animation_style":script.get("animation_style",""),
            "qa_pass":qa.get("overall_pass",False),
            "ctr":ctr,"avp":avp,"views":views,"algorithm_stage":stage,
        }, ensure_ascii=True) + "\n")

    bias_path = MEMORY_DIR/"topic_priority_bias.json"
    bias = read_json(bias_path) if json_exists(bias_path) else {
        "title_mode_weights":{"authority":0.35,"curiosity":0.45,"benefit":0.20},
        "channel_performance_index":{},"topic_blacklist_by_channel":{},
        "trend_response_patterns":[],"winning_animation_patterns":[],
    }
    if ctr and ctr >= 6.0 and avp and avp >= 50.0:
        bias.setdefault("winning_animation_patterns",[]).append({
            "run_id":run_id,"channel_id":channel_id,
            "animation_style":script.get("animation_style",""),
            "is_trending":script.get("is_trending",False),
            "ctr":ctr,"avp":avp,"recorded_at":now_iso(),
        })
        bias["winning_animation_patterns"] = bias["winning_animation_patterns"][-50:]
    bias.setdefault("channel_performance_index",{})[channel_id] = {
        "avg_ctr_level":"HIGH" if (ctr and ctr>=5.5) else "TARGET",
        "avg_avp":avp or 0.0,"avg_views":views,"algorithm_stage":stage,"updated_at":now_iso(),
    }
    write_json(bias_path, bias)

    s13 = run_dir/"step13"; s13.mkdir(parents=True, exist_ok=True)
    write_json(s13/"variant_performance.json", {
        "run_id":run_id,"channel_id":channel_id,"recorded_at":now_iso(),
        "ctr":ctr,"ctr_level":kpi.get("ctr_level","UNKNOWN"),
        "avp":avp,"views":views,"algorithm_stage":stage,"winner_title_ref":"v1",
    })
    write_json(s13/"decision_trace.json", {"events":[]})
    purchase_actual = script.get("affiliate_insert",{}).get("purchase_rate_applied",0.0) or 0.0
    write_json(s13/"next_policy_update.json", {
        "channel_id":channel_id,"run_id":run_id,"recorded_at":now_iso(),
        "preferred_title_mode":"curiosity",
        "preferred_animation_style":script.get("animation_style",""),
        "preferred_render_tool":script.get("render_tool","manim"),
        "is_trending_effective":script.get("is_trending",False),
        "affiliate_click_rate_actual":0.0,
        "affiliate_purchase_rate_actual":purchase_actual,
        "revenue_on_track_for_1_5m":(views or 0) > 50000,
        "algorithm_stage_feedback":stage,"rpm_tier_feedback":"CONFIRMED",
        "memory_store_update":{
            "topic_blacklist_add":[],
            "channel_ctr_update":{"channel_id":channel_id,"ctr_level":kpi.get("ctr_level","UNKNOWN")},
            "winning_animation_pattern":{"style":script.get("animation_style"),"render_tool":script.get("render_tool"),"avp":avp},
            "trend_pattern_update":{"was_trending":script.get("is_trending",False),"trend_boost_ratio":0.0},
        },
    })
    logger.info(f"[STEP13] {channel_id}/{run_id} 완료 stage={stage}")
    return read_json(s13/"variant_performance.json")
