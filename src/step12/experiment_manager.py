"""STEP 12 — A/B 실험 관리."""
import logging
from src.core.ssot import read_json, write_json, json_exists, now_iso, get_run_dir

logger = logging.getLogger(__name__)

def record_experiment(channel_id: str, run_id: str, variant_ref: str, kpi: dict) -> dict:
    s12 = get_run_dir(channel_id, run_id)/"step12"; s12.mkdir(parents=True, exist_ok=True)
    exp = {"channel_id":channel_id,"run_id":run_id,"variant_ref":variant_ref,
            "recorded_at":now_iso(),"ctr":kpi.get("ctr"),"views":kpi.get("views"),
            "avg_view_percentage":kpi.get("avg_view_percentage"),"winner":False}
    write_json(s12/f"experiment_{variant_ref}.json", exp)
    return exp

def select_winner(channel_id: str, run_id: str) -> str:
    s12 = get_run_dir(channel_id, run_id)/"step12"
    best_ref, best_ctr = "v1", 0.0
    for ref in ["v1","v2","v3"]:
        fp = s12/f"experiment_{ref}.json"
        if not json_exists(fp): continue
        ctr = read_json(fp).get("ctr") or 0.0
        if ctr > best_ctr: best_ctr=ctr; best_ref=ref
    logger.info(f"[STEP12] {channel_id}/{run_id} 승자: {best_ref} CTR={best_ctr}")
    return best_ref
