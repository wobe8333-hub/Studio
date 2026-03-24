"""
v5-Step2: Plan Draft + Simulation Report 저장 + Lock 관리

저장 위치:
- plan_draft: backend/output/autonomy_v5/plans/<run_id>_plan_draft.json
- simulation_report: backend/output/autonomy_v5/reports/<run_id>_simulation_report.json
- lock: backend/output/autonomy_v5/plans/<run_id>_plan_draft.lock
"""

import json
from pathlib import Path
from typing import Dict, Any, Optional

from backend.autonomy_v5.schema import utc_now_compact


def ensure_directories(project_root: Path) -> tuple[Path, Path]:
    """
    출력 디렉토리 생성
    
    Args:
        project_root: 프로젝트 루트 경로
    
    Returns:
        Tuple[Path, Path]: (plans_dir, reports_dir)
    """
    plans_dir = project_root / "backend" / "output" / "autonomy_v5" / "plans"
    reports_dir = project_root / "backend" / "output" / "autonomy_v5" / "reports"
    
    plans_dir.mkdir(parents=True, exist_ok=True)
    reports_dir.mkdir(parents=True, exist_ok=True)
    
    return plans_dir, reports_dir


def save_plan_draft(
    plan_draft: Dict[str, Any],
    project_root: Path,
    force: bool = False
) -> tuple[Optional[Path], Optional[str]]:
    """
    PlanDraftV5 저장 + Lock 생성
    
    Args:
        plan_draft: PlanDraftV5 데이터
        project_root: 프로젝트 루트 경로
        force: 기존 lock이 있어도 덮어쓰기 허용
    
    Returns:
        Tuple[Optional[Path], Optional[str]]: (plan_draft_path, error_message)
    """
    plans_dir, _ = ensure_directories(project_root)
    
    run_id = plan_draft["run_id"]
    plan_draft_path = plans_dir / f"{run_id}_plan_draft.json"
    lock_path = plans_dir / f"{run_id}_plan_draft.lock"
    
    # Lock 존재 확인
    if lock_path.exists() and not force:
        return None, "PLAN_DRAFT_ALREADY_FROZEN"
    
    # --force 시 백업
    if force and plan_draft_path.exists():
        backup_path = plans_dir / f"{run_id}_plan_draft.json.bak.{utc_now_compact()}"
        try:
            plan_draft_path.rename(backup_path)
        except Exception as e:
            return None, f"Failed to backup plan_draft: {str(e)}"
    
    # PlanDraft 저장 (utf-8-sig for PowerShell compatibility)
    try:
        with open(plan_draft_path, "w", encoding="utf-8-sig") as f:
            json.dump(plan_draft, f, ensure_ascii=False, indent=2)
    except Exception as e:
        return None, f"Failed to save plan_draft: {str(e)}"
    
    # Lock 생성
    lock_data = {
        "run_id": run_id,
        "plan_draft_path": str(plan_draft_path.resolve()),
        "frozen_at": plan_draft["created_at"]
    }
    
    try:
        with open(lock_path, "w", encoding="utf-8") as f:
            json.dump(lock_data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        return None, f"Failed to save lock: {str(e)}"
    
    return plan_draft_path, None


def save_simulation_report(
    simulation_report: Dict[str, Any],
    project_root: Path,
    force: bool = False
) -> tuple[Optional[Path], Optional[str]]:
    """
    Simulation Report 저장
    
    Args:
        simulation_report: Simulation Report 데이터
        project_root: 프로젝트 루트 경로
        force: 기존 파일이 있어도 덮어쓰기 허용
    
    Returns:
        Tuple[Optional[Path], Optional[str]]: (report_path, error_message)
    """
    _, reports_dir = ensure_directories(project_root)
    
    run_id = simulation_report["run_id"]
    report_path = reports_dir / f"{run_id}_simulation_report.json"
    
    # --force 시 백업
    if force and report_path.exists():
        backup_path = reports_dir / f"{run_id}_simulation_report.json.bak.{utc_now_compact()}"
        try:
            report_path.rename(backup_path)
        except Exception as e:
            return None, f"Failed to backup simulation report: {str(e)}"
    
    # Simulation Report 저장 (utf-8-sig for PowerShell compatibility)
    try:
        with open(report_path, "w", encoding="utf-8-sig") as f:
            json.dump(simulation_report, f, ensure_ascii=False, indent=2)
    except Exception as e:
        return None, f"Failed to save simulation report: {str(e)}"
    
    return report_path, None

