"""
Manual Seed Loader - 수동 seed 키워드/채널 로더
"""

import os
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple


def load_manual_keywords(keywords_file: Optional[str] = None) -> Tuple[List[str], Optional[str]]:
    """
    수동 seed 키워드 파일 로드
    
    Args:
        keywords_file: 키워드 파일 경로 (기본값: backend/config/kr_manual_seed_keywords.txt)
    
    Returns:
        (keywords: List[str], error: Optional[str])
    """
    if not keywords_file:
        # 프로젝트 루트 기준 경로 계산
        project_root = Path(__file__).resolve().parents[3]
        keywords_file = str(project_root / "backend" / "config" / "kr_manual_seed_keywords.txt")
    
    keywords_file_path = Path(keywords_file)
    
    if not keywords_file_path.exists():
        return [], f"file_not_found: {keywords_file}"
    
    try:
        keywords = []
        with open(keywords_file_path, "r", encoding="utf-8") as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                # 빈 줄 또는 주석(#으로 시작) 무시
                if not line or line.startswith("#"):
                    continue
                keywords.append(line)
        
        return keywords, None
    except Exception as e:
        return [], f"read_error: {type(e).__name__}: {str(e)}"


def load_manual_channels(channels_file: Optional[str] = None) -> Tuple[List[str], Optional[str]]:
    """
    수동 seed 채널 URL 파일 로드
    
    Args:
        channels_file: 채널 파일 경로 (기본값: backend/config/kr_manual_seed_channels.txt)
    
    Returns:
        (channels: List[str], error: Optional[str])
    """
    if not channels_file:
        # 프로젝트 루트 기준 경로 계산
        project_root = Path(__file__).resolve().parents[3]
        channels_file = str(project_root / "backend" / "config" / "kr_manual_seed_channels.txt")
    
    channels_file_path = Path(channels_file)
    
    # 파일이 없으면 빈 리스트 반환 (선택적 파일)
    if not channels_file_path.exists():
        return [], None
    
    try:
        channels = []
        with open(channels_file_path, "r", encoding="utf-8") as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                # 빈 줄 또는 주석(#으로 시작) 무시
                if not line or line.startswith("#"):
                    continue
                # URL 형태 검증 (간단히 http 포함 확인)
                if "http" in line.lower():
                    channels.append(line)
        
        return channels, None
    except Exception as e:
        return [], f"read_error: {type(e).__name__}: {str(e)}"

