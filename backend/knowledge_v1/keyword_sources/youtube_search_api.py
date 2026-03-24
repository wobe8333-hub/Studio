"""
YouTube Data API v3 search.list - 비디오 ID 대량 수집 (Analytics 실패 시 Fallback)
"""

import os
import json
import requests
from datetime import datetime, timedelta
from typing import List, Dict, Any, Tuple, Optional
from pathlib import Path


def _load_api_key() -> Optional[str]:
    """API 키 로딩"""
    api_key = os.getenv("YOUTUBE_API_KEY")
    if api_key:
        return api_key.strip()
    
    # 파일에서 로드
    project_root = Path(__file__).resolve().parents[4]
    key_file = project_root / "backend" / "credentials" / "youtube_api_key.txt"
    
    if key_file.exists():
        try:
            with open(key_file, "r", encoding="utf-8") as f:
                key = f.read().strip()
                if key:
                    return key
        except Exception:
            pass
    
    return None


def fetch_video_ids_via_search(
    seeds: List[str],
    max_videos: int,
    lookback_days: int = 30
) -> Tuple[List[str], Dict[str, Any]]:
    """
    YouTube Data API v3 search.list로 비디오 ID 대량 수집
    
    Args:
        seeds: 검색 키워드 리스트
        max_videos: 수집할 최대 비디오 ID 개수
        lookback_days: 최근 N일 내 비디오만 검색
    
    Returns:
        (video_ids: List[str], snapshot: Dict[str, Any])
    """
    api_key = _load_api_key()
    
    if not api_key:
        return [], {
            "ok": False,
            "seeds_used": seeds,
            "requests_count": 0,
            "fetched_video_ids_count": 0,
            "errors": [{"seed": None, "http_status": None, "message": "YOUTUBE_API_KEY not configured"}]
        }
    
    if not seeds:
        return [], {
        "ok": False,
        "seeds_used": [],
        "requests_count": 0,
        "fetched_video_ids_count": 0,
        "errors": [{"seed": None, "http_status": None, "message": "no seeds provided"}]
    }
    
    video_ids = set()
    errors = []
    requests_count = 0
    
    # publishedAfter 계산 (UTC 기준)
    published_after = (datetime.utcnow() - timedelta(days=lookback_days)).strftime("%Y-%m-%dT%H:%M:%SZ")
    
    # 각 seed로 검색
    for seed in seeds:
        if len(video_ids) >= max_videos:
            break
        
        try:
            url = "https://www.googleapis.com/youtube/v3/search"
            params = {
                "part": "snippet",
                "q": seed,
                "type": "video",
                "order": "viewCount",
                "publishedAfter": published_after,
                "maxResults": min(50, max_videos - len(video_ids)),
                "key": api_key
            }
            
            response = requests.get(url, params=params, timeout=30)
            requests_count += 1
            http_status = response.status_code
            
            if http_status == 200:
                data = response.json()
                items = data.get("items", [])
                
                for item in items:
                    video_id = item.get("id", {}).get("videoId", "")
                    if video_id:
                        video_ids.add(video_id)
                
                if len(video_ids) >= max_videos:
                    break
            else:
                # HTTP 에러
                try:
                    error_data = response.json()
                    error_message = str(error_data)
                except Exception:
                    error_message = response.text[:500] if response.text else f"HTTP {http_status}"
                
                errors.append({
                    "seed": seed,
                    "http_status": http_status,
                    "message": error_message
                })
        
        except requests.exceptions.RequestException as e:
            errors.append({
                "seed": seed,
                "http_status": None,
                "message": f"{type(e).__name__}: {str(e)}"
            })
        except Exception as e:
            errors.append({
                "seed": seed,
                "http_status": None,
                "message": f"{type(e).__name__}: {str(e)}"
            })
    
    video_ids_list = list(video_ids)[:max_videos]
    
    return video_ids_list, {
        "ok": len(video_ids_list) >= 1,
        "seeds_used": seeds,
        "requests_count": requests_count,
        "fetched_video_ids_count": len(video_ids_list),
        "errors": errors
    }

