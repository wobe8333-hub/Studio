"""
Knowledge 저장소 유틸리티 (V3)

기능:
- Knowledge item 저장/갱신
- Index 관리 (append-only)
"""

import json
from pathlib import Path
from typing import Dict, Any, Optional

from backend.utils.run_manager import get_project_root


def get_knowledge_root(base_dir: Optional[Path] = None) -> Path:
    """
    Knowledge 저장소 루트 경로 반환
    
    Args:
        base_dir: 기본 디렉토리 (None이면 프로젝트 루트 기준)
    
    Returns:
        Path: backend/output/knowledge 경로
    """
    if base_dir is None:
        project_root = get_project_root()
        knowledge_root = project_root / "backend" / "output" / "knowledge"
    else:
        if base_dir.name == "backend":
            output_root = base_dir / "output"
        else:
            output_root = base_dir / "output" if (base_dir / "output").exists() else base_dir
        knowledge_root = output_root / "knowledge"
    
    return knowledge_root


def ensure_dirs(base_dir: Optional[Path] = None) -> Dict[str, Path]:
    """
    Knowledge 저장소 디렉토리 구조 생성
    
    Args:
        base_dir: 기본 디렉토리
    
    Returns:
        Dict[str, Path]: 디렉토리 경로 딕셔너리
    """
    knowledge_root = get_knowledge_root(base_dir)
    items_dir = knowledge_root / "items"
    search_cache_dir = knowledge_root / "search_cache"
    
    items_dir.mkdir(parents=True, exist_ok=True)
    search_cache_dir.mkdir(parents=True, exist_ok=True)
    
    return {
        "root": knowledge_root,
        "items": items_dir,
        "search_cache": search_cache_dir
    }


def write_item(run_id: str, item_dict: Dict[str, Any], base_dir: Optional[Path] = None) -> Path:
    """
    Knowledge item 저장
    
    Args:
        run_id: 실행 ID
        item_dict: item 데이터
        base_dir: 기본 디렉토리
    
    Returns:
        Path: 저장된 파일 경로
    """
    dirs = ensure_dirs(base_dir)
    item_path = dirs["items"] / f"{run_id}.json"
    
    with open(item_path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(item_dict, f, ensure_ascii=False, indent=2)
    
    return item_path


def append_index(line_dict: Dict[str, Any], base_dir: Optional[Path] = None) -> bool:
    """
    Index에 1줄 append (append-only, 중복 허용)
    
    Args:
        line_dict: index 라인 데이터 (run_id 포함)
        base_dir: 기본 디렉토리
    
    Returns:
        bool: append 성공 여부
    """
    knowledge_root = get_knowledge_root(base_dir)
    index_path = knowledge_root / "index.jsonl"
    
    # append
    index_path.parent.mkdir(parents=True, exist_ok=True)
    with open(index_path, "a", encoding="utf-8", newline="\n") as f:
        json_line = json.dumps(line_dict, ensure_ascii=False, separators=(",", ":"))
        f.write(json_line + "\n")
    
    return True


def read_item(run_id: str, base_dir: Optional[Path] = None) -> Optional[Dict[str, Any]]:
    """
    Knowledge item 읽기
    
    Args:
        run_id: 실행 ID
        base_dir: 기본 디렉토리
    
    Returns:
        Optional[Dict]: item 데이터 (없으면 None)
    """
    dirs = ensure_dirs(base_dir)
    item_path = dirs["items"] / f"{run_id}.json"
    
    if not item_path.exists():
        return None
    
    try:
        with open(item_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def check_index_has_run_id(run_id: str, base_dir: Optional[Path] = None) -> bool:
    """
    Index에 run_id가 존재하는지 확인
    
    Args:
        run_id: 실행 ID
        base_dir: 기본 디렉토리
    
    Returns:
        bool: 존재 여부
    """
    knowledge_root = get_knowledge_root(base_dir)
    index_path = knowledge_root / "index.jsonl"
    
    if not index_path.exists():
        return False
    
    try:
        with open(index_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    try:
                        existing = json.loads(line)
                        if existing.get("run_id") == run_id:
                            return True
                    except (json.JSONDecodeError, KeyError):
                        continue
    except Exception:
        pass
    
    return False

