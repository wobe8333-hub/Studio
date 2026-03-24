"""
YouTube Data API Trending Collector - videos.list(chart=mostPopular) 트렌딩 앵커 수집
"""

import os
import json
import urllib.request
import urllib.parse
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple


def _load_api_key() -> str:
    """API 키 로드 - SSOT는 환경변수 YOUTUBE_DATA_API_KEY (호환 2종 포함)"""
    primary = (os.getenv("YOUTUBE_DATA_API_KEY") or "").strip()
    compat_ytdapi = (os.getenv("YTDAPI_API_KEY") or "").strip()
    compat_youtube = (os.getenv("YOUTUBE_API_KEY") or "").strip()

    for candidate in (primary, compat_ytdapi, compat_youtube):
        if candidate:
            return candidate

    # 모든 환경변수가 비어 있으면 즉시 실패
    raise RuntimeError("MISSING_YOUTUBE_DATA_API_KEY")


def _load_categories_config(categories_file: str) -> List[str]:
    """카테고리 설정 파일 로드"""
    try:
        config_path = Path(categories_file)
        if config_path.exists():
            with open(config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
                categories = config.get("categories", [])
                if categories:
                    return [str(c) for c in categories]
    except Exception:
        pass
    
    # 기본값: ["0"] (전체)
    return ["0"]


def _call_videos_list(
    api_key: str,
    region_code: str = "KR",
    max_results: int = 50,
    video_category_id: Optional[str] = None
) -> Tuple[Dict[str, Any], int]:
    """
    YouTube Data API videos.list 호출 (chart=mostPopular만)
    
    Args:
        api_key: API 키
        region_code: 지역 코드 (기본 "KR")
        max_results: 최대 결과 수 (기본 50)
        video_category_id: 비디오 카테고리 ID (선택)
    
    Returns:
        (response_dict, units_used)
        units_used: 1 (videos.list 호출 1회당 1 unit)
    """
    base_url = "https://www.googleapis.com/youtube/v3/videos"
    
    params = {
        "part": "snippet,statistics",
        "chart": "mostPopular",
        "regionCode": region_code,
        "maxResults": min(max_results, 50),  # 최대 50
        "key": api_key
    }
    
    if video_category_id:
        params["videoCategoryId"] = video_category_id
    
    # URL 구성
    url = f"{base_url}?{urllib.parse.urlencode(params)}"
    
    try:
        # HTTP 요청
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=30) as response:
            response_data = json.loads(response.read().decode("utf-8"))
            
            # 응답 처리
            items = []
            for item in response_data.get("items", []):
                snippet = item.get("snippet", {})
                statistics = item.get("statistics", {})
                
                items.append({
                    "videoId": item.get("id", ""),
                    "title": snippet.get("title", ""),
                    "channelId": snippet.get("channelId", ""),
                    "channelTitle": snippet.get("channelTitle", ""),
                    "publishedAt": snippet.get("publishedAt", ""),
                    "viewCount": int(statistics.get("viewCount", 0)) if statistics.get("viewCount") else 0
                })
            
            return {
                "ok": True,
                "items": items,
                "total_results": len(items),
                "nextPageToken": response_data.get("nextPageToken")
            }, 1  # 1 unit used
            
    except urllib.error.HTTPError as e:
        error_data = {}
        try:
            error_body = e.read().decode("utf-8")
            error_data = json.loads(error_body)
        except Exception:
            pass
        
        error_message = error_data.get("error", {}).get("message", str(e))
        return {
            "ok": False,
            "items": [],
            "total_results": 0,
            "error_type": "HTTPError",
            "http_status": e.code,
            "error_message": error_message
        }, 1  # 시도한 호출은 quota 차감됨
        
    except Exception as e:
        return {
            "ok": False,
            "items": [],
            "total_results": 0,
            "error_type": type(e).__name__,
            "error_message": str(e)
        }, 0  # 네트워크 오류 등은 quota 미사용으로 간주


