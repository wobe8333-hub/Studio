"""STEP 12 — KPI 수집 (48시간 후).
버그 수정(BUG-kpi): 토큰은 authorized_user JSON 파일 경로로 Credentials 로드.
E-3: impressions / impressionClickThroughRate(CTR) 메트릭 추가.
"""
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from loguru import logger

from src.core.config import CREDENTIALS_DIR, USD_TO_KRW
from src.core.ssot import get_run_dir, now_iso, write_json
from src.quota.youtube_quota import consume

ANALYTICS_SCOPES = [
    "https://www.googleapis.com/auth/yt-analytics.readonly",
    "https://www.googleapis.com/auth/yt-analytics-monetary.readonly",  # 수익 데이터
    "https://www.googleapis.com/auth/youtube.readonly",
]

# Analytics API 메트릭 순서 (index로 row 값 매핑)
_ANALYTICS_METRICS = (
    "views,estimatedMinutesWatched,averageViewDuration,averageViewPercentage,"
    "impressions,impressionClickThroughRate,"
    "estimatedRevenue,estimatedRevenuePer1000Views"
)
_METRIC_IDX = {
    "views": 0,
    "estimated_minutes_watched": 1,
    "avg_view_duration_sec": 2,
    "avg_view_percentage": 3,
    "impressions": 4,
    "ctr": 5,
    "estimated_revenue_usd": 6,
    "rpm_actual_usd": 7,
}

def _get_analytics_service(channel_id: str):
    """Analytics API 서비스 빌드. 만료 토큰은 자동 갱신한다."""
    token_path = CREDENTIALS_DIR / f"{channel_id}_token.json"
    if not token_path.exists():
        raise FileNotFoundError(f"token.json 없음: {token_path}")
    creds = Credentials.from_authorized_user_file(str(token_path), ANALYTICS_SCOPES)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        token_path.write_text(creds.to_json(), encoding="utf-8")
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
        "estimated_revenue_usd": None,  # YouTube 보고 통화(USD)
        "rpm_actual_usd": None,         # RPM (USD/1,000회)
        "rpm_actual_krw": None,         # RPM (KRW 환산, USD_TO_KRW 기준)
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
            metrics=_ANALYTICS_METRICS,
            filters=f"video=={video_id}",
        ).execute()
        if response.get("rows"):
            row = response["rows"][0]
            def _int(v):   return int(v) if v else 0
            def _float(v): return round(float(v), 4) if v else 0.0
            kpi["views"]                = _int(row[_METRIC_IDX["views"]])
            kpi["watch_time_hours"]     = round(_float(row[_METRIC_IDX["estimated_minutes_watched"]]) / 60, 2)
            kpi["avg_view_duration_sec"]= _int(row[_METRIC_IDX["avg_view_duration_sec"]])
            kpi["avg_view_percentage"]  = _float(row[_METRIC_IDX["avg_view_percentage"]])
            kpi["impressions"]          = _int(row[_METRIC_IDX["impressions"]])
            kpi["ctr"]                  = round(_float(row[_METRIC_IDX["ctr"]]) * 100, 2)  # 소수 → %
            # RPM 실측값: YouTube는 USD로 보고, KRW 환산 저장
            rpm_usd = _float(row[_METRIC_IDX["rpm_actual_usd"]])
            if rpm_usd > 0:
                kpi["estimated_revenue_usd"] = round(_float(row[_METRIC_IDX["estimated_revenue_usd"]]), 4)
                kpi["rpm_actual_usd"]        = round(rpm_usd, 4)
                kpi["rpm_actual_krw"]        = int(rpm_usd * USD_TO_KRW)
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
