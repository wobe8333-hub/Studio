"""
Step4 진입 차단 및 준비 상태 검증 유틸리티
"""
import json
from pathlib import Path
from typing import List, Tuple, Optional

from backend.utils.run_manager import load_run_manifest, get_run_dir, get_runs_root, get_project_root
from backend.utils.step3_converter import validate_fixed_spec


def check_step4_ready(run_id: str, base_dir: Optional[Path] = None) -> Tuple[bool, List[str]]:
    """
    Step4 실행 준비 상태를 검사한다.
    
    요구사항:
    - runs 폴더 존재
    - run_id 하위 폴더 존재
    - manifest.json 존재
    - step2.status == success
    - step3.status == success
    - scenes_fixed.json 존재 + 스펙 검증 통과
    """
    reasons: List[str] = []
    
    # runs_root 단일 진실 경로 계산
    runs_root = get_runs_root(base_dir)
    
    if not runs_root.exists():
        reasons.append(f"runs 폴더가 없습니다: {runs_root}")
        return False, reasons
    
    # run_dir 계산 (runs_root 기준)
    run_dir = runs_root / run_id
    if not run_dir.exists():
        reasons.append(f"run 폴더가 없습니다: {run_dir}")
        return False, reasons
    
    # manifest.json 경로
    manifest_path = run_dir / "manifest.json"
    if not manifest_path.exists():
        reasons.append(f"manifest.json이 없습니다: {manifest_path}")
        return False, reasons
    
    manifest = load_run_manifest(run_id, base_dir)
    if manifest is None:
        reasons.append(f"manifest.json 로드 실패: {manifest_path}")
        return False, reasons
    
    steps = manifest.get("steps", {})
    if steps.get("step2", {}).get("status") != "success":
        reasons.append("step2.status 가 success가 아닙니다")
    if steps.get("step3", {}).get("status") != "success":
        reasons.append("step3.status 가 success가 아닙니다")
    
    scenes_fixed_path = run_dir / "step3" / "scenes_fixed.json"
    if not scenes_fixed_path.exists():
        reasons.append(f"step3/scenes_fixed.json이 없습니다: {scenes_fixed_path}")
    else:
        try:
            with open(scenes_fixed_path, "r", encoding="utf-8") as f:
                fixed_data = json.load(f)
            is_valid, missing_required, forbidden_found = validate_fixed_spec(fixed_data)
            if not is_valid:
                reasons.append(f"scenes_fixed.json 스펙 검증 실패 (필수 누락 {len(missing_required)}, 금지 {len(forbidden_found)})")
        except Exception as exc:
            reasons.append(f"scenes_fixed.json 검증 중 오류: {exc}")
    
    return len(reasons) == 0, reasons


def enforce_step4_ready(run_id: str, base_dir: Optional[Path] = None) -> None:
    """
    Step4 준비 상태를 강제 검사하고 실패 시 예외를 발생시킨다.
    """
    ready, reasons = check_step4_ready(run_id, base_dir)
    if not ready:
        raise ValueError(f"Step4 진입 차단: {', '.join(reasons)}")

