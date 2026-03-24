"""
YouTube Data API 트렌드 앵커 (저쿼터)
STEP D: KR 트렌드 후보 최대 50개 수집
"""

import os
import json
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional

from backend.knowledge_v1.paths import get_root


def _load_api_key() -> Optional[str]:
    """API 키 로딩"""
    api_key = os.getenv("YOUTUBE_DATA_API_KEY") or os.getenv("YOUTUBE_API_KEY")
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


def collect_trending_anchor(
    region: str = "KR",
    max_keywords: int = 50,
    cycle_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    YouTube Data API로 트렌드 앵커 수집 (저쿼터)
    
    Args:
        region: 지역 코드 (기본 "KR")
        max_keywords: 최대 키워드 수 (기본 50)
        cycle_id: cycle_id (선택)
    
    Returns:
        {
            "ok": bool,
            "region": str,
            "collected_at": str,
            "keywords": List[str],
            "quota": {"used": int|null, "remaining": int|null},
            "request_meta": Dict,
            "error": Optional[str]
        }
    """
    api_key = _load_api_key()
    if not api_key:
        return {
            "ok": False,
            "region": region,
            "collected_at": datetime.utcnow().isoformat() + "Z",
            "keywords": [],
            "quota": {"used": None, "remaining": None},
            "request_meta": {},
            "error": "YOUTUBE_DATA_API_KEY not configured"
        }
    
    # 경로 설정
    kd_root = get_root() / "keyword_discovery"
    anchor_dir = kd_root / "anchors"
    anchor_dir.mkdir(parents=True, exist_ok=True)
    
    collected_at = datetime.utcnow().isoformat() + "Z"
    keywords: List[str] = []
    quota_used = None
    quota_remaining = None
    request_meta: Dict[str, Any] = {}
    error = None
    
    try:
        import urllib.request
        import urllib.parse
        
        # YouTube Data API v3 videos.list (trending)
        # region_code=KR, maxResults=50
        base_url = "https://www.googleapis.com/youtube/v3/videos"
        params = {
            "part": "snippet",
            "chart": "mostPopular",
            "regionCode": region,
            "maxResults": min(max_keywords, 50),
            "key": api_key
        }
        
        url = f"{base_url}?{urllib.parse.urlencode(params)}"
        
        with urllib.request.urlopen(url, timeout=15) as response:
            data = json.loads(response.read().decode("utf-8"))
            
            if "items" in data:
                for item in data.get("items", []):
                    snippet = item.get("snippet", {})
                    title = snippet.get("title", "").strip()
                    if title:
                        keywords.append(title)
                
                # 쿼터 정보 (응답에 있으면)
                if "quota" in data:
                    quota_used = data["quota"].get("used")
                    quota_remaining = data["quota"].get("remaining")
                
                request_meta = {
                    "items_count": len(data.get("items", [])),
                    "region_code": region,
                    "http_status": response.status
                }
            else:
                error = data.get("error", {}).get("message", "unknown_error")
                request_meta = {"error": error}
    
    except Exception as e:
        error = f"{type(e).__name__}: {str(e)[:200]}"
        request_meta = {"exception": error}
    
    result = {
        "ok": len(keywords) >= 1 and error is None,
        "region": region,
        "collected_at": collected_at,
        "keywords": keywords[:max_keywords],
        "quota": {
            "used": quota_used,
            "remaining": quota_remaining
        },
        "request_meta": request_meta
    }
    
    if error:
        result["error"] = error
    
    # 산출물 저장
    anchor_file = anchor_dir / f"youtube_data_api_anchor_{region.lower()}.json"
    with open(anchor_file, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    # quota_log.jsonl append
    quota_log_file = anchor_dir / "quota_log.jsonl"
    quota_log_entry = {
        "ts": collected_at,
        "used": quota_used,
        "remaining": quota_remaining,
        "request_meta": request_meta,
        "cycle_id": cycle_id
    }
    with open(quota_log_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(quota_log_entry, ensure_ascii=False) + "\n")
    
    return result

