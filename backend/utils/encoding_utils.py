"""
인코딩 유틸리티 - 한글 깨짐 방지 및 복구

기능:
- 입력 문자열 인코딩 검증
- 모지박 감지 및 복구
- UTF-8 강제 변환
- 한글 포함 여부 검증
"""

import re
import sys
import os
from typing import Tuple, Optional, Dict, Any
from pathlib import Path


# 한글 유니코드 범위
KOREAN_PATTERN = re.compile(r'[가-힣]')
MOJIBOX_PATTERNS = [
    re.compile(r'[\uFFFD]'),  # 모지박 문자 (U+FFFD)
    re.compile(r'\?[가-힣]'),  # ?덈 같은 패턴
    re.compile(r'[^\x00-\x7F가-힣\s\.,!?;:()\[\]{}\'"-]+'),  # 비정상 문자
]


def detect_mojibox(text: str) -> Tuple[bool, Optional[str]]:
    """
    모지박 문자 감지
    
    Args:
        text: 검사할 텍스트
    
    Returns:
        Tuple[bool, Optional[str]]: (모지박 발견 여부, 발견된 패턴)
    """
    if not text:
        return False, None
    
    for pattern in MOJIBOX_PATTERNS:
        if pattern.search(text):
            return True, pattern.pattern
    
    return False, None


def has_korean(text: str) -> bool:
    """
    한글 포함 여부 검사
    
    Args:
        text: 검사할 텍스트
    
    Returns:
        bool: 한글이 포함되어 있으면 True
    """
    if not text:
        return False
    return bool(KOREAN_PATTERN.search(text))


def count_korean_chars(text: str) -> int:
    """
    한글 문자 개수 세기
    
    Args:
        text: 검사할 텍스트
    
    Returns:
        int: 한글 문자 개수
    """
    if not text:
        return 0
    return len(KOREAN_PATTERN.findall(text))


def fix_encoding(text: str, source_encoding: str = "cp949") -> Tuple[str, bool]:
    """
    인코딩 복구 시도
    
    Args:
        text: 복구할 텍스트
        source_encoding: 원본 인코딩 추정값 (기본: cp949)
    
    Returns:
        Tuple[str, bool]: (복구된 텍스트, 성공 여부)
    """
    if not text:
        return text, True
    
    # 이미 정상인 경우
    if not detect_mojibox(text)[0]:
        return text, True
    
    try:
        # 모지박이 있는 경우 복구 시도
        # 1. cp949로 인코딩 후 utf-8로 디코딩
        fixed = text.encode(source_encoding, errors="ignore").decode("utf-8", errors="ignore")
        
        # 복구 후 모지박이 없어졌는지 확인
        if not detect_mojibox(fixed)[0]:
            return fixed, True
        
        # 2. utf-8로 인코딩 후 cp949로 디코딩 (역방향)
        try:
            fixed2 = text.encode("utf-8", errors="ignore").decode(source_encoding, errors="ignore")
            if not detect_mojibox(fixed2)[0]:
                return fixed2, True
        except:
            pass
        
        return text, False
    except Exception:
        return text, False


def ensure_utf8_string(text: str, log_context: str = "") -> Tuple[str, Dict[str, Any]]:
    """
    문자열을 UTF-8로 보장 (검증 및 복구)
    
    Args:
        text: 처리할 텍스트
        log_context: 로그 컨텍스트 (디버깅용)
    
    Returns:
        Tuple[str, Dict[str, Any]]: (처리된 텍스트, 진단 정보)
    """
    diagnostic = {
        "original_length": len(text) if text else 0,
        "has_korean": False,
        "has_mojibox": False,
        "fixed": False,
        "encoding_fallback_used": None,
        "korean_count": 0
    }
    
    if not text:
        return text, diagnostic
    
    # 한글 포함 여부
    diagnostic["has_korean"] = has_korean(text)
    diagnostic["korean_count"] = count_korean_chars(text)
    
    # 모지박 감지
    has_mojibox, pattern = detect_mojibox(text)
    diagnostic["has_mojibox"] = has_mojibox
    
    if has_mojibox:
        # 복구 시도
        fixed_text, success = fix_encoding(text)
        diagnostic["fixed"] = success
        if success:
            diagnostic["encoding_fallback_used"] = "cp949"
            return fixed_text, diagnostic
        else:
            # 복구 실패 - 원본 반환 (에러는 호출부에서 처리)
            return text, diagnostic
    
    # 정상 문자열
    return text, diagnostic


def validate_before_save(text: str, field_name: str = "text") -> Tuple[bool, Optional[str]]:
    """
    저장 전 한글 검증
    
    Args:
        text: 검증할 텍스트
        field_name: 필드 이름 (에러 메시지용)
    
    Returns:
        Tuple[bool, Optional[str]]: (검증 통과 여부, 에러 메시지)
    """
    if not text:
        return True, None
    
    # 모지박 감지
    has_mojibox, pattern = detect_mojibox(text)
    if has_mojibox:
        return False, f"{field_name}에 모지박 문자가 발견되었습니다 (패턴: {pattern})"
    
    # UTF-8 인코딩 가능 여부 확인
    try:
        text.encode("utf-8")
    except UnicodeEncodeError as e:
        return False, f"{field_name}를 UTF-8로 인코딩할 수 없습니다: {str(e)}"
    
    return True, None


def log_encoding_step(
    step_name: str,
    text: str,
    log_file: Optional[Path] = None
) -> None:
    """
    인코딩 추적 로그 기록
    
    Args:
        step_name: 단계 이름
        text: 텍스트
        log_file: 로그 파일 경로
    """
    if not log_file:
        return
    
    try:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        
        # 텍스트 샘플 (처음 50자)
        sample = repr(text[:50]) if text else "None"
        
        # 진단 정보
        has_kor = has_korean(text)
        has_mojibox, pattern = detect_mojibox(text)
        korean_count = count_korean_chars(text)
        
        # ASCII 여부
        is_ascii = all(ord(c) < 128 for c in text) if text else True
        
        log_entry = f"[{step_name}]\n"
        log_entry += f"  sample: {sample}\n"
        log_entry += f"  length: {len(text) if text else 0}\n"
        log_entry += f"  has_korean: {has_kor}\n"
        log_entry += f"  korean_count: {korean_count}\n"
        log_entry += f"  has_mojibox: {has_mojibox}\n"
        log_entry += f"  is_ascii: {is_ascii}\n"
        if has_mojibox:
            log_entry += f"  mojibox_pattern: {pattern}\n"
        log_entry += "\n"
        
        with open(log_file, "a", encoding="utf-8", newline="\n") as f:
            f.write(log_entry)
    except Exception as e:
        # 로그 기록 실패해도 무시
        pass


def get_encoding_info() -> Dict[str, Any]:
    """
    시스템 인코딩 정보 수집
    
    Returns:
        Dict: 인코딩 정보
    """
    return {
        "python_version": sys.version,
        "default_encoding": sys.getdefaultencoding(),
        "filesystem_encoding": sys.getfilesystemencoding(),
        "stdout_encoding": sys.stdout.encoding if hasattr(sys.stdout, 'encoding') else None,
        "stderr_encoding": sys.stderr.encoding if hasattr(sys.stderr, 'encoding') else None,
        "preferred_encoding": "utf-8",
        "PYTHONUTF8": os.environ.get("PYTHONUTF8", "not set")
    }

