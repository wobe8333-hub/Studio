"""
Knowledge v1 Path Guard - Path 타입 누수(str leakage) 전면 차단 유틸리티

이 모듈은 Path 타입 누수 문제를 근본적으로 해결하기 위한 전역 방어 함수들을 제공합니다.
모든 경로 관련 작업은 이 모듈의 함수들을 통해 수행하여 str이 Path 메서드를 호출하는 것을 방지합니다.
"""

from pathlib import Path
from typing import Union, Any


def P(x: Any) -> Path:
    """
    Path 강제 캐스팅 전역 방어 함수
    
    Args:
        x: Path, str, 또는 기타 타입
        
    Returns:
        Path: 항상 Path 인스턴스
        
    Raises:
        TypeError: x가 None이거나 변환 불가능한 타입인 경우
    """
    if isinstance(x, Path):
        return x
    if x is None:
        raise TypeError(f"Path cannot be None")
    if isinstance(x, str):
        return Path(x)
    # 기타 타입은 str로 변환 시도
    try:
        return Path(str(x))
    except Exception as e:
        raise TypeError(f"Cannot convert {type(x)} to Path: {e}")


def ensure_parent_dir(path: Union[Path, str]) -> None:
    """
    경로의 부모 디렉토리를 생성 (존재하지 않으면 생성)
    
    Args:
        path: Path 또는 str (Path로 변환됨)
    """
    path = P(path)
    path.parent.mkdir(parents=True, exist_ok=True)


def touch_jsonl(path: Union[Path, str]) -> None:
    """
    JSONL 파일이 없으면 빈 파일로 생성 (부모 디렉토리도 생성)
    
    Args:
        path: Path 또는 str (Path로 변환됨)
    """
    path = P(path)
    ensure_parent_dir(path)
    if not path.exists():
        path.touch()

