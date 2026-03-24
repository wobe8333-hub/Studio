"""
실패 요약 및 재시작 안내 유틸리티 (Step6)

기능:
- manifest에서 실패한 마지막 step과 원인 추출
- resume 모드 시 완료된 step과 재시작 지점 정보 생성
"""

from typing import Dict, List, Optional, Tuple, Any
from pathlib import Path

from backend.utils.run_manager import load_run_manifest


def get_last_failure_summary(
    run_id: str,
    base_dir: Optional[Path] = None
) -> Optional[Dict[str, Any]]:
    """
    manifest에서 실패한 마지막 step 정보 추출
    
    Args:
        run_id: 실행 ID
        base_dir: 기본 디렉토리
    
    Returns:
        Optional[Dict]: 실패 정보 (없으면 None)
        {
            "run_id": str,
            "failed_step": str,
            "status": str,
            "reason": str
        }
    """
    manifest = load_run_manifest(run_id, base_dir)
    if manifest is None:
        return None
    
    steps = manifest.get("steps", {})
    
    # step1~step4 순서로 확인하여 실패한 마지막 step 찾기
    step_order = ["step1", "step2", "step3", "step4"]
    last_failed_step = None
    last_failed_status = None
    last_failed_reason = None
    
    for step_name in step_order:
        step_data = steps.get(step_name, {})
        status = step_data.get("status")
        
        if status and status != "success":
            last_failed_step = step_name
            last_failed_status = status
            
            # reason 추출 (여러 가능한 필드 확인)
            reason = (
                step_data.get("last_error") or
                step_data.get("error") or
                (step_data.get("errors", [])[0] if step_data.get("errors") else None) or
                "unknown"
            )
            last_failed_reason = reason
    
    if last_failed_step is None:
        return None
    
    return {
        "run_id": run_id,
        "failed_step": last_failed_step,
        "status": last_failed_status,
        "reason": last_failed_reason
    }


def format_failure_summary(failure_info: Dict[str, Any]) -> str:
    """
    실패 요약 문자열 생성
    
    Args:
        failure_info: get_last_failure_summary() 반환값
    
    Returns:
        str: 포맷된 실패 요약 문자열
    """
    run_id = failure_info.get("run_id", "unknown")
    failed_step = failure_info.get("failed_step", "unknown")
    status = failure_info.get("status", "unknown")
    reason = failure_info.get("reason", "unknown")
    
    lines = [
        "❌ LAST FAILURE SUMMARY",
        f"- RUN_ID: {run_id}",
        f"- FAILED_STEP: {failed_step}",
        f"- STATUS: {status}",
        f"- REASON: {reason}"
    ]
    
    return "\n".join(lines)


def get_resume_info(
    run_id: str,
    base_dir: Optional[Path] = None
) -> Dict[str, Any]:
    """
    resume 모드 정보 생성
    
    Args:
        run_id: 실행 ID
        base_dir: 기본 디렉토리
    
    Returns:
        Dict: resume 정보
        {
            "completed_steps": List[str],
            "resume_from": Optional[str],
            "skipped_scenes": List[int]
        }
    """
    manifest = load_run_manifest(run_id, base_dir)
    if manifest is None:
        return {
            "completed_steps": [],
            "resume_from": None,
            "skipped_scenes": []
        }
    
    steps = manifest.get("steps", {})
    step_order = ["step1", "step2", "step3", "step4"]
    
    completed_steps = []
    resume_from = None
    
    for step_name in step_order:
        step_data = steps.get(step_name, {})
        status = step_data.get("status")
        
        if status == "success":
            completed_steps.append(step_name)
        else:
            if resume_from is None:
                resume_from = step_name
    
    # Step4의 경우, 완료된 scene들도 확인
    skipped_scenes = []
    if "step4" in steps:
        step4_data = steps["step4"]
        step4_scenes = step4_data.get("scenes", {})
        
        for scene_key, scene_data in step4_scenes.items():
            if scene_data.get("status") == "success":
                try:
                    scene_index = int(scene_key)
                    skipped_scenes.append(scene_index)
                except (ValueError, TypeError):
                    pass
        
        skipped_scenes.sort()
    
    return {
        "completed_steps": completed_steps,
        "resume_from": resume_from,
        "skipped_scenes": skipped_scenes
    }


def format_resume_info(resume_info: Dict[str, Any]) -> str:
    """
    resume 정보 문자열 생성
    
    Args:
        resume_info: get_resume_info() 반환값
    
    Returns:
        str: 포맷된 resume 정보 문자열
    """
    completed_steps = resume_info.get("completed_steps", [])
    resume_from = resume_info.get("resume_from", "unknown")
    skipped_scenes = resume_info.get("skipped_scenes", [])
    
    lines = [
        "🔁 RESUME MODE",
        f"- COMPLETED_STEPS: {', '.join(completed_steps) if completed_steps else 'none'}",
        f"- RESUME_FROM: {resume_from}",
        f"- SKIPPED_SCENES: {skipped_scenes if skipped_scenes else '[]'}"
    ]
    
    return "\n".join(lines)

