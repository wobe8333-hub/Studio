"""
YouTube Trending Topics Dataset - 재현성 보강 (Kaggle + 스냅샷 fallback)
"""

import os
import json
from typing import Dict, Any, List, Optional
from pathlib import Path


def load_trending_dataset_snapshot() -> Dict[str, Any]:
    """내장 스냅샷 로드"""
    try:
        snapshot_path = Path(__file__).parent.parent / "fixtures" / "trending_dataset_snapshot.json"
        if snapshot_path.exists():
            with open(snapshot_path, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return {"keywords": []}


def fetch_trending_keywords(category: str) -> Dict[str, Any]:
    """
    Trending Dataset에서 키워드 추출 (Kaggle API 또는 스냅샷)
    
    Returns:
        {
            "evidence_snapshot": List[str],
            "source": "trending_dataset",
            "kaggle_configured": bool,
            "snapshot_used": bool,
            "error": Optional[str]
        }
    """
    kaggle_username = os.getenv("KAGGLE_USERNAME")
    kaggle_key = os.getenv("KAGGLE_KEY")
    
    kaggle_configured = bool(kaggle_username and kaggle_key)
    snapshot_used = False
    
    # Kaggle API 시도 (설정되어 있을 때)
    if kaggle_configured:
        try:
            from kaggle.api.kaggle_api_extended import KaggleApi
            api = KaggleApi()
            api.authenticate()
            
            # 실제 데이터셋 다운로드 로직 (여기서는 시뮬레이션)
            # dataset = "some/youtube-trending-dataset"
            # api.dataset_download_files(dataset, unzip=True)
            
            # 현재는 스냅샷 사용
            snapshot_used = True
            snapshot = load_trending_dataset_snapshot()
            keywords = snapshot.get("keywords", [])
            
            return {
                "evidence_snapshot": keywords,
                "source": "trending_dataset",
                "kaggle_configured": True,
                "snapshot_used": True,
                "error": None
            }
        except Exception as e:
            # Kaggle 실패 시 스냅샷 fallback
            snapshot_used = True
    else:
        snapshot_used = True
    
    # 스냅샷 사용
    snapshot = load_trending_dataset_snapshot()
    keywords = snapshot.get("keywords", [])
    
    return {
        "evidence_snapshot": keywords,
        "source": "trending_dataset",
        "kaggle_configured": kaggle_configured,
        "snapshot_used": True,
        "error": None if snapshot_used else "snapshot_not_found"
    }

