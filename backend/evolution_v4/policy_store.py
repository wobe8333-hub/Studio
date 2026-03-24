"""
v4-Step3: Policy 저장 + Lock 관리

저장 위치:
- policy: backend/output/evolution_v4/policies/<run_id>.json
- report: backend/output/evolution_v4/reports/<run_id>_policy_report.json
- lock: backend/output/evolution_v4/policies/<run_id>.lock
"""

import json
from pathlib import Path
from typing import Dict, Any, Optional

from backend.evolution_v4.schema import utc_now_iso, utc_now_compact


def ensure_directories(project_root: Path) -> tuple[Path, Path]:
    """
    출력 디렉토리 생성
    
    Args:
        project_root: 프로젝트 루트 경로
    
    Returns:
        Tuple[Path, Path]: (policies_dir, reports_dir)
    """
    policies_dir = project_root / "backend" / "output" / "evolution_v4" / "policies"
    reports_dir = project_root / "backend" / "output" / "evolution_v4" / "reports"
    
    policies_dir.mkdir(parents=True, exist_ok=True)
    reports_dir.mkdir(parents=True, exist_ok=True)
    
    return policies_dir, reports_dir


def save_policy_draft(
    policy_draft_set: Dict[str, Any],
    project_root: Path,
    force: bool = False
) -> tuple[Optional[Path], Optional[str]]:
    """
    PolicyDraftSet 저장 + Lock 생성
    
    Args:
        policy_draft_set: PolicyDraftSet 데이터
        project_root: 프로젝트 루트 경로
        force: 기존 lock이 있어도 덮어쓰기 허용
    
    Returns:
        Tuple[Optional[Path], Optional[str]]: (policy_path, error_message)
    """
    policies_dir, _ = ensure_directories(project_root)
    
    run_id = policy_draft_set["run_id"]
    policy_path = policies_dir / f"{run_id}.json"
    lock_path = policies_dir / f"{run_id}.lock"
    
    # Lock 존재 확인
    if lock_path.exists() and not force:
        return None, "POLICY_ALREADY_FROZEN"
    
    # --force 시 백업
    if force and policy_path.exists():
        backup_path = policies_dir / f"{run_id}.json.bak.{utc_now_compact()}"
        try:
            policy_path.rename(backup_path)
        except Exception as e:
            return None, f"Failed to backup policy: {str(e)}"
    
    # Policy 저장 (utf-8-sig for PowerShell compatibility)
    try:
        with open(policy_path, "w", encoding="utf-8-sig") as f:
            json.dump(policy_draft_set, f, ensure_ascii=False, indent=2)
    except Exception as e:
        return None, f"Failed to save policy: {str(e)}"
    
    # Lock 생성
    lock_data = {
        "run_id": run_id,
        "policy_path": str(policy_path.resolve()),
        "frozen_at": policy_draft_set["created_at"]
    }
    
    try:
        with open(lock_path, "w", encoding="utf-8") as f:
            json.dump(lock_data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        return None, f"Failed to save lock: {str(e)}"
    
    return policy_path, None


def save_report(
    policy_draft_set: Dict[str, Any],
    project_root: Path
) -> tuple[Optional[Path], Optional[str]]:
    """
    Policy 리포트 저장
    
    Args:
        policy_draft_set: PolicyDraftSet 데이터
        project_root: 프로젝트 루트 경로
    
    Returns:
        Tuple[Optional[Path], Optional[str]]: (report_path, error_message)
    """
    _, reports_dir = ensure_directories(project_root)
    
    run_id = policy_draft_set["run_id"]
    report_path = reports_dir / f"{run_id}_policy_report.json"
    
    # 리포트 데이터 생성
    report = {
        "run_id": run_id,
        "created_at": policy_draft_set["created_at"],
        "baseline_ref": policy_draft_set["baseline_ref"],
        "candidates_ref": policy_draft_set["candidates_ref"],
        "policy_count": len(policy_draft_set.get("policies", [])),
        "policy_types": list(set(p.get("candidate_type") for p in policy_draft_set.get("policies", []))),
        "notes": policy_draft_set.get("notes", {})
    }
    
    try:
        with open(report_path, "w", encoding="utf-8-sig") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
    except Exception as e:
        return None, f"Failed to save report: {str(e)}"
    
    return report_path, None

