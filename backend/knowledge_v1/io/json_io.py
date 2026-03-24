"""
JSON IO SSOT 유틸 - UTF-8 강제 저장/로드
한글 인코딩 깨짐 방지를 위한 단일 진입점
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def dump_json(path: Path, obj: Any) -> None:
    """
    JSON 파일 저장 (UTF-8 강제, ensure_ascii=False)
    
    Args:
        path: 저장 경로
        obj: 저장할 객체
        
    Raises:
        OSError: 파일 쓰기 실패
        TypeError: JSON 직렬화 불가능한 객체
    """
    # 부모 디렉터리 자동 생성
    path.parent.mkdir(parents=True, exist_ok=True)
    
    # UTF-8 강제 저장 (ensure_ascii=False로 한글 escape 금지)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2, sort_keys=False)


def load_json(path: Path) -> Any:
    """
    JSON 파일 로드 (UTF-8 강제)
    
    Args:
        path: 로드할 파일 경로
        
    Returns:
        Any: 파싱된 JSON 객체
        
    Raises:
        FileNotFoundError: 파일이 존재하지 않음
        json.JSONDecodeError: JSON 파싱 실패
        UnicodeDecodeError: UTF-8 디코딩 실패
    """
    # UTF-8 강제 로드
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

