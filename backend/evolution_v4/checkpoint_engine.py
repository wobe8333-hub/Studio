"""
v4-Step5: Checkpoint Engine

기능:
- v4-Step1~4 산출물을 참조하여 CheckpointV4 생성
- 모든 입력 파일의 sha256 해시 기록
- 회귀 감지용 메타데이터 생성
- 실제 실행/변경 금지
"""

import json
import hashlib
from pathlib import Path
from typing import Dict, Any, Optional

from backend.evolution_v4.schema import utc_now_iso
from backend.evolution_v4.apply_engine import sanitize_policy_id


def sha256_file(path: Path) -> str:
    """
    파일의 SHA256 해시 계산
    
    Args:
        path: 파일 경로
    
    Returns:
        str: SHA256 해시 (hex)
    """
    sha256_hash = hashlib.sha256()
    with open(path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()


def load_json_safe(path: Path) -> Optional[Dict[str, Any]]:
    """
    JSON 파일 안전 로드
    
    Args:
        path: 파일 경로
    
    Returns:
        Optional[Dict]: JSON 데이터 (실패 시 None)
    """
    if not path.exists():
        return None
    
    try:
        encoding = "utf-8-sig" if path.suffix == ".json" else "utf-8"
        with open(path, "r", encoding=encoding) as f:
            return json.load(f)
    except Exception:
        return None


def create_checkpoint(
    run_id: str,
    baseline_path: Path,
    candidates_path: Path,
    policies_path: Path,
    plan_patch_path: Path,
    plan_path: Optional[Path] = None
) -> Dict[str, Any]:
    """
    CheckpointV4 생성
    
    Args:
        run_id: 실행 ID
        baseline_path: baseline 파일 경로
        candidates_path: candidates 파일 경로
        policies_path: policies 파일 경로
        plan_patch_path: plan_patch 파일 경로
        plan_path: plan 파일 경로 (옵션)
    
    Returns:
        Dict: CheckpointV4 JSON 데이터
    """
    created_at = utc_now_iso()
    checkpoint_id = f"checkpoint_v4_step5:{run_id}:{created_at}"
    
    # 입력 경로
    inputs = {
        "baseline_path": str(baseline_path.resolve().as_posix()),
        "candidates_path": str(candidates_path.resolve().as_posix()),
        "policies_path": str(policies_path.resolve().as_posix()),
        "plan_patch_path": str(plan_patch_path.resolve().as_posix()),
        "plan_path": str(plan_path.resolve().as_posix()) if plan_path and plan_path.exists() else None
    }
    
    # 해시 계산
    hashes = {
        "baseline_sha256": sha256_file(baseline_path),
        "candidates_sha256": sha256_file(candidates_path),
        "policies_sha256": sha256_file(policies_path),
        "plan_patch_sha256": sha256_file(plan_patch_path)
    }
    
    if plan_path and plan_path.exists():
        hashes["plan_sha256"] = sha256_file(plan_path)
    else:
        hashes["plan_sha256"] = None
    
    # 상태 스냅샷 (각 산출물의 state 확인)
    baseline_data = load_json_safe(baseline_path)
    candidates_data = load_json_safe(candidates_path)
    policies_data = load_json_safe(policies_path)
    plan_patch_data = load_json_safe(plan_patch_path)
    
    state_snapshot = {
        "baseline_state": baseline_data.get("state", "UNKNOWN") if baseline_data else "UNKNOWN",
        "candidates_state": candidates_data.get("state", "UNKNOWN") if candidates_data else "UNKNOWN",
        "policies_state": policies_data.get("state", "UNKNOWN") if policies_data else "UNKNOWN",
        "applied_state": plan_patch_data.get("state", "UNKNOWN") if plan_patch_data else "UNKNOWN"
    }
    
    # 회귀 방지 가드
    regression_guard = {
        "guarded": True,
        "compare_keys": [
            "baseline_sha256",
            "candidates_sha256",
            "policies_sha256",
            "plan_patch_sha256",
            "plan_sha256"
        ]
    }
    
    return {
        "run_id": run_id,
        "checkpoint_id": checkpoint_id,
        "created_at": created_at,
        "inputs": inputs,
        "hashes": hashes,
        "state_snapshot": state_snapshot,
        "regression_guard": regression_guard,
        "version": "v4_step5",
        "state": "CHECKPOINT_FROZEN"
    }


def create_rollback_manifest(
    checkpoint: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Rollback Manifest 생성
    
    Args:
        checkpoint: CheckpointV4 데이터
    
    Returns:
        Dict: Rollback Manifest JSON 데이터
    """
    run_id = checkpoint["run_id"]
    created_at = checkpoint["created_at"]
    rollback_id = f"rollback_v4_step5:{run_id}:{created_at}"
    
    # 복원 대상 경로
    inputs = checkpoint.get("inputs", {})
    restore_targets = {
        "baseline": inputs.get("baseline_path", ""),
        "candidates": inputs.get("candidates_path", ""),
        "policies": inputs.get("policies_path", ""),
        "plan_patch": inputs.get("plan_patch_path", ""),
        "plan": inputs.get("plan_path")
    }
    
    # 해시 복사
    hashes = checkpoint.get("hashes", {}).copy()
    
    # 롤백 지시사항
    instructions = [
        "모든 해시가 일치하는지 먼저 검증한다",
        "불일치 시 롤백 중단",
        "plan 원본은 복원 대상이 아니다(참조용)"
    ]
    
    return {
        "run_id": run_id,
        "rollback_id": rollback_id,
        "created_at": created_at,
        "restore_targets": restore_targets,
        "hashes": hashes,
        "instructions": instructions,
        "version": "v4_step5"
    }


def generate_checkpoint(
    run_id: str,
    policy_id: str,
    project_root: Optional[Path] = None
) -> tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]], Optional[str]]:
    """
    CheckpointV4 + Rollback Manifest 생성 (전체 프로세스)
    
    Args:
        run_id: 실행 ID
        policy_id: Step4에서 사용한 policy_id
        project_root: 프로젝트 루트 경로
    
    Returns:
        Tuple[Optional[Dict], Optional[Dict], Optional[str]]: (checkpoint, rollback_manifest, error_message)
    """
    if project_root is None:
        project_root = Path.cwd()
    
    # Baseline 검증
    baseline_path = project_root / "backend" / "output" / "evolution_v4" / "baselines" / f"{run_id}.json"
    baseline_lock_path = project_root / "backend" / "output" / "evolution_v4" / "baselines" / f"{run_id}.lock"
    
    if not baseline_path.exists():
        return None, None, f"Baseline not found: {baseline_path.resolve()}"
    
    if not baseline_lock_path.exists():
        return None, None, f"Baseline lock not found: {baseline_lock_path.resolve()}"
    
    # Candidates 검증
    candidates_path = project_root / "backend" / "output" / "evolution_v4" / "candidates" / f"{run_id}.json"
    
    if not candidates_path.exists():
        return None, None, f"Candidates not found: {candidates_path.resolve()}"
    
    # Policies 검증
    policies_path = project_root / "backend" / "output" / "evolution_v4" / "policies" / f"{run_id}.json"
    policies_lock_path = project_root / "backend" / "output" / "evolution_v4" / "policies" / f"{run_id}.lock"
    
    if not policies_path.exists():
        return None, None, f"Policies not found: {policies_path.resolve()}"
    
    if not policies_lock_path.exists():
        return None, None, f"Policies lock not found: {policies_lock_path.resolve()}"
    
    # PlanPatch 검증 (policy_id 필요)
    policy_id_sanitized = sanitize_policy_id(policy_id)
    plan_patch_path = project_root / "backend" / "output" / "evolution_v4" / "applied" / run_id / policy_id_sanitized / "plan_patch.json"
    plan_patch_lock_path = project_root / "backend" / "output" / "evolution_v4" / "applied" / run_id / policy_id_sanitized / ".lock"
    
    if not plan_patch_path.exists():
        return None, None, f"Plan patch not found: {plan_patch_path.resolve()}"
    
    if not plan_patch_lock_path.exists():
        return None, None, f"Plan patch lock not found: {plan_patch_lock_path.resolve()}"
    
    # Plan 검증 (옵션)
    plan_path = project_root / "backend" / "output" / "plans" / f"{run_id}.json"
    plan = load_json_safe(plan_path) if plan_path.exists() else None
    
    # Checkpoint 생성
    checkpoint = create_checkpoint(
        run_id, baseline_path, candidates_path, policies_path, plan_patch_path,
        plan_path if plan_path.exists() else None
    )
    
    # Rollback Manifest 생성
    rollback_manifest = create_rollback_manifest(checkpoint)
    
    return checkpoint, rollback_manifest, None

