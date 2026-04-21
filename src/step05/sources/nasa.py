"""
NASA Open API 소스 (Layer 2 — 일간, CH2 과학 전용)
APOD (오늘의 천문사진), NEO (근지구 천체) 데이터 수집
"""

import json
import os
import urllib.parse
import urllib.request
from typing import Any, Dict, List


def _load_api_key() -> str:
    return os.getenv("NASA_API_KEY", "DEMO_KEY").strip()


def _fetch_apod(api_key: str, count: int = 7) -> List[Dict[str, str]]:
    """APOD (Astronomy Picture of the Day) 최근 N일 수집"""
    params = urllib.parse.urlencode({"api_key": api_key, "count": count})
    url = f"https://api.nasa.gov/planetary/apod?{params}"
    try:
        with urllib.request.urlopen(url, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        if isinstance(data, list):
            return [{"title": d.get("title", ""), "explanation": d.get("explanation", "")[:200]} for d in data]
        return []
    except Exception:
        return []


def _fetch_neo_titles(api_key: str) -> List[str]:
    """이번 주 근지구 소행성 이름 수집 (흥미 주제로 활용)"""
    from datetime import date, timedelta
    today = date.today()
    end = today + timedelta(days=7)
    params = urllib.parse.urlencode({
        "start_date": today.isoformat(),
        "end_date": end.isoformat(),
        "api_key": api_key,
    })
    url = f"https://api.nasa.gov/neo/rest/v1/feed?{params}"
    try:
        with urllib.request.urlopen(url, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        neo_objects = []
        for date_key, neos in data.get("near_earth_objects", {}).items():
            for neo in neos[:3]:
                neo_objects.append(neo.get("name", ""))
        return [n for n in neo_objects if n][:10]
    except Exception:
        return []


def fetch_nasa_data(category: str = "science") -> Dict[str, Any]:
    """
    NASA API로 천문/우주 주제 데이터 수집 (과학 채널 전용)

    Returns:
        {
            "topics": List[str],       — APOD 제목 + NEO 이름
            "summaries": List[str],    — APOD 설명
            "source": "nasa",
            "applicable": bool,
            "error": Optional[str]
        }
    """
    if category != "science":
        return {
            "topics": [],
            "summaries": [],
            "source": "nasa",
            "applicable": False,
            "error": f"NASA API는 science 카테고리 전용 (현재: {category})",
        }

    api_key = _load_api_key()
    errors: List[str] = []
    topics: List[str] = []
    summaries: List[str] = []

    try:
        apod_items = _fetch_apod(api_key, count=7)
        for item in apod_items:
            if item["title"]:
                topics.append(f"우주 사진: {item['title']}")
                summaries.append(item["explanation"])
    except Exception as e:
        errors.append(f"APOD: {str(e)[:100]}")

    try:
        neo_names = _fetch_neo_titles(api_key)
        for name in neo_names:
            topics.append(f"근지구 소행성: {name}")
    except Exception as e:
        errors.append(f"NEO: {str(e)[:100]}")

    return {
        "topics": topics[:20],
        "summaries": summaries,
        "source": "nasa",
        "applicable": True,
        "error": "; ".join(errors) if errors else None,
    }