def collect_ytdapi_trending(
    cycle_id: str,
    snapshot_dir: Path,
    region_code: str = "KR",
    max_results: int = 50,
    categories_file: str = "backend/config/ytdapi_trending_categories_kr.json",
    quota_max_units: int = 50
) -> Dict[str, Any]:
    """
    YouTube Data API 트렌딩 수집 (videos.list chart=mostPopular만)
    
    Args:
        cycle_id: 사이클 ID
        snapshot_dir: 스냅샷 디렉토리
        region_code: 지역 코드
        max_results: 카테고리당 최대 결과 수
        categories_file: 카테고리 설정 파일 경로
        quota_max_units: 최대 쿼터 사용량
    
    Returns:
        {
            "trending_path": str,
            "quota_path": str,
            "errors_path": str,
            "ok": bool,
            "total_items": int,
            "units_total": int
        }
    """
    enabled = os.getenv("YTDAPI_TRENDING_ENABLED", "0") in ["1", "true", "True"]
    
    signals_dir = snapshot_dir / "signals"
    signals_dir.mkdir(parents=True, exist_ok=True)
    
    trending_path = signals_dir / "ytdapi_trending_kr.json"
    quota_path = signals_dir / "ytdapi_trending_kr_quota.json"
    errors_path = signals_dir / "ytdapi_trending_kr_errors.json"
    
    if not enabled:
        # disabled인 경우 빈 JSON 생성
        trending_json = {
            "cycle_id": cycle_id,
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "scope": "KR",
            "provider": "youtube_data_api",
            "mode": "mostPopular",
            "regionCode": region_code,
            "categories": []
        }
        
        quota_json = {
            "cycle_id": cycle_id,
            "requests": [],
            "units_total": 0
        }
        
        with open(trending_path, "w", encoding="utf-8") as f:
            json.dump(trending_json, f, ensure_ascii=False, indent=2)
        
        with open(quota_path, "w", encoding="utf-8") as f:
            json.dump(quota_json, f, ensure_ascii=False, indent=2)
        
        with open(errors_path, "w", encoding="utf-8") as f:
            json.dump([{
                "source": "ytdapi_trending",
                "error_type": "Disabled",
                "error_message": "YTDAPI_TRENDING_ENABLED=0",
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }], f, ensure_ascii=False, indent=2)
        
        return {
            "trending_path": str(trending_path),
            "quota_path": str(quota_path),
            "errors_path": str(errors_path),
            "ok": True,
            "total_items": 0,
            "units_total": 0
        }
    
    # API 키 확인 (없으면 RuntimeError로 fail-fast)
    api_key = _load_api_key()
    
    # 카테고리 로드
    categories = _load_categories_config(categories_file)
    
    # 각 카테고리별로 호출
    category_results = []
    quota_requests = []
    errors = []
    units_total = 0
    total_items = 0
    
    for video_category_id in categories:
        try:
            response, units_used = _call_videos_list(
                api_key=api_key,
                region_code=region_code,
                max_results=max_results,
                video_category_id=video_category_id if video_category_id != "0" else None
            )
            
            units_total += units_used
            
            # 쿼터 상한 확인
            if units_total > quota_max_units:
                errors.append({
                    "source": "ytdapi_trending",
                    "error_type": "QuotaExceeded",
                    "error_message": f"quota_max_units ({quota_max_units}) exceeded",
                    "timestamp": datetime.utcnow().isoformat() + "Z"
                })
                break
            
            quota_requests.append({
                "endpoint": "videos.list",
                "count": 1,
                "units_per_call": 1,
                "units_total": units_total,
                "note": f"chart=mostPopular region={region_code} cat={video_category_id}"
            })
            
            if response.get("ok"):
                category_results.append({
                    "videoCategoryId": video_category_id,
                    "maxResults": max_results,
                    "status": "ok",
                    "items": response.get("items", [])
                })
                total_items += len(response.get("items", []))
            else:
                category_results.append({
                    "videoCategoryId": video_category_id,
                    "maxResults": max_results,
                    "status": "error",
                    "items": [],
                    "error": {
                        "error_type": response.get("error_type"),
                        "http_status": response.get("http_status"),
                        "error_message": response.get("error_message")
                    }
                })
                errors.append({
                    "source": "ytdapi_trending",
                    "error_type": response.get("error_type", "Unknown"),
                    "error_message": response.get("error_message", "unknown error"),
                    "video_category_id": video_category_id,
                    "http_status": response.get("http_status"),
                    "timestamp": datetime.utcnow().isoformat() + "Z"
                })
                
        except Exception as e:
            errors.append({
                "source": "ytdapi_trending",
                "error_type": type(e).__name__,
                "error_message": str(e),
                "video_category_id": video_category_id,
                "timestamp": datetime.utcnow().isoformat() + "Z"
            })
            category_results.append({
                "videoCategoryId": video_category_id,
                "maxResults": max_results,
                "status": "error",
                "items": [],
                "error": {
                    "error_type": type(e).__name__,
                    "error_message": str(e)
                }
            })
    
    # JSON 생성
    trending_json = {
        "cycle_id": cycle_id,
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "scope": "KR",
        "provider": "youtube_data_api",
        "mode": "mostPopular",
        "regionCode": region_code,
        "categories": category_results
    }
    
    quota_json = {
        "cycle_id": cycle_id,
        "requests": quota_requests,
        "units_total": units_total
    }
    
    # 파일 저장
    with open(trending_path, "w", encoding="utf-8") as f:
        json.dump(trending_json, f, ensure_ascii=False, indent=2)
    
    with open(quota_path, "w", encoding="utf-8") as f:
        json.dump(quota_json, f, ensure_ascii=False, indent=2)
    
    with open(errors_path, "w", encoding="utf-8") as f:
        json.dump(errors, f, ensure_ascii=False, indent=2)
    
    return {
        "trending_path": str(trending_path),
        "quota_path": str(quota_path),
        "errors_path": str(errors_path),
        "ok": len(errors) == 0 and total_items > 0,
        "total_items": total_items,
        "units_total": units_total
    }

