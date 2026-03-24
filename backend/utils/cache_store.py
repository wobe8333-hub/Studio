"""
글로벌 캐시 저장소 유틸리티 (Step7)

기능:
- scene 캐시 키 생성 (sha256)
- scene 캐시 저장/조회
- 캐시 메타데이터 관리
"""

import json
import hashlib
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Any

from backend.utils.run_manager import get_project_root


def get_cache_root(base_dir: Optional[Path] = None) -> Path:
    """
    글로벌 캐시 루트 경로 반환
    
    Args:
        base_dir: 기본 디렉토리 (None이면 프로젝트 루트 기준)
    
    Returns:
        Path: backend/output/cache 경로
    """
    if base_dir is None:
        project_root = get_project_root()
        cache_root = project_root / "backend" / "output" / "cache"
    else:
        if base_dir.name == "backend":
            output_root = base_dir / "output"
        else:
            output_root = base_dir / "output" if (base_dir / "output").exists() else base_dir
        cache_root = output_root / "cache"
    
    return cache_root


def compute_scene_cache_key(scene: Dict[str, Any]) -> str:
    """
    scene 객체에서 캐시 키 생성
    
    Args:
        scene: scene 객체 (scenes_fixed.json의 scene)
    
    Returns:
        str: sha256 hex 문자열 (cache_key)
    """
    # scene_index 제외하고 정규화
    scene_normalized = {k: v for k, v in scene.items() if k != "scene_index"}
    
    # JSON 정규화 (sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    json_str = json.dumps(scene_normalized, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    
    # sha256 해시
    hash_obj = hashlib.sha256(json_str.encode("utf-8"))
    cache_key = hash_obj.hexdigest()
    
    return cache_key


def get_cached_scene_path(cache_key: str, base_dir: Optional[Path] = None) -> Path:
    """
    캐시된 scene mp4 경로 반환
    
    Args:
        cache_key: scene 캐시 키
        base_dir: 기본 디렉토리
    
    Returns:
        Path: cache/scenes/<cache_key>/scene.mp4 경로
    """
    cache_root = get_cache_root(base_dir)
    scene_cache_dir = cache_root / "scenes" / cache_key
    return scene_cache_dir / "scene.mp4"


def get_cached_scene_meta_path(cache_key: str, base_dir: Optional[Path] = None) -> Path:
    """
    캐시된 scene 메타데이터 경로 반환
    
    Args:
        cache_key: scene 캐시 키
        base_dir: 기본 디렉토리
    
    Returns:
        Path: cache/scenes/<cache_key>/meta.json 경로
    """
    cache_root = get_cache_root(base_dir)
    scene_cache_dir = cache_root / "scenes" / cache_key
    return scene_cache_dir / "meta.json"


def get_cached_scene_mp4(scene: Dict[str, Any], base_dir: Optional[Path] = None) -> Optional[Path]:
    """
    캐시된 scene mp4 파일 경로 반환 (존재 여부 확인)
    
    Args:
        scene: scene 객체
        base_dir: 기본 디렉토리
    
    Returns:
        Optional[Path]: 캐시된 파일 경로 (없으면 None)
    """
    cache_key = compute_scene_cache_key(scene)
    cached_path = get_cached_scene_path(cache_key, base_dir)
    
    if cached_path.exists() and cached_path.is_file():
        return cached_path
    
    return None


def put_scene(
    scene: Dict[str, Any],
    scene_mp4_path: Path,
    base_dir: Optional[Path] = None
) -> bool:
    """
    scene mp4를 캐시에 저장
    
    Args:
        scene: scene 객체
        scene_mp4_path: 원본 scene mp4 파일 경로
        base_dir: 기본 디렉토리
    
    Returns:
        bool: 성공 여부
    """
    try:
        if not scene_mp4_path.exists():
            return False
        
        cache_key = compute_scene_cache_key(scene)
        cache_root = get_cache_root(base_dir)
        scene_cache_dir = cache_root / "scenes" / cache_key
        scene_cache_dir.mkdir(parents=True, exist_ok=True)
        
        # scene.mp4 복사
        cached_mp4_path = scene_cache_dir / "scene.mp4"
        shutil.copy2(scene_mp4_path, cached_mp4_path)
        
        # meta.json 생성
        meta_path = scene_cache_dir / "meta.json"
        meta_data = {
            "cache_key": cache_key,
            "scene_index": scene.get("scene_index"),
            "scene_type": scene.get("scene_type"),
            "duration_sec": scene.get("duration_sec"),
            "cached_at": None  # datetime은 JSON 직렬화를 위해 문자열로 저장 필요
        }
        
        from datetime import datetime
        meta_data["cached_at"] = datetime.now().isoformat()
        
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(meta_data, f, ensure_ascii=False, indent=2)
        
        return True
    
    except Exception as e:
        print(f"[CACHE] 저장 실패: {e}")
        return False

