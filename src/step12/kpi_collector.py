"""STEP 12 — KPI 수집 (48시간 후).
버그 수정(BUG-kpi): 토큰은 authorized_user JSON 파일 경로로 Credentials 로드.
"""
import logging
from pathlib import Path
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from src.core.ssot import read_json, write_json, json_exists, now_iso, get_run_dir
from src.core.config import CREDENTIALS_DIR
from src.quota.youtube_quota import consume

logger = logging.getLogger(__name__)
ANALYTICS_SCOPES = ["https://www.googleapis.com/auth/yt-analytics.readonly"]

def _get_analytics_service(channel_id: str):
    token_path = CREDENTIALS_DIR / f"{channel_id}_token.json"
    if not token_path.exists():
        raise FileNotFoundError(f"token.json 없음: {token_path}")
    creds = Credentials.from_authorized_user_file(str(token_path), ANALYTICS_SCOPES)
    return build("youtubeAnalytics", "v2", credentials=creds)

def collect_kpi_48h(channel_id: str, run_id: str, video_id: str) -> dict:
    step12_dir = get_run_dir(channel_id, run_id) / "step12"
    step12_dir.mkdir(parents=True, exist_ok=True)
    kpi = {
        "video_id": video_id, "channel_id": channel_id,
        "collected_at": now_iso(),
        "impressions": None, "ctr": None, "views": None,
        "watch_time_hours": None, "avg_view_duration_sec": None,
        "avg_view_percentage": None,
        "traffic_source_browse_pct": None,
        "traffic_source_suggested_pct": None,
        "traffic_source_search_pct": None,
        "missing_reason": None,
    }
    try:
        analytics  = _get_analytics_service(channel_id)
        from datetime import datetime, timedelta
        end_date   = datetime.utcnow().strftime("%Y-%m-%d")
        start_date = (datetime.utcnow() - timedelta(days=2)).strftime("%Y-%m-%d")
        response   = analytics.reports().query(
            ids="channel==MINE",
            startDate=start_date, endDate=end_date,
            metrics="views,estimatedMinutesWatched,averageViewDuration,averageViewPercentage",
            filters=f"video=={video_id}",
        ).execute()
        if response.get("rows"):
            row = response["rows"][0]
            kpi["views"]                = int(row[0]) if row[0] else 0
            kpi["watch_time_hours"]     = round(float(row[1]) / 60, 2) if row[1] else 0
            kpi["avg_view_duration_sec"]= int(row[2]) if row[2] else 0
            kpi["avg_view_percentage"]  = round(float(row[3]), 2) if row[3] else 0
        consume(20, "other")
    except Exception as e:
        kpi["missing_reason"] = f"api_error: {str(e)[:100]}"
        logger.warning(f"KPI_COLLECT_WARN {channel_id}/{run_id}: {e}")

    if kpi["ctr"] is None:
        avp = kpi.get("avg_view_percentage", 0) or 0
        avd = kpi.get("avg_view_duration_sec", 0) or 0
        kpi["ctr_level_estimated"] = ("TARGET" if avp>=45 and avd>=280
                                       else "FLOOR" if avp<35 or avd<240 else "UNKNOWN")
    else:
        ctr = kpi["ctr"]
        kpi["ctr_level"] = "HIT" if ctr >= 8 else "TARGET" if ctr >= 5.5 else "FLOOR"

    _assess_algorithm_stage(channel_id, run_id, kpi, step12_dir)
    write_json(step12_dir / "kpi_48h.json", kpi)
    return kpi

def _assess_algorithm_stage(channel_id: str, run_id: str,
                              kpi: dict, step12_dir: Path) -> None:
    ctr        = kpi.get("ctr")
    avp        = kpi.get("avg_view_percentage", 0) or 0
    browse_pct = kpi.get("traffic_source_browse_pct", 0) or 0
    views      = kpi.get("views", 0) or 0
    if views >= 100000 or (ctr and ctr >= 8):            stage = "ALGORITHM-ACTIVE"
    elif ctr and ctr >= 5.5 and avp >= 45 and browse_pct >= 20: stage = "BROWSE-ENTRY"
    elif ctr and 4 <= ctr < 5.5:                         stage = "SEARCH-ONLY"
    elif avp >= 45 and kpi.get("avg_view_duration_sec",0) >= 280: stage = "BROWSE-ENTRY"
    else:                                                 stage = "PRE-ENTRY"
    write_json(step12_dir / "algorithm_stage_assessment.json", {
        "run_id": run_id, "channel_id": channel_id,
        "assessed_at": now_iso(), "ctr_48h": kpi.get("ctr"),
        "avp_48h": avp, "avd_48h_sec": kpi.get("avg_view_duration_sec"),
        "browse_pct": browse_pct, "views_48h": views,
        "algorithm_stage": stage,
        "stage_basis": "ctr+avp+browse" if ctr else "avp+avd_fallback",
        "action_required": "thumbnail_change_required" if stage == "PRE-ENTRY" else "",
        "missing_reason": kpi.get("missing_reason"),
    })
