"""피드백 루프 — YouTube Analytics KPI → Episode Metadata 기록 → 차기 기획 반영 (최적화 ①)

PQS 학습용 kpi_48h / kpi_7d 필드를 episode JSON에 직접 기록.
차기 시리즈 기획 summary는 data/global/learning_feedback.json 에 저장.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import httpx
from loguru import logger

from src.core.ssot import read_json, write_json
from src.pipeline_v2.episode_schema import EpisodeKpi, EpisodeMeta, load_episode, save_episode

LEARNING_FEEDBACK_PATH = Path("data/global/learning_feedback.json")
YOUTUBE_ANALYTICS_BASE = "https://youtubeanalytics.googleapis.com/v2"


def _get_oauth_token(channel_id: str) -> str:
    token_path = Path(f"credentials/{channel_id}_token.json")
    if not token_path.exists():
        raise FileNotFoundError(f"OAuth 토큰 없음: {token_path}")
    token_data = read_json(token_path)
    return token_data.get("access_token", "")


def _fetch_video_analytics(video_id: str, channel_id: str, days: int = 2) -> dict:
    """YouTube Analytics API로 영상 KPI 수집."""
    token = _get_oauth_token(channel_id)
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    params = {
        "ids": "channel==MINE",
        "startDate": today,
        "endDate": today,
        "metrics": "views,estimatedMinutesWatched,averageViewDuration,averageViewPercentage,annotationClickThroughRate",
        "filters": f"video=={video_id}",
        "dimensions": "video",
    }
    headers = {"Authorization": f"Bearer {token}"}

    try:
        with httpx.Client(timeout=30) as client:
            resp = client.get(f"{YOUTUBE_ANALYTICS_BASE}/reports", params=params, headers=headers)
            resp.raise_for_status()
            data = resp.json()

        rows = data.get("rows", [])
        if not rows:
            return {}
        row = rows[0]
        headers_list = [h["name"] for h in data.get("columnHeaders", [])]
        return dict(zip(headers_list, row))
    except Exception as e:
        logger.warning(f"Analytics API 실패 ({video_id}): {e}")
        return {}


def collect_episode_kpi(
    episode_id: str,
    channel_id: str,
    video_id: str,
    window: str = "48h",
    year_month: str | None = None,
) -> EpisodeMeta:
    """48h / 7d KPI를 수집해 episode metadata에 기록."""
    meta = load_episode(channel_id, episode_id, year_month)
    analytics = _fetch_video_analytics(video_id, channel_id)

    kpi = EpisodeKpi(
        views=int(analytics.get("views", 0)) or None,
        ctr=float(analytics.get("annotationClickThroughRate", 0)) or None,
        avd_pct=float(analytics.get("averageViewPercentage", 0)) or None,
    )

    if window == "48h":
        meta.kpi_48h = kpi
        logger.info(f"KPI 48h 기록: {episode_id} views={kpi.views} ctr={kpi.ctr}")
    else:
        meta.kpi_7d = kpi
        logger.info(f"KPI 7d 기록: {episode_id} views={kpi.views} ctr={kpi.ctr}")

    save_episode(meta)
    return meta


def generate_next_series_input(
    channel_id: str,
    recent_episodes: list[EpisodeMeta],
) -> dict:
    """최근 에피소드 KPI 분석 → 차기 시리즈 기획 input 생성."""
    if not recent_episodes:
        return {}

    # 성과 기반 winning pattern 탐지
    sorted_eps = sorted(
        [ep for ep in recent_episodes if ep.kpi_48h.ctr is not None],
        key=lambda e: (e.kpi_48h.ctr or 0),
        reverse=True,
    )

    winning_hooks = [ep.features.title_hook_type for ep in sorted_eps[:3] if ep.features.title_hook_type]
    best_bgm_tags = [ep.features.bgm_mood_tag for ep in sorted_eps[:3] if ep.features.bgm_mood_tag]
    avg_ctr = sum(ep.kpi_48h.ctr or 0 for ep in recent_episodes) / len(recent_episodes)
    avg_avd = sum(ep.kpi_48h.avd_pct or 0 for ep in recent_episodes) / len(recent_episodes)

    losing_segments = [
        {"episode_id": ep.episode_id, "avd_pct": ep.kpi_48h.avd_pct}
        for ep in sorted_eps[-3:]
        if ep.kpi_48h.avd_pct is not None and ep.kpi_48h.avd_pct < 40
    ]

    feedback = {
        "channel_id": channel_id,
        "analyzed_at": datetime.now(timezone.utc).isoformat(),
        "episode_count": len(recent_episodes),
        "avg_ctr": round(avg_ctr, 4),
        "avg_avd_pct": round(avg_avd, 2),
        "winning_hooks": winning_hooks,
        "best_bgm_tags": best_bgm_tags,
        "losing_segments": losing_segments,
        "recommended_topics": [],  # content-director가 채움
        "recommended_hook_types": winning_hooks[:2],
    }

    for ep in recent_episodes:
        ep.feedback_cycle_input.winning_hook = winning_hooks[0] if winning_hooks else None
        ep.feedback_cycle_input.losing_segments = losing_segments
        save_episode(ep)

    _append_learning_feedback(feedback)
    logger.info(f"피드백 루프 완료: {channel_id} avg_ctr={avg_ctr:.3f} avg_avd={avg_avd:.1f}%")
    return feedback


def _append_learning_feedback(feedback: dict) -> None:
    existing = []
    if LEARNING_FEEDBACK_PATH.exists():
        try:
            existing = read_json(LEARNING_FEEDBACK_PATH)
            if not isinstance(existing, list):
                existing = [existing]
        except Exception:
            existing = []
    existing.append(feedback)
    write_json(LEARNING_FEEDBACK_PATH, existing[-200:])  # 최근 200건만 유지
