"""
Import Sanity Check - backend.* import 규칙 강제 검증

정답 실행 명령:
    python -m backend.scripts.import_sanity

기능:
- backend/ 하위 모든 *.py 파일 스캔
- 금지 패턴 발견 시 즉시 FAIL (종료코드 1)
- 예외 없음 (로컬 모듈은 반드시 backend.*로만)
"""

import sys
from pathlib import Path
from typing import List, Tuple


# 금지 패턴 리스트 (정규식 아님, 단순 문자열 포함 검사)
FORBIDDEN_PATTERNS = [
    'from db.',
    'from utils.',
    'from ai_engine.',
    'from checkprompts.',
    'from core.',
    'from jobs.',
    'from tools.',
    'from scripts.',
    'from schemas.',
    'from configs.',
    'from crawler.',
    'from memory.',
    'from video.',
    'import db',
    'import utils',
    'import ai_engine',
    'import checkprompts',
    'import core',
    'import jobs',
    'import tools',
    'import scripts',
    'import schemas',
    'import configs',
    'import crawler',
    'import memory',
    'import video',
]


def scan_file(file_path: Path) -> List[Tuple[int, str]]:
    """
    파일 스캔하여 금지 패턴 발견 위치 반환
    
    Args:
        file_path: 스캔할 파일 경로
    
    Returns:
        List[Tuple[int, str]]: (라인 번호, 발견된 패턴) 리스트
    """
    violations = []
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, start=1):
                # 주석/문자열 내부는 제외하지 않음 (엄격하게 체크)
                for pattern in FORBIDDEN_PATTERNS:
                    if pattern in line:
                        violations.append((line_num, pattern))
    except Exception as e:
        # 파일 읽기 실패는 무시 (인코딩 오류 등)
        pass
    
    return violations


def should_exclude_file(file_path: Path, backend_dir: Path) -> bool:
    """
    파일이 스캔 제외 대상인지 확인
    
    Args:
        file_path: 확인할 파일 경로
        backend_dir: backend 디렉토리 경로
    
    Returns:
        bool: 제외 대상이면 True
    """
    file_str = str(file_path)
    
    # __pycache__ 제외
    if '__pycache__' in file_str:
        return True
    
    # .venv 제외
    if '.venv' in file_str:
        return True
    
    # site-packages 제외
    if 'site-packages' in file_str:
        return True
    
    # import_sanity.py 자기 자신 제외
    if file_path.name == 'import_sanity.py':
        return True
    
    return False


def main():
    """메인 실행 함수"""
    backend_dir = Path(__file__).resolve().parent.parent
    all_violations = []
    
    # backend/ 하위 모든 .py 파일 스캔
    for py_file in backend_dir.rglob('*.py'):
        # 제외 대상 확인
        if should_exclude_file(py_file, backend_dir):
            continue
        
        violations = scan_file(py_file)
        if violations:
            # backend/ 기준 상대 경로로 변환
            rel_path = py_file.relative_to(backend_dir.parent)
            for line_num, pattern in violations:
                all_violations.append((str(rel_path), line_num, pattern))
    
    # 결과 출력
    if all_violations:
        print("=" * 60)
        print("❌ IMPORT SANITY CHECK FAILED")
        print("=" * 60)
        print(f"\n총 {len(all_violations)}개 위반 발견:\n")
        
        for file_path, line_num, pattern in all_violations:
            print(f"  {file_path}:{line_num} - 금지 패턴: '{pattern}'")
        
        print("\n" + "=" * 60)
        print("해결 방법:")
        print("  모든 로컬 import를 'backend.*' 형식으로 변경하세요.")
        print("  예: 'from db.database import X' -> 'from backend.db.database import X'")
        print("=" * 60)
        sys.exit(1)
    else:
        print("=" * 60)
        print("✅ IMPORT SANITY CHECK PASSED")
        print("=" * 60)
        print("\n모든 import가 backend.* 규칙을 준수합니다.")
        sys.exit(0)


if __name__ == "__main__":
    main()

