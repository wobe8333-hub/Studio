"""STEP 11 — QA 게이트."""
import logging
from src.core.ssot import read_json, write_json, json_exists, now_iso, get_run_dir

logger = logging.getLogger(__name__)
REVIEW_REQUIRED    = {"CH1","CH2","CH4"}
REVIEW_CONDITIONAL = {"CH3"}

def run_step11(channel_id: str, run_id: str,
               human_review_completed: bool = False,
               reviewer: str = None) -> dict:
    run_dir = get_run_dir(channel_id, run_id)
    s08=run_dir/"step08"; s11=run_dir/"step11"; s11.mkdir(parents=True, exist_ok=True)
    script  = read_json(s08/"script.json") if json_exists(s08/"script.json") else {}
    video   = s08/"video.mp4"
    anim_pass = (video.exists() and video.stat().st_size > 0
                 and script.get("hook",{}).get("animation_preview_at_sec",99) <= 10)
    has_disc  = True
    if channel_id == "CH2":    has_disc = bool(script.get("medical_disclaimer"))
    elif channel_id in ["CH1","CH4"]: has_disc = bool(script.get("financial_disclaimer"))
    ai_label    = bool(script.get("ai_label"))
    policy_pass = ai_label and has_disc
    aff         = script.get("affiliate_insert",{})
    formula_ok  = aff.get("purchase_rate_applied",0) > 0
    hr_required = channel_id in REVIEW_REQUIRED
    hr_completed= human_review_completed if hr_required else True
    overall     = anim_pass and policy_pass and formula_ok and hr_completed
    qa = {
        "channel_id":channel_id,"run_id":run_id,"qa_timestamp":now_iso(),
        "animation_quality_check":{"pass":anim_pass},
        "script_accuracy_check":{"pass":has_disc},
        "youtube_policy_check":{
            "ai_label_placed":ai_label,
            "medical_disclaimer_placed":bool(script.get("medical_disclaimer")) if channel_id=="CH2" else None,
            "financial_disclaimer_placed":bool(script.get("financial_disclaimer")) if channel_id in ["CH1","CH4"] else None,
            "pass":policy_pass,
        },
        "human_review":{"required":hr_required,"completed":hr_completed,
                         "reviewer":reviewer,"sla_hours":24 if hr_required else 0},
        "affiliate_formula_check":{"purchase_rate_applied":aff.get("purchase_rate_applied",0),
                                    "formula_correct":formula_ok},
        "overall_pass":overall,
    }
    write_json(s11/"qa_result.json", qa)
    if overall: logger.info(f"[STEP11] {channel_id}/{run_id} QA PASS")
    else:
        reasons = [k for k,v in [("animation",not anim_pass),("policy",not policy_pass),
                                   ("formula",not formula_ok),("human_review",not hr_completed)] if v]
        logger.warning(f"[STEP11] QA FAIL {channel_id}/{run_id}: {reasons}")
    return qa
