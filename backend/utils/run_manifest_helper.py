"""
Run Manifest Helper - runs 구조 파일 복사 및 manifest 업데이트

기능:
- Step2/Step3 파일을 runs 구조로 복사
- manifest.json 업데이트
"""

import json
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime

from backend.utils.run_manager import (
    get_run_dir,
    get_run_subdirs,
    load_run_manifest,
    _atomic_write_json,
)


def copy_step2_files_to_runs(
    run_id: str,
    legacy_files: Dict[str, Path],
    base_dir: Optional[Path] = None
) -> Dict[str, bool]:
    """
    Step2 파일을 runs 구조로 복사
    
    Args:
        run_id: 실행 ID
        legacy_files: 기존 위치 파일 경로 딕셔너리
            - script_txt: output/verify/{run_id}_script.txt
            - sentences_txt: output/verify/{run_id}_sentences.txt
            - scenes_json: output/plans/{run_id}_scenes.json
            - report_json: output/reports/{run_id}_step2_report.json
        base_dir: 기본 디렉토리
    
    Returns:
        Dict[str, bool]: 복사 성공 여부
            - script.txt: True/False
            - sentences.txt: True/False
            - step2_report.json: True/False
    """
    dirs = get_run_subdirs(run_id, base_dir)
    step2_dir = dirs["step2"]
    
    result = {
        "script.txt": False,
        "sentences.txt": False,
        "step2_report.json": False
    }
    
    # script.txt 복사
    if "script_txt" in legacy_files and legacy_files["script_txt"].exists():
        try:
            dest = step2_dir / "script.txt"
            shutil.copy2(legacy_files["script_txt"], dest)
            result["script.txt"] = True
        except Exception as e:
            print(f"[RUN_MANIFEST] Step2 script.txt 복사 실패: {e}")
    
    # sentences.txt 복사
    if "sentences_txt" in legacy_files and legacy_files["sentences_txt"].exists():
        try:
            dest = step2_dir / "sentences.txt"
            shutil.copy2(legacy_files["sentences_txt"], dest)
            result["sentences.txt"] = True
        except Exception as e:
            print(f"[RUN_MANIFEST] Step2 sentences.txt 복사 실패: {e}")
    
    # step2_report.json 복사
    if "report_json" in legacy_files and legacy_files["report_json"].exists():
        try:
            dest = step2_dir / "step2_report.json"
            shutil.copy2(legacy_files["report_json"], dest)
            result["step2_report.json"] = True
        except Exception as e:
            print(f"[RUN_MANIFEST] Step2 step2_report.json 복사 실패: {e}")
    
    return result


def copy_step3_files_to_runs(
    run_id: str,
    legacy_files: Dict[str, Path],
    base_dir: Optional[Path] = None
) -> Dict[str, bool]:
    """
    Step3 파일을 runs 구조로 복사
    
    Args:
        run_id: 실행 ID
        legacy_files: 기존 위치 파일 경로 딕셔너리
            - scenes_fixed_json: output/plans/{run_id}_scenes_fixed.json
            - report_json: output/reports/{run_id}_step3_report.json
        base_dir: 기본 디렉토리
    
    Returns:
        Dict[str, bool]: 복사 성공 여부
            - scenes_fixed.json: True/False
            - step3_report.json: True/False
    """
    dirs = get_run_subdirs(run_id, base_dir)
    step3_dir = dirs["step3"]
    
    result = {
        "scenes_fixed.json": False,
        "step3_report.json": False
    }
    
    # scenes_fixed.json 복사
    if "scenes_fixed_json" in legacy_files and legacy_files["scenes_fixed_json"].exists():
        try:
            dest = step3_dir / "scenes_fixed.json"
            shutil.copy2(legacy_files["scenes_fixed_json"], dest)
            result["scenes_fixed.json"] = True
        except Exception as e:
            print(f"[RUN_MANIFEST] Step3 scenes_fixed.json 복사 실패: {e}")
    
    # step3_report.json 복사
    if "report_json" in legacy_files and legacy_files["report_json"].exists():
        try:
            dest = step3_dir / "step3_report.json"
            shutil.copy2(legacy_files["report_json"], dest)
            result["step3_report.json"] = True
        except Exception as e:
            print(f"[RUN_MANIFEST] Step3 step3_report.json 복사 실패: {e}")
    
    return result


