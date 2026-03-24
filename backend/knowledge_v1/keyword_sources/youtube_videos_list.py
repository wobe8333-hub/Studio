"""
YouTube Data API v3 videos.list - 대량 비디오 메타데이터 수집
"""

import os
import json
import requests
from typing import Dict, Any, List, Optional
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


def fetch_videos_list_snapshot(video_ids: List[str]) -> Dict[str, Any]:
    """
    YouTube Data API v3 videos.list로 대량 비디오 메타데이터 수집 (50개 배치)
    
    Args:
        video_ids: Video ID 리스트
    
    Returns:
        {
            "ok": bool,
            "requested_video_ids": int,
            "fetched_items": int,
            "missing_video_ids": int,
            "batches": int,
            "errors": [{"batch_index": int, "http_status": int, "message": str}],
            "items": [
                {
                    "video_id": str,
                    "title": str,
                    "description": str,
                    "tags": [str],
                    "channelTitle": str,
                    "publishedAt": str
                }
            ]
        }
    """
    api_key = _load_api_key()
    
    if not api_key:
        return {
            "ok": False,
            "requested_video_ids": len(video_ids),
            "fetched_items": 0,
            "missing_video_ids": len(video_ids),
            "batches": 0,
            "errors": [{"batch_index": 0, "http_status": None, "message": "YOUTUBE_API_KEY not configured"}],
            "items": []
        }
    
    if not video_ids:
        return {
            "ok": False,
            "requested_video_ids": 0,
            "fetched_items": 0,
            "missing_video_ids": 0,
            "batches": 0,
            "errors": [],
            "items": []
        }
    
    items = []
    errors = []
    fetched_ids = set()
    
    # 50개 단위로 배치 처리
    batch_size = 50
    batches = (len(video_ids) + batch_size - 1) // batch_size
    
    for batch_idx in range(batches):
        start_idx = batch_idx * batch_size
        end_idx = min(start_idx + batch_size, len(video_ids))
        batch_ids = video_ids[start_idx:end_idx]
        
        try:
            # API 호출
            url = "https://www.googleapis.com/youtube/v3/videos"
            params = {
                "part": "snippet",
                "id": ",".join(batch_ids),
                "key": api_key
            }
            
            response = requests.get(url, params=params, timeout=30)
            http_status = response.status_code
            
            if http_status == 200:
                data = response.json()
                api_items = data.get("items", [])
                
                for item in api_items:
                    video_id = item.get("id", "")
                    snippet = item.get("snippet", {})
                    
                    items.append({
                        "video_id": video_id,
                        "title": snippet.get("title", ""),
                        "description": snippet.get("description", ""),
                        "tags": snippet.get("tags", []),
                        "channelTitle": snippet.get("channelTitle", ""),
                        "publishedAt": snippet.get("publishedAt", "")
                    })
                    fetched_ids.add(video_id)
            else:
                # HTTP 에러
                try:
                    error_data = response.json()
                    error_message = str(error_data)
                except Exception:
                    error_message = response.text[:500] if response.text else f"HTTP {http_status}"
                
                errors.append({
                    "batch_index": batch_idx,
                    "http_status": http_status,
                    "message": error_message
                })
        
        except requests.exceptions.RequestException as e:
            errors.append({
                "batch_index": batch_idx,
                "http_status": None,
                "message": f"{type(e).__name__}: {str(e)}"
            })
        except Exception as e:
            errors.append({
                "batch_index": batch_idx,
                "http_status": None,
                "message": f"{type(e).__name__}: {str(e)}"
            })
    
    # 누락된 video_ids 계산
    missing_ids = [vid for vid in video_ids if vid not in fetched_ids]
    
    return {
        "ok": len(items) >= 1,
        "requested_video_ids": len(video_ids),
        "fetched_items": len(items),
        "missing_video_ids": len(missing_ids),
        "batches": batches,
        "errors": errors,
        "items": items
    }


def fetch_most_popular_titles(
    *,
    region_code: str = "KR",
    max_results: int = 50,
) -> Dict[str, Any]:
    """
    videos.list chart=mostPopular title 수집.
    """
    api_key = _load_api_key()
    if not api_key:
        return {
            "ok": False,
            "reason": "apiKeyMissing",
            "titles": [],
            "items": [],
            "errors": [{"message": "YOUTUBE_API_KEY missing"}],
        }

    url = "https://www.googleapis.com/youtube/v3/videos"
    params = {
        "part": "snippet",
        "chart": "mostPopular",
        "regionCode": region_code,
        "maxResults": min(max_results, 50),
        "key": api_key,
    }
    try:
        resp = requests.get(url, params=params, timeout=20)
        if resp.status_code != 200:
            reason = "youtubeError"
            text = ""
            try:
                payload = resp.json()
                text = json.dumps(payload, ensure_ascii=False)
            except Exception:
                text = resp.text or ""
            lower = text.lower()
            if "api key expired" in lower or "keyexpired" in lower:
                reason = "keyExpired"
            elif resp.status_code == 403 or "quota" in lower:
                reason = "quotaExceeded"
            return {
                "ok": False,
                "reason": reason,
                "titles": [],
                "items": [],
                "errors": [{"http_status": resp.status_code, "message": text[:500]}],
            }

        data = resp.json()
        items = data.get("items", []) if isinstance(data, dict) else []
        titles = []
        for item in items:
            snippet = item.get("snippet", {}) if isinstance(item, dict) else {}
            title = (snippet.get("title") or "").strip()
            if title:
                titles.append(title)
        return {"ok": True, "reason": None, "titles": titles, "items": items, "errors": []}
    except requests.exceptions.RequestException as e:
        return {
            "ok": False,
            "reason": "youtubeError",
            "titles": [],
            "items": [],
            "errors": [{"message": f"{type(e).__name__}: {str(e)}"}],
        }
