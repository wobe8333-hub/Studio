"""STEP 01 — 채널 준비도 측정."""
import logging, sys
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from src.core.config import (
    KAS_ROOT, CHANNELS_DIR, CHANNEL_IDS, CHANNEL_RPM_PROXY,
    CHANNEL_RPM_INITIAL, CHANNEL_MONTHLY_TARGET,
    CHANNEL_LAUNCH_PHASE, REVENUE_TARGET_PER_CHANNEL,
)
from src.core.ssot import write_json, now_iso
from src.quota.youtube_quota import consume

logger = logging.getLogger(__name__)
SCOPES = ["https://www.googleapis.com/auth/youtube.readonly"]

AFFILIATE_PARAMS = {
    "CH1": {"product": "증권사 계좌 개설 CPA", "purchase_rate": 0.20},
    "CH2": {"product": "건강기능식품 CPS",      "purchase_rate": 0.07},
    "CH3": {"product": "심리학 도서 CPS",       "purchase_rate": 0.10},
    "CH4": {"product": "부동산 강의 CPS",       "purchase_rate": 0.08},
    "CH5": {"product": "AI 강의 CPS",           "purchase_rate": 0.08},
}
OPERATING_COST = {
    "CH1": 80000, "CH2": 100000, "CH3": 100000, "CH4": 100000, "CH5": 100000,
}

def _get_youtube_service(channel_id: str):
    token_path = KAS_ROOT / "credentials" / f"{channel_id}_token.json"
    if not token_path.exists():
        raise FileNotFoundError(f"token.json 없음: {token_path}")
    return build("youtube", "v3",
                 credentials=Credentials.from_authorized_user_file(str(token_path), SCOPES))

def _fetch_channel_stats(channel_id: str) -> dict:
    default = {"subscriber_count": 0, "video_count": 0, "view_count": 0}
    yt_id   = CHANNEL_IDS.get(channel_id, "")
    if not yt_id:
        logger.warning(f"[STEP01] {channel_id} CHANNEL_ID 미설정")
        return default
    if not consume(1, "channels_list"):
        logger.error(f"[STEP01] 쿼터 초과")
        return default
    try:
        resp  = _get_youtube_service(channel_id).channels().list(
            part="statistics", id=yt_id).execute()
        if not resp.get("items"):
            return default
        stats = resp["items"][0].get("statistics", {})
        return {
            "subscriber_count": int(stats.get("subscriberCount", 0)),
            "video_count":      int(stats.get("videoCount", 0)),
            "view_count":       int(stats.get("viewCount", 0)),
        }
    except Exception as e:
        logger.error(f"[STEP01] {channel_id} API 오류: {e}")
        return default

def _trust_level(subs: int) -> str:
    if subs >= 10000: return "ACTIVE"
    if subs >= 1000:  return "WARMING"
    return "COLD"

def _monetization(subs: int, vids: int) -> str:
    return "PENDING" if subs >= 1000 and vids >= 10 else "NOT_ELIGIBLE"

def create_channel_baseline(channel_id: str) -> dict:
    ch_dir = CHANNELS_DIR / channel_id
    ch_dir.mkdir(parents=True, exist_ok=True)
    stats  = _fetch_channel_stats(channel_id)
    trust  = _trust_level(stats["subscriber_count"])
    moneti = _monetization(stats["subscriber_count"], stats["video_count"])
    baseline = {
        "schema_version": "1.0", "channel_id": channel_id,
        "channel_registry_id": CHANNEL_IDS.get(channel_id, ""),
        "assessment_date": now_iso()[:10],
        "subscriber_count": stats["subscriber_count"],
        "video_count": stats["video_count"],
        "view_count": stats["view_count"],
        "uploads_last_90d": 0, "avg_views_per_video_90d": 0,
        "avg_ctr_90d": None, "avg_avp_90d": None, "rpm_actual_90d": None,
        "monetization_status": moneti,
        "algorithm_trust_level": trust,
        "current_animation_quality": "NONE",
        "rpm_proxy": CHANNEL_RPM_PROXY[channel_id],
        "rpm_initial": CHANNEL_RPM_INITIAL[channel_id],
        "launch_phase": CHANNEL_LAUNCH_PHASE[channel_id],
        "note": "신규 채널 COLD 시작." if trust == "COLD" else "",
    }
    write_json(ch_dir / "channel_baseline.json", baseline)
    return baseline

def create_cashflow_plan(channel_id: str, baseline: dict) -> dict:
    ch_dir = CHANNELS_DIR / channel_id
    aff    = AFFILIATE_PARAMS[channel_id]
    op     = OPERATING_COST[channel_id]
    mv     = CHANNEL_MONTHLY_TARGET[channel_id]
    rpm_p  = CHANNEL_RPM_PROXY[channel_id]
    rpm_i  = CHANNEL_RPM_INITIAL[channel_id]
    trust  = baseline["algorithm_trust_level"]
    target = int((REVENUE_TARGET_PER_CHANNEL + op) / (rpm_p / 1000))
    plan = {
        "schema_version": "1.0", "channel_id": channel_id,
        "assessment_date": now_iso()[:10],
        "revenue_target_net": REVENUE_TARGET_PER_CHANNEL,
        "monthly_video_target": mv, "operating_cost_monthly": op,
        "affiliate_formula": {
            "description": "views x click_rate x purchase_rate x price x commission",
            "click_rate_initial": 0.003, "click_rate_growth": 0.008,
            "click_rate_stable": 0.015,
            "purchase_rate": aff["purchase_rate"], "product": aff["product"],
        },
        "rpm_stage_rules": {
            "initial_months": 3, "initial_multiplier": 0.5,
            "rpm_initial": rpm_i, "rpm_proxy": rpm_p,
            "stable_source": "rpm_actual_or_proxy",
        },
        "target_views_stable_monthly": target,
        "avg_views_per_video_needed": target // mv if mv > 0 else 0,
        "cold_start_extension_months": 3 if trust == "COLD" else 0,
        "revenue_by_month": {}, "target_achieved_month": 0,
        "note": "COLD 시작 - 타임라인 +3개월" if trust == "COLD" else "",
    }
    write_json(ch_dir / "cashflow_plan.json", plan)
    return plan

def run_step01(channel_ids: list) -> dict:
    results = {}
    for ch in channel_ids:
        logger.info(f"[STEP01] {ch} 측정 시작...")
        bl = create_channel_baseline(ch)
        pl = create_cashflow_plan(ch, bl)
        results[ch] = {"baseline": bl, "plan": pl}
        print(f"[STEP01] {ch}: subs={bl['subscriber_count']} / trust={bl['algorithm_trust_level']}")
    return results

if __name__ == "__main__":
    logging.basicConfig(level="INFO")
    channels = sys.argv[1:] if len(sys.argv) > 1 else ["CH1", "CH2"]
    run_step01(channels)
