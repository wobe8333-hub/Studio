"""
JSON Sanitize - JSON-safe 문자열 정규화

기능:
- manifest에 저장되는 모든 문자열을 JSON-safe하게 정규화
- Windows 경로를 POSIX 경로로 변환
- 제어문자 제거/치환
"""

import re
from pathlib import Path
from typing import Any, Dict, List, Union


def normalize_path_str(s: str) -> str:
    """
    Windows 경로를 POSIX 경로로 정규화
    
    Args:
        s: 입력 문자열
    
    Returns:
        str: 정규화된 경로 문자열
    """
    if not isinstance(s, str):
        return s
    
    # Windows 경로 패턴 감지
    # 드라이브 문자 포함 (C:\Users\...) 또는 백슬래시 포함
    if ':\\' in s or '\\' in s:
        # 모든 백슬래시를 슬래시로 변환
        s = s.replace('\\', '/')
        # 연속된 슬래시를 하나로
        s = re.sub(r'/+', '/', s)
    
    return s


def strip_control_chars(s: str) -> str:
    """
    문자열에서 제어문자 제거 또는 안전 치환
    
    Args:
        s: 입력 문자열
    
    Returns:
        str: 제어문자가 제거/치환된 문자열
    """
    if not isinstance(s, str):
        return s
    
    # \r, \n, \t는 공백 하나로 치환
    s = s.replace('\r', ' ')
    s = s.replace('\n', ' ')
    s = s.replace('\t', ' ')
    
    # 나머지 제어문자(0x00~0x1F) 제거
    # 단, 이미 치환한 \r(0x0D), \n(0x0A), \t(0x09)는 제외
    result = []
    for char in s:
        code = ord(char)
        if code < 0x20 and code not in [0x09, 0x0A, 0x0D]:  # \t, \n, \r 제외
            continue  # 제거
        result.append(char)
    
    return ''.join(result)


def sanitize_string(s: str) -> str:
    """
    문자열을 JSON-safe하게 정규화
    
    Args:
        s: 입력 문자열
    
    Returns:
        str: 정규화된 문자열
    """
    if not isinstance(s, str):
        return s
    
    # 1) 제어문자 제거/치환
    s = strip_control_chars(s)
    
    # 2) 경로로 보이는 경우 정규화
    # 경로 판정 휴리스틱
    is_path = (
        ':\\' in s or
        '\\Users\\' in s or
        '\\output\\' in s or
        '\\backend\\' in s or
        '\\runs\\' in s or
        '\\renders\\' in s or
        '\\verify\\' in s or
        s.startswith('C:/') or
        s.startswith('D:/') or
        s.startswith('E:/') or
        ('/output/' in s and ('/runs/' in s or '/verify/' in s))
    )
    
    if is_path:
        s = normalize_path_str(s)
    
    return s


def sanitize_json_obj(obj: Any) -> Any:
    """
    JSON 객체를 재귀적으로 정규화
    
    Args:
        obj: 정규화할 객체 (dict, list, tuple, str, Path 등)
    
    Returns:
        Any: 정규화된 객체
    """
    if isinstance(obj, Path):
        # Path 객체는 POSIX 경로로 변환 후 sanitize
        return sanitize_string(obj.resolve().as_posix())
    elif isinstance(obj, str):
        return sanitize_string(obj)
    elif isinstance(obj, dict):
        return {k: sanitize_json_obj(v) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return [sanitize_json_obj(item) for item in obj]
    elif isinstance(obj, (int, float, bool, type(None))):
        return obj
    else:
        # 기타 타입은 문자열로 변환 후 sanitize
        return sanitize_string(str(obj))

