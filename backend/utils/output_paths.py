"""
출력 경로 유틸리티 - run_id 기반 경로 생성 통합

기능:
- run_id 기반 output 경로 생성
- 디렉토리 자동 생성 보장
- 파일 경로 규칙 통일
"""

from pathlib import Path
from typing import Dict, Optional


def get_output_dirs(base_dir: Optional[Path] = None) -> Dict[str, Path]:
    """
    output 디렉토리 구조 생성 및 반환
    
    Args:
        base_dir: 기본 디렉토리 (None이면 backend 디렉토리 기준)
    
    Returns:
        Dict[str, Path]: 디렉토리 경로 딕셔너리
            - root: output 루트
            - verify: output/verify
            - plans: output/plans
            - reports: output/reports
            - logs: output/logs
            - cache: output/cache
    """
    if base_dir is None:
        # backend 디렉토리 기준
        backend_dir = Path(__file__).resolve().parent.parent
        output_root = backend_dir / "output"
    else:
        output_root = base_dir / "output"
    
    dirs = {
        "root": output_root,
        "verify": output_root / "verify",
        "plans": output_root / "plans",
        "reports": output_root / "reports",
        "logs": output_root / "logs",
        "cache": output_root / "cache"
    }
    
    # 모든 디렉토리 생성 보장
    for dir_path in dirs.values():
        dir_path.mkdir(parents=True, exist_ok=True)
    
    return dirs


def get_step2_file_paths(run_id: str, base_dir: Optional[Path] = None) -> Dict[str, Path]:
    """
    Step2 산출물 파일 경로 생성
    
    Args:
        run_id: 실행 ID
        base_dir: 기본 디렉토리
    
    Returns:
        Dict[str, Path]: 파일 경로 딕셔너리
            - script_txt: output/verify/{run_id}_script.txt
            - sentences_txt: output/verify/{run_id}_sentences.txt
            - scenes_json: output/plans/{run_id}_scenes.json
            - report_json: output/reports/{run_id}_step2_report.json
    """
    dirs = get_output_dirs(base_dir)
    
    return {
        "script_txt": dirs["verify"] / f"{run_id}_script.txt",
        "sentences_txt": dirs["verify"] / f"{run_id}_sentences.txt",
        "scenes_json": dirs["plans"] / f"{run_id}_scenes.json",
        "report_json": dirs["reports"] / f"{run_id}_step2_report.json"
    }


def get_step3_file_paths(run_id: str, base_dir: Optional[Path] = None) -> Dict[str, Path]:
    """
    Step3 산출물 파일 경로 생성
    
    Args:
        run_id: 실행 ID
        base_dir: 기본 디렉토리
    
    Returns:
        Dict[str, Path]: 파일 경로 딕셔너리
            - scenes_fixed_json: output/plans/{run_id}_scenes_fixed.json
            - report_json: output/reports/{run_id}_step3_report.json
    """
    dirs = get_output_dirs(base_dir)
    
    return {
        "scenes_fixed_json": dirs["plans"] / f"{run_id}_scenes_fixed.json",
        "report_json": dirs["reports"] / f"{run_id}_step3_report.json"
    }


def get_encoding_log_path(run_id: str, base_dir: Optional[Path] = None) -> Path:
    """
    인코딩 추적 로그 파일 경로 생성
    
    Args:
        run_id: 실행 ID
        base_dir: 기본 디렉토리
    
    Returns:
        Path: 로그 파일 경로 (output/logs/{run_id}_encoding_step2.log)
    """
    dirs = get_output_dirs(base_dir)
    return dirs["logs"] / f"{run_id}_encoding_step2.log"


def get_run_step2_file_paths(run_id: str, base_dir: Optional[Path] = None) -> Dict[str, Path]:
    """
    Run 구조 내 Step2 산출물 파일 경로 생성
    
    Args:
        run_id: 실행 ID
        base_dir: 기본 디렉토리
    
    Returns:
        Dict[str, Path]: 파일 경로 딕셔너리 (runs/{run_id}/ 하위)
    """
    from backend.utils.run_manager import get_run_subdirs
    
    dirs = get_run_subdirs(run_id, base_dir)
    
    step2_dir = dirs["step2"]
    
    return {
        "script_txt": step2_dir / "script.txt",
        "sentences_txt": step2_dir / "sentences.txt",
        "scenes_json": step2_dir / "scenes.json",
        "report_json": step2_dir / "step2_report.json"
    }


def get_run_step3_file_paths(run_id: str, base_dir: Optional[Path] = None) -> Dict[str, Path]:
    """
    Run 구조 내 Step3 산출물 파일 경로 생성
    
    Args:
        run_id: 실행 ID
        base_dir: 기본 디렉토리
    
    Returns:
        Dict[str, Path]: 파일 경로 딕셔너리 (runs/{run_id}/ 하위)
    """
    from backend.utils.run_manager import get_run_subdirs
    
    dirs = get_run_subdirs(run_id, base_dir)
    
    step3_dir = dirs["step3"]
    
    return {
        "scenes_fixed_json": step3_dir / "scenes_fixed.json",
        "report_json": step3_dir / "step3_report.json"
    }

