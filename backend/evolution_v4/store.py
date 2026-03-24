"""
v4-Step1: Baseline 저장 + Lock 관리

저장 위치:
- baseline: backend/output/evolution_v4/baselines/<run_id>.json
- report: backend/output/evolution_v4/reports/<run_id>_kpi_report.json
- lock: backend/output/evolution_v4/baselines/<run_id>.lock
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
        Tuple[Path, Path]: (baselines_dir, reports_dir)
    """
    baselines_dir = project_root / "backend" / "output" / "evolution_v4" / "baselines"
    reports_dir = project_root / "backend" / "output" / "evolution_v4" / "reports"
    
    baselines_dir.mkdir(parents=True, exist_ok=True)
    reports_dir.mkdir(parents=True, exist_ok=True)
    
    return baselines_dir, reports_dir


def save_baseline(
    baseline: Dict[str, Any],
    project_root: Path,
    force: bool = False
) -> tuple[Optional[Path], Optional[str]]:
    """
    Baseline 저장 + Lock 생성
    
    Args:
        baseline: BaselineV4 데이터
        project_root: 프로젝트 루트 경로
        force: 기존 lock이 있어도 덮어쓰기 허용
    
    Returns:
        Tuple[Optional[Path], Optional[str]]: (baseline_path, error_message)
    """
    baselines_dir, _ = ensure_directories(project_root)
    
    run_id = baseline["run_id"]
    baseline_path = baselines_dir / f"{run_id}.json"
    lock_path = baselines_dir / f"{run_id}.lock"
    
    # Lock 존재 확인
    if lock_path.exists() and not force:
        return None, "BASELINE_ALREADY_FROZEN"
    
    # --force 시 백업
    if force and baseline_path.exists():
        backup_path = baselines_dir / f"{run_id}.json.bak.{utc_now_compact()}"
        try:
            baseline_path.rename(backup_path)
        except Exception as e:
            return None, f"Failed to backup baseline: {str(e)}"
    
    # Baseline 저장
    try:
        with open(baseline_path, "w", encoding="utf-8", newline="\n") as f:
            json.dump(baseline, f, ensure_ascii=False, indent=2)
    except Exception as e:
        return None, f"Failed to save baseline: {str(e)}"
    
    # Lock 생성
    lock_data = {
        "run_id": run_id,
        "baseline_path": str(baseline_path.resolve()),
        "frozen_at": baseline["created_at"]
    }
    
    try:
        with open(lock_path, "w", encoding="utf-8", newline="\n") as f:
            json.dump(lock_data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        return None, f"Failed to save lock: {str(e)}"
    
    return baseline_path, None


def save_report(
    baseline: Dict[str, Any],
    project_root: Path
) -> tuple[Optional[Path], Optional[str]]:
    """
    KPI 리포트 저장
    
    Args:
        baseline: BaselineV4 데이터
        project_root: 프로젝트 루트 경로
    
    Returns:
        Tuple[Optional[Path], Optional[str]]: (report_path, error_message)
    """
    _, reports_dir = ensure_directories(project_root)
    
    run_id = baseline["run_id"]
    report_path = reports_dir / f"{run_id}_kpi_report.json"
    
    # 리포트 데이터 생성
    report = {
        "run_id": run_id,
        "baseline_id": baseline["baseline_id"],
        "created_at": baseline["created_at"],
        "kpis": baseline["kpis"],
        "notes": baseline["notes"]
    }
    
    try:
        with open(report_path, "w", encoding="utf-8", newline="\n") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
    except Exception as e:
        return None, f"Failed to save report: {str(e)}"
    
    return report_path, None

