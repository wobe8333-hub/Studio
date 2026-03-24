"""
YouTube Analytics API - Top-200 Watchtime + Views 2패스 수집 (OAuth 2.0 필수)
"""

import os
import json
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path

try:
    from googleapiclient.discovery import build
    from google.oauth2.credentials import Credentials
    GOOGLE_API_AVAILABLE = True
except ImportError:
    GOOGLE_API_AVAILABLE = False


def _mask_api_key(key: str) -> str:
    """API Key 마스킹 (로그용)"""
    if not key or len(key) < 8:
        return "***"
    return key[:4] + "***" + key[-4:]


def _load_oauth_credentials(
    client_path: Optional[str] = None,
    token_path: Optional[str] = None
) -> Optional[Credentials]:
    """OAuth 자격증명 로드 (Credentials 객체 반환)"""
    if not GOOGLE_API_AVAILABLE:
        return None
    
    from backend.knowledge_v1.auth.youtube_oauth import load_oauth_credentials
    return load_oauth_credentials(client_path, token_path)


def fetch_top_videos(
    credentials: Optional[Any],  # Credentials 객체 또는 None
    end_date: str,
    lookback_days: int,
    top_k: int,
    sort: str
) -> Dict[str, Any]:
    """
    YouTube Analytics API로 Top 비디오 수집 (pagination: startIndex/maxResults)
    
    Args:
        credentials: OAuth 자격증명 (None이면 실패)
        end_date: 종료일 (YYYY-MM-DD)
        lookback_days: 조회 기간 (일)
        top_k: 수집할 최대 개수
        sort: 정렬 기준 ("-estimatedMinutesWatched" 또는 "-views")
    
    Returns:
        {
            "ok": bool,
            "sort": str,
            "lookback_days": int,
            "requested_top_k": int,
            "returned_count": int,
            "calls": [{"startIndex":int,"rows":int}, ...],
            "items": [{"videoId":str,"views":int,"estimatedMinutesWatched":float}],
            "error": {"class":str,"message":str} | null
        }
    """
    if not credentials or not GOOGLE_API_AVAILABLE:
        return {
            "ok": False,
            "sort": sort,
            "lookback_days": lookback_days,
            "requested_top_k": top_k,
            "returned_count": 0,
            "calls": [],
            "items": [],
            "error": {"class": "OAuthNotConfigured", "message": "OAuth credentials not found or google-api-python-client not installed"}
        }
    
    try:
        # 날짜 계산
        end = datetime.strptime(end_date, "%Y-%m-%d")
        start = end - timedelta(days=lookback_days)
        start_date = start.strftime("%Y-%m-%d")
        
        # Analytics API 빌드
        analytics = build('youtubeAnalytics', 'v2', credentials=credentials)
        
        collected = 0
        items = []
        calls = []
        startIndex = 1
        
        while collected < top_k:
            maxResults = min(200, top_k - collected)
            response = analytics.reports().query(
                ids='channel==MINE',
                startDate=start_date,
                endDate=end_date,
                metrics='views,estimatedMinutesWatched',
                dimensions='video',
                sort=sort,
                startIndex=startIndex,
                maxResults=maxResults
            ).execute()
            
            rows = response.get('rows', [])
            if not rows:
                break
            
            for row in rows:
                video_id = row[0]  # dimensions=video
                views = int(row[1]) if len(row) > 1 else 0
                watchtime = float(row[2]) if len(row) > 2 else 0.0
                items.append({
                    "videoId": video_id,
                    "views": views,
                    "estimatedMinutesWatched": watchtime
                })
            
            rows_count = len(rows)
            collected += rows_count
            calls.append({"startIndex": startIndex, "rows": rows_count})
            startIndex += rows_count
        
        return {
            "ok": True,
            "sort": sort,
            "lookback_days": lookback_days,
            "requested_top_k": top_k,
            "returned_count": collected,
            "calls": calls,
            "items": items,
            "error": None
        }
        
    except Exception as e:
        return {
            "ok": False,
            "sort": sort,
            "lookback_days": lookback_days,
            "requested_top_k": top_k,
            "returned_count": 0,
            "calls": [],
            "items": [],
            "error": {"class": type(e).__name__, "message": str(e)}
        }