def update_manifest_step2(
    run_id: str,
    status: str,
    files: Dict[str, bool],
    errors: List[str] = None,
    warnings: List[str] = None,
    base_dir: Optional[Path] = None
) -> Dict[str, Any]:
    """
    Manifest의 Step2 정보 업데이트
    
    Args:
        run_id: 실행 ID
        status: 상태 ("success" | "failed" | "pending")
        files: 파일 존재 여부
        errors: 에러 목록
        warnings: 경고 목록
        base_dir: 기본 디렉토리
    
    Returns:
        Dict: 업데이트된 Manifest
    """
    manifest = load_run_manifest(run_id, base_dir)
    if manifest is None:
        raise ValueError(f"Run manifest not found: {run_id}")
    
    # step2 블록 보정
    steps = manifest.setdefault("steps", {})
    if "step2" not in steps:
        steps["step2"] = {"status": "pending", "artifacts": [], "errors": [], "warnings": []}
    
    manifest["last_updated"] = datetime.now().isoformat()
    steps["step2"]["status"] = status
    # artifacts는 POSIX 경로로 저장 (JSON-safe)
    from backend.utils.json_sanitize import sanitize_string
    artifacts = [sanitize_string(name) for name, exists in files.items() if exists]
    steps["step2"]["artifacts"] = artifacts
    steps["step2"]["errors"] = errors or []
    steps["step2"]["warnings"] = warnings or []
    steps["step2"]["files"] = files  # 정보 보존용
    
    if status == "fail":
        manifest["status"] = "failed"
    else:
        manifest["status"] = "running"
    
    # Manifest 저장 (원자적 쓰기)
    run_dir = get_run_dir(run_id, base_dir)
    manifest_path = run_dir / "manifest.json"
    _atomic_write_json(manifest_path, manifest)
    return manifest


def update_manifest_step3(
    run_id: str,
    status: str,
    files: Dict[str, bool],
    errors: List[str] = None,
    warnings: List[str] = None,
    base_dir: Optional[Path] = None
) -> Dict[str, Any]:
    """
    Manifest의 Step3 정보 업데이트
    
    Args:
        run_id: 실행 ID
        status: 상태 ("success" | "failed" | "pending")
        files: 파일 존재 여부
        errors: 에러 목록
        warnings: 경고 목록
        base_dir: 기본 디렉토리
    
    Returns:
        Dict: 업데이트된 Manifest
    """
    manifest = load_run_manifest(run_id, base_dir)
    if manifest is None:
        raise ValueError(f"Run manifest not found: {run_id}")
    
    steps = manifest.setdefault("steps", {})
    if "step3" not in steps:
        steps["step3"] = {"status": "pending", "artifacts": [], "errors": [], "warnings": []}
    
    manifest["last_updated"] = datetime.now().isoformat()
    steps["step3"]["status"] = status
    # artifacts는 POSIX 경로로 저장 (JSON-safe)
    from backend.utils.json_sanitize import sanitize_string
    artifacts = [sanitize_string(name) for name, exists in files.items() if exists]
    steps["step3"]["artifacts"] = artifacts
    steps["step3"]["errors"] = errors or []
    steps["step3"]["warnings"] = warnings or []
    steps["step3"]["files"] = files
    
    if status == "fail":
        manifest["status"] = "failed"
    elif steps.get("step2", {}).get("status") == "success" and steps["step3"]["status"] == "success":
        manifest["status"] = "success"
    else:
        manifest["status"] = "running"
    
    run_dir = get_run_dir(run_id, base_dir)
    manifest_path = run_dir / "manifest.json"
    _atomic_write_json(manifest_path, manifest)
    return manifest

