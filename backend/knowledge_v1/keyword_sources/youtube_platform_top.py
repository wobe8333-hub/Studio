"""
YouTube Data API v3 - 플랫폼 전체 Top 영상 확보 (mostPopular + search)
PATCH: 쿼터 최적화 (캐시, 예산, ledger)
"""

import os
import json
import requests
import hashlib
from typing import List, Dict, Any, Tuple, Optional
from pathlib import Path
from datetime import datetime, timedelta


# 쿼터 비용 상수
SEARCH_CALL_COST_UNITS = 100  # /search 호출당 100 units
VIDEOS_CALL_COST_UNITS = 1    # /videos 호출당 1 unit

# 캐시 스키마 버전
CACHE_SCHEMA_VERSION = "1.0"


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
                key = f.read().strip().split("\n")[0]
                if key:
                    return key
        except Exception:
            pass
    
    return None


def _get_cache_root() -> Path:
    """캐시 루트 경로 반환"""
    backend_dir = Path(__file__).resolve().parent.parent.parent
    project_root = backend_dir.parent
    cache_root = project_root / "backend" / "output" / "knowledge_v1" / "cache" / "youtube_api"
    cache_root.mkdir(parents=True, exist_ok=True)
    return cache_root


def _get_ledger_path() -> Path:
    """호출 원장 경로 반환"""
    cache_root = _get_cache_root()
    ledger_path = cache_root / "api_call_ledger.jsonl"
    return ledger_path


def _compute_cache_key(endpoint: str, params: Dict[str, Any]) -> str:
    """캐시키 계산 (sha256)"""
    params_sorted = json.dumps(params, sort_keys=True, ensure_ascii=False)
    cache_input = f"{endpoint}|{params_sorted}|{CACHE_SCHEMA_VERSION}"
    return hashlib.sha256(cache_input.encode("utf-8")).hexdigest()


def _get_cache_path(cache_key: str) -> Path:
    """캐시 파일 경로 반환"""
    cache_root = _get_cache_root()
    return cache_root / f"{cache_key}.json"


def _load_cache(cache_path: Path, ttl_seconds: int) -> Optional[Dict[str, Any]]:
    """캐시 로드 및 검증"""
    if not cache_path.exists():
        return None
    
    try:
        # 파일 크기 검증
        if cache_path.stat().st_size == 0:
            return None
        
        # JSON 파싱
        with open(cache_path, "r", encoding="utf-8") as f:
            cached_data = json.load(f)
        
        # 최소 필드 검증
        if not isinstance(cached_data, dict):
            return None
        
        # TTL 검증
        cached_at_str = cached_data.get("cached_at")
        if cached_at_str:
            try:
                cached_at = datetime.fromisoformat(cached_at_str.replace("Z", "+00:00"))
                if cached_at.tzinfo:
                    cached_at = cached_at.replace(tzinfo=None) - timedelta(hours=9)  # UTC to local
                age = (datetime.utcnow() - cached_at).total_seconds()
                if age > ttl_seconds:
                    return None
            except Exception:
                pass
        
        # response_hash 검증 (있는 경우)
        response_hash = cached_data.get("response_hash")
        if response_hash:
            response_data = cached_data.get("response", {})
            response_json = json.dumps(response_data, sort_keys=True, ensure_ascii=False)
            computed_hash = hashlib.sha256(response_json.encode("utf-8")).hexdigest()
            if computed_hash != response_hash:
                return None
        
        return cached_data.get("response")
    except Exception:
        # 캐시 오염 시 무효 처리
        try:
            cache_path.unlink()
        except Exception:
            pass
        return None


def _save_cache(cache_path: Path, response_data: Dict[str, Any]) -> None:
    """캐시 저장"""
    try:
        response_json = json.dumps(response_data, sort_keys=True, ensure_ascii=False)
        response_hash = hashlib.sha256(response_json.encode("utf-8")).hexdigest()
        
        cached_entry = {
            "cached_at": datetime.utcnow().isoformat() + "Z",
            "response": response_data,
            "response_hash": response_hash,
            "schema_version": CACHE_SCHEMA_VERSION
        }
        
        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump(cached_entry, f, ensure_ascii=False, indent=2)
    except Exception:
        pass  # 캐시 저장 실패해도 계속 진행


