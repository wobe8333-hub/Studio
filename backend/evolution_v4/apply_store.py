"""
v4-Step4: PlanPatch 저장 + Lock 관리

저장 위치:
- plan_patch: backend/output/evolution_v4/applied/<run_id>/<policy_id_sanitized>/plan_patch.json
- report: backend/output/evolution_v4/reports/<run_id>_<policy_id_sanitized>_apply_report.json
- lock: backend/output/evolution_v4/applied/<run_id>/<policy_id_sanitized>/.lock
"""

import json
from pathlib import Path
from typing import Dict, Any, Optional

from backend.evolution_v4.schema import utc_now_iso, utc_now_compact
from backend.evolution_v4.apply_engine import sanitize_policy_id


def ensure_directories(project_root: Path, run_id: str, policy_id: str) -> tuple[Path, Path]:
    """
    출력 디렉토리 생성
    
    Args:
        project_root: 프로젝트 루트 경로
        run_id: 실행 ID
        policy_id: policy_id
    
    Returns:
        Tuple[Path, Path]: (applied_dir, reports_dir)
    """
    policy_id_sanitized = sanitize_policy_id(policy_id)
    applied_dir = project_root / "backend" / "output" / "evolution_v4" / "applied" / run_id / policy_id_sanitized
    reports_dir = project_root / "backend" / "output" / "evolution_v4" / "reports"
    
    applied_dir.mkdir(parents=True, exist_ok=True)
    reports_dir.mkdir(parents=True, exist_ok=True)
    
    return applied_dir, reports_dir


def save_plan_patch(
    plan_patch: Dict[str, Any],
    project_root: Path,
    force: bool = False
) -> tuple[Optional[Path], Optional[str]]:
    """
    PlanPatchV4 저장 + Lock 생성
    
    Args:
        plan_patch: PlanPatchV4 데이터
        project_root: 프로젝트 루트 경로
        force: 기존 lock이 있어도 덮어쓰기 허용
    
    Returns:
        Tuple[Optional[Path], Optional[str]]: (patch_path, error_message)
    """
    run_id = plan_patch["run_id"]
    policy_id = plan_patch["policy_id"]
    policy_id_sanitized = sanitize_policy_id(policy_id)
    
    applied_dir, _ = ensure_directories(project_root, run_id, policy_id)
    
    patch_path = applied_dir / "plan_patch.json"
    lock_path = applied_dir / ".lock"
    
    # Lock 존재 확인
    if lock_path.exists() and not force:
        return None, "APPLY_ALREADY_FROZEN"
    
    # --force 시 백업
    if force and patch_path.exists():
        backup_path = applied_dir / f"plan_patch.json.bak.{utc_now_compact()}"
        try:
            patch_path.rename(backup_path)
        except Exception as e:
            return None, f"Failed to backup plan_patch: {str(e)}"
    
    # PlanPatch 저장 (utf-8-sig for PowerShell compatibility)
    try:
        with open(patch_path, "w", encoding="utf-8-sig") as f:
            json.dump(plan_patch, f, ensure_ascii=False, indent=2)
    except Exception as e:
        return None, f"Failed to save plan_patch: {str(e)}"
    
    # Lock 생성
    lock_data = {
        "run_id": run_id,
        "policy_id": policy_id,
        "patch_path": str(patch_path.resolve()),
        "frozen_at": plan_patch["applied_at"]
    }
    
    try:
        with open(lock_path, "w", encoding="utf-8") as f:
            json.dump(lock_data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        return None, f"Failed to save lock: {str(e)}"
    
    return patch_path, None


def save_report(
    plan_patch: Dict[str, Any],
    project_root: Path
) -> tuple[Optional[Path], Optional[str]]:
    """
    Apply 리포트 저장
    
    Args:
        plan_patch: PlanPatchV4 데이터
        project_root: 프로젝트 루트 경로
    
    Returns:
        Tuple[Optional[Path], Optional[str]]: (report_path, error_message)
    """
    run_id = plan_patch["run_id"]
    policy_id = plan_patch["policy_id"]
    policy_id_sanitized = sanitize_policy_id(policy_id)
    
    _, reports_dir = ensure_directories(project_root, run_id, policy_id)
    
    report_path = reports_dir / f"{run_id}_{policy_id_sanitized}_apply_report.json"
    
    # 리포트 데이터 생성
    report = {
        "run_id": run_id,
        "policy_id": policy_id,
        "applied_at": plan_patch["applied_at"],
        "applied_id": plan_patch["applied_id"],
        "inputs": plan_patch["inputs"],
        "patch_mode": plan_patch["patch"]["mode"],
        "proposed_changes_count": len(plan_patch["patch"].get("proposed_changes", [])),
        "notes": plan_patch.get("notes", {})
    }
    
    try:
        with open(report_path, "w", encoding="utf-8-sig") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
    except Exception as e:
        return None, f"Failed to save report: {str(e)}"
    
    return report_path, None

