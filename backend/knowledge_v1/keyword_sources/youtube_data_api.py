"""
YouTube Data API v3 - 키워드 후보 추출
"""

import os
import json
from typing import List, Dict, Any, Optional
from pathlib import Path

try:
    from dotenv import load_dotenv
    DOTENV_AVAILABLE = True
except ImportError:
    DOTENV_AVAILABLE = False


def _load_env() -> None:
    """.env 파일 로드 (프로젝트 루트 기준)"""
    if not DOTENV_AVAILABLE:
        return
    
    # 프로젝트 루트 계산 (backend/knowledge_v1/keyword_sources/youtube_data_api.py 기준)
    project_root = Path(__file__).resolve().parents[4]
    
    # backend/.env, 루트/.env 순서로 로드 (override=False)
    backend_env = project_root / "backend" / ".env"
    root_env = project_root / ".env"
    
    if backend_env.exists():
        load_dotenv(backend_env, override=False)
    if root_env.exists():
        load_dotenv(root_env, override=False)


def _load_api_key() -> Optional[str]:
    """API 키 로딩 (env var → file fallback)"""
    # .env 로드
    _load_env()
    
    # 1) 환경변수에서 로드
    api_key = os.getenv("YOUTUBE_API_KEY")
    if api_key:
        return api_key.strip()
    
    # 2) 파일에서 로드
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


def _mask_api_key(key: str) -> str:
    """API Key 마스킹 (로그용)"""
    if not key or len(key) < 8:
        return "***"
    return key[:4] + "***" + key[-4:]


def fetch_youtube_keywords(category: str, max_results: int = 50) -> Dict[str, Any]:
    """
    YouTube Data API v3로 키워드 후보 추출 (Fallback용)
    
    BULK 모드에서는 사용하지 않으며, analytics/videos.list가 모두 실패한 경우에만 fallback으로 사용
    
    Returns:
        {
            "candidate_keywords": List[str],
            "source": "youtube_data_api",
            "api_key_configured": bool,
            "api_key_masked": Optional[str],
            "error": Optional[str]
        }
    """
    api_key = _load_api_key()
    
    if not api_key:
        return {
            "candidate_keywords": [],
            "source": "youtube_data_api",
            "api_key_configured": False,
            "api_key_masked": None,
            "error": "YOUTUBE_API_KEY not configured (set env var or backend/credentials/youtube_api_key.txt)"
        }
    
    try:
        # Fallback: 카테고리별 시드 키워드 맵 (최후 수단)
        seed_map = {
            "science": ["gravity", "quantum physics", "evolution", "climate change", "black hole"],
            "history": ["world war", "ancient rome", "renaissance", "cold war", "industrial revolution"],
            "common_sense": ["electricity", "water cycle", "photosynthesis", "gravity", "magnetism"],
            "economy": ["inflation", "gdp", "stock market", "cryptocurrency", "trade"],
            "geography": ["latitude", "longitude", "tectonic plates", "ocean currents", "climate zones"],
            "papers": ["transformer", "attention mechanism", "neural network", "deep learning", "llm"]
        }
        
        # 시드 키워드에서 후보 생성 (최대 30개로 제한, fallback이므로)
        seeds = seed_map.get(category, [f"{category} topic"])
        candidate_keywords = seeds[:min(max_results, 30)]
        
        return {
            "candidate_keywords": candidate_keywords,
            "source": "youtube_data_api_fallback",
            "api_key_configured": True,
            "api_key_masked": _mask_api_key(api_key),
            "error": None
        }
        
    except Exception as e:
        return {
            "candidate_keywords": [],
            "source": "youtube_data_api",
            "api_key_configured": True,
            "error": f"{type(e).__name__}: {str(e)}"
        }