def fetch_analytics_top_videos(
    category: str,
    client_path: Optional[str] = None,
    token_path: Optional[str] = None
) -> Dict[str, Any]:
    """
    YouTube Analytics API로 Top-200 Watchtime + Views 2패스 수집 및 합집합
    
    Returns:
        {
            "top_videos": List[Dict],
            "analytics_hint": Dict[str, float],
            "source": "youtube_analytics_api",
            "oauth_configured": bool,
            "snapshot": Dict,
            "error": Optional[str]
        }
    """
    credentials = _load_oauth_credentials(client_path, token_path)
    
    if not credentials:
        return {
            "top_videos": [],
            "analytics_hint": {},
            "source": "youtube_analytics_api",
            "oauth_configured": False,
            "snapshot": {
                "lookback_days": 30,
                "top_k_each": 200,
                "passes": {
                    "watchtime": {"ok": False, "error": {"class": "OAuthNotConfigured", "message": "OAuth credentials not found"}},
                    "views": {"ok": False, "error": {"class": "OAuthNotConfigured", "message": "OAuth credentials not found"}}
                },
                "merge": {"union_count": 0, "overlap_count": 0, "only_watchtime_count": 0, "only_views_count": 0},
                "top_videos": [],
                "ok": False
            },
            "error": "SKIPPED_OAUTH_NOT_CONFIGURED"
        }
    
    lookback_days = 30
    top_k_each = 200
    end_date = datetime.utcnow().strftime("%Y-%m-%d")
    
    # PASS 1: Watchtime Top-200
    pass_watchtime = fetch_top_videos(
        credentials=credentials,
        end_date=end_date,
        lookback_days=lookback_days,
        top_k=top_k_each,
        sort="-estimatedMinutesWatched"
    )
    
    # PASS 2: Views Top-200
    pass_views = fetch_top_videos(
        credentials=credentials,
        end_date=end_date,
        lookback_days=lookback_days,
        top_k=top_k_each,
        sort="-views"
    )
    
    # 합집합 (중복 제거)
    merged = {}
    watchtime_items = {item["videoId"]: item for item in pass_watchtime.get("items", [])}
    views_items = {item["videoId"]: item for item in pass_views.get("items", [])}
    
    for video_id, item in watchtime_items.items():
        merged[video_id] = {
            "videoId": video_id,
            "views": item.get("views", 0),
            "estimatedMinutesWatched": item.get("estimatedMinutesWatched", 0.0),
            "sources": ["watchtime"]
        }
    
    for video_id, item in views_items.items():
        if video_id in merged:
            # 중복: max 값 사용
            merged[video_id]["views"] = max(merged[video_id]["views"], item.get("views", 0))
            merged[video_id]["estimatedMinutesWatched"] = max(
                merged[video_id]["estimatedMinutesWatched"],
                item.get("estimatedMinutesWatched", 0.0)
            )
            merged[video_id]["sources"].append("views")
        else:
            # views만 존재
            merged[video_id] = {
                "videoId": video_id,
                "views": item.get("views", 0),
                "estimatedMinutesWatched": item.get("estimatedMinutesWatched", 0.0),
                "sources": ["views"]
            }
    
    # 통계 계산
    union_count = len(merged)
    overlap_count = sum(1 for v in merged.values() if len(v["sources"]) > 1)
    only_watchtime_count = sum(1 for v in merged.values() if v["sources"] == ["watchtime"])
    only_views_count = sum(1 for v in merged.values() if v["sources"] == ["views"])
    
    # 성과 정규화
    top_videos = list(merged.values())
    if top_videos:
        # score_raw 계산
        for v in top_videos:
            v["score_raw"] = (1.0 * v["views"]) + (0.01 * v["estimatedMinutesWatched"])
        
        # 정규화 (0~1)
        max_score = max(v["score_raw"] for v in top_videos)
        if max_score > 0:
            for v in top_videos:
                v["score_norm"] = v["score_raw"] / max_score
        else:
            for v in top_videos:
                v["score_norm"] = 0.0
    else:
        for v in top_videos:
            v["score_raw"] = 0.0
            v["score_norm"] = 0.0
    
    # 스냅샷 구성
    snapshot = {
        "lookback_days": lookback_days,
        "top_k_each": top_k_each,
        "passes": {
            "watchtime": {
                "sort": "-estimatedMinutesWatched",
                "requested_top_k": top_k_each,
                "maxResults_per_call": 200,
                "calls": pass_watchtime.get("calls", []),
                "returned_count": pass_watchtime.get("returned_count", 0),
                "ok": pass_watchtime.get("ok", False),
                "error": pass_watchtime.get("error")
            },
            "views": {
                "sort": "-views",
                "requested_top_k": top_k_each,
                "maxResults_per_call": 200,
                "calls": pass_views.get("calls", []),
                "returned_count": pass_views.get("returned_count", 0),
                "ok": pass_views.get("ok", False),
                "error": pass_views.get("error")
            }
        },
        "merge": {
            "union_count": union_count,
            "overlap_count": overlap_count,
            "only_watchtime_count": only_watchtime_count,
            "only_views_count": only_views_count
        },
        "top_videos": top_videos[:400],  # 상위 400개까지만 저장
        "ok": union_count > 0
    }
    
    # analytics_hint는 빈 dict (실제로는 Data API v3로 title/description/tags 추출 후 계산)
    analytics_hint = {}
    
    return {
        "top_videos": top_videos,
        "analytics_hint": analytics_hint,
        "source": "youtube_analytics_api",
        "oauth_configured": True,
        "snapshot": snapshot,
        "error": None if snapshot["ok"] else "both_passes_failed"
    }


def fetch_analytics_hints(category: str) -> Dict[str, Any]:
    """
    레거시 호환: fetch_analytics_top_videos 래퍼
    """
    result = fetch_analytics_top_videos(category)
    return {
        "performance_hint": result.get("analytics_hint", {}),
        "source": result.get("source"),
        "oauth_configured": result.get("oauth_configured", False),
        "error": result.get("error")
    }