def _log_api_call(
    cycle_id: str,
    endpoint: str,
    params_hash: str,
    cache_hit: bool,
    cost_units: int,
    status: str,
    error_msg: Optional[str] = None
) -> None:
    """API 호출 원장 기록"""
    try:
        ledger_path = _get_ledger_path()
        entry = {
            "cycle_id": cycle_id,
            "ts_utc": datetime.utcnow().isoformat() + "Z",
            "endpoint": endpoint,
            "params_hash": params_hash,
            "cache_hit": cache_hit,
            "cost_units": cost_units,
            "status": status
        }
        if error_msg:
            entry["error_msg"] = error_msg[:500]  # 최대 500자
        
        with open(ledger_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception:
        pass  # ledger 기록 실패해도 계속 진행


def _make_api_request(
    cycle_id: str,
    endpoint: str,
    params: Dict[str, Any],
    cost_units: int,
    ttl_seconds: int
) -> Tuple[Optional[Dict[str, Any]], bool, Optional[str]]:
    """
    API 요청 (캐시 지원)
    
    Returns:
        (response_data, cache_hit, error_msg)
    """
    params_hash = _compute_cache_key(endpoint, params)
    cache_path = _get_cache_path(params_hash)
    
    # 캐시 확인
    cached_response = _load_cache(cache_path, ttl_seconds)
    if cached_response is not None:
        _log_api_call(cycle_id, endpoint, params_hash, True, 0, "ok")
        return cached_response, True, None
    
    # 네트워크 호출
    try:
        url = f"https://www.googleapis.com/youtube/v3/{endpoint}"
        response = requests.get(url, params=params, timeout=30)
        http_status = response.status_code
        
        if http_status == 200:
            data = response.json()
            # 캐시 저장
            _save_cache(cache_path, data)
            _log_api_call(cycle_id, endpoint, params_hash, False, cost_units, "ok")
            return data, False, None
        else:
            try:
                error_data = response.json()
                error_message = str(error_data)[:500]
            except Exception:
                error_message = response.text[:500] if response.text else f"HTTP {http_status}"
            
            _log_api_call(cycle_id, endpoint, params_hash, False, cost_units, "error", error_message)
            return None, False, error_message
    except requests.exceptions.RequestException as e:
        error_msg = f"{type(e).__name__}: {str(e)}"[:500]
        _log_api_call(cycle_id, endpoint, params_hash, False, cost_units, "error", error_msg)
        return None, False, error_msg
    except Exception as e:
        error_msg = f"{type(e).__name__}: {str(e)}"[:500]
        _log_api_call(cycle_id, endpoint, params_hash, False, cost_units, "error", error_msg)
        return None, False, error_msg


def fetch_platform_top_video_ids(
    categories: List[str],
    max_videos: int,
    region_codes: List[str] = None,
    cycle_id: Optional[str] = None
) -> Tuple[List[str], Dict[str, Any]]:
    """
    YouTube Data API로 플랫폼 전체 Top 영상 ID 수집
    
    Args:
        categories: 카테고리 리스트 (seed로 사용)
        max_videos: 최대 수집할 비디오 ID 개수
        region_codes: 지역 코드 리스트 (기본: ["US", "KR"])
        cycle_id: 사이클 ID (ledger 기록용, 없으면 자동 생성)
    
    Returns:
        (video_ids: List[str], snapshot: Dict[str, Any])
    """
    if cycle_id is None:
        cycle_id = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    
    if region_codes is None:
        region_codes = ["US", "KR"]
    
    api_key = _load_api_key()
    
    if not api_key:
        return [], {
            "ok": False,
            "api_key_configured": False,
            "region_codes": region_codes,
            "max_videos": max_videos,
            "counts": {
                "mostPopular": 0,
                "viewCount": 0,
                "relevance": 0,
                "union_count": 0,
                "api_calls_videos_mostPopular": 0,
                "api_calls_search_viewCount": 0,
                "cache_hits": 0,
                "cache_misses": 0,
                "quota_units_estimated_used": 0,
                "search_skipped_due_to_budget_count": 0
            },
            "errors": [{"source": "api_key", "http_status": None, "message": "YOUTUBE_API_KEY not configured"}],
            "sampled_video_ids": [],
            "source": "youtube_data_api",
            "warnings": []
        }
    
    # 환경변수 읽기
    search_enabled = os.getenv("YOUTUBE_SEARCH_ENABLED", "0") == "1"
    quota_budget = int(os.getenv("YOUTUBE_QUOTA_BUDGET_UNITS", "10000"))
    search_seeds_max = int(os.getenv("YOUTUBE_SEARCH_SEEDS_MAX", "0"))
    cache_ttl = int(os.getenv("YOUTUBE_API_CACHE_TTL_SECONDS", "86400"))
    
    video_ids_set = set()
    errors = []
    warnings = []
    counts = {
        "mostPopular": 0,
        "viewCount": 0,
        "relevance": 0,
        "union_count": 0,
        "api_calls_videos_mostPopular": 0,
        "api_calls_search_viewCount": 0,
        "cache_hits": 0,
        "cache_misses": 0,
        "quota_units_estimated_used": 0,
        "search_skipped_due_to_budget_count": 0
    }
    
    quota_used = 0
    
    # (1) mostPopular (chart=mostPopular) - 항상 실행
    for region in region_codes:
        if len(video_ids_set) >= max_videos:
            break
        
        params = {
            "part": "id",
            "chart": "mostPopular",
            "regionCode": region,
            "maxResults": min(50, max_videos),
            "key": api_key
        }
        
        response_data, cache_hit, error_msg = _make_api_request(
            cycle_id, "videos", params, VIDEOS_CALL_COST_UNITS, cache_ttl
        )
        
        if cache_hit:
            counts["cache_hits"] += 1
        else:
            counts["cache_misses"] += 1
            quota_used += VIDEOS_CALL_COST_UNITS
        
        if response_data:
            items = response_data.get("items", [])
            for item in items:
                video_id = item.get("id", "")
                if video_id:
                    video_ids_set.add(video_id)
            counts["mostPopular"] += len(items)
            counts["api_calls_videos_mostPopular"] += 1
        else:
            errors.append({
                "source": f"mostPopular_{region}",
                "http_status": None,
                "message": error_msg or "unknown_error"
            })
    
    # (2) search.list (order=viewCount) - 환경변수 및 예산 기반
    if search_enabled:
        seed_keywords = categories[:search_seeds_max] if search_seeds_max > 0 else categories[:5]
        
        for seed in seed_keywords:
            if len(video_ids_set) >= max_videos:
                break
            
            # 예산 확인
            if quota_used + SEARCH_CALL_COST_UNITS > quota_budget:
                counts["search_skipped_due_to_budget_count"] += 1
                warnings.append({
                    "source": "search_viewCount",
                    "seed": seed,
                    "message": f"Budget exceeded: quota_used={quota_used}, budget={quota_budget}, cost={SEARCH_CALL_COST_UNITS}"
                })
                continue
            
            params = {
                "part": "snippet",
                "q": seed,
                "type": "video",
                "order": "viewCount",
                "maxResults": min(50, max_videos - len(video_ids_set)),
                "key": api_key
            }
            
            response_data, cache_hit, error_msg = _make_api_request(
                cycle_id, "search", params, SEARCH_CALL_COST_UNITS, cache_ttl
            )
            
            if cache_hit:
                counts["cache_hits"] += 1
            else:
                counts["cache_misses"] += 1
                quota_used += SEARCH_CALL_COST_UNITS
            
            if response_data:
                items = response_data.get("items", [])
                for item in items:
                    video_id = item.get("id", {}).get("videoId", "")
                    if video_id:
                        video_ids_set.add(video_id)
                counts["viewCount"] += len(items)
                counts["api_calls_search_viewCount"] += 1
            else:
                errors.append({
                    "source": f"search_viewCount_{seed}",
                    "http_status": None,
                    "message": error_msg or "unknown_error"
                })
    
    # (3) search.list (order=relevance) - 환경변수 및 예산 기반
    if search_enabled:
        seed_keywords = categories[:search_seeds_max] if search_seeds_max > 0 else categories[:5]
        
        for seed in seed_keywords:
            if len(video_ids_set) >= max_videos:
                break
            
            # 예산 확인
            if quota_used + SEARCH_CALL_COST_UNITS > quota_budget:
                counts["search_skipped_due_to_budget_count"] += 1
                warnings.append({
                    "source": "search_relevance",
                    "seed": seed,
                    "message": f"Budget exceeded: quota_used={quota_used}, budget={quota_budget}, cost={SEARCH_CALL_COST_UNITS}"
                })
                continue
            
            params = {
                "part": "snippet",
                "q": seed,
                "type": "video",
                "order": "relevance",
                "maxResults": min(50, max_videos - len(video_ids_set)),
                "key": api_key
            }
            
            response_data, cache_hit, error_msg = _make_api_request(
                cycle_id, "search", params, SEARCH_CALL_COST_UNITS, cache_ttl
            )
            
            if cache_hit:
                counts["cache_hits"] += 1
            else:
                counts["cache_misses"] += 1
                quota_used += SEARCH_CALL_COST_UNITS
            
            if response_data:
                items = response_data.get("items", [])
                for item in items:
                    video_id = item.get("id", {}).get("videoId", "")
                    if video_id:
                        video_ids_set.add(video_id)
                counts["relevance"] += len(items)
            else:
                errors.append({
                    "source": f"search_relevance_{seed}",
                    "http_status": None,
                    "message": error_msg or "unknown_error"
                })
    
    video_ids_list = list(video_ids_set)[:max_videos]
    counts["union_count"] = len(video_ids_list)
    counts["quota_units_estimated_used"] = quota_used
    
    return video_ids_list, {
        "ok": len(video_ids_list) >= 1,
        "api_key_configured": True,
        "region_codes": region_codes,
        "max_videos": max_videos,
        "counts": counts,
        "errors": errors,
        "warnings": warnings,
        "sampled_video_ids": video_ids_list[:200],
        "source": "youtube_data_api"
    }
