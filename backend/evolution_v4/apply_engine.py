"""
v4-Step4: Limited Apply Engine

기능:
- PolicyDraftSet에서 지정된 policy_id를 선택하여 PlanPatchV4 생성
- 실제 plan 수정/재생성 금지 (패치 파일만 생성)
- LLM/Render 호출 금지
"""

import json
import hashlib
from pathlib import Path
from typing import Dict, Any, Optional

from backend.evolution_v4.schema import utc_now_iso


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


def sanitize_policy_id(policy_id: str) -> str:
    """
    policy_id를 파일/폴더명 안전하게 변환
    
    Args:
        policy_id: 원본 policy_id
    
    Returns:
        str: sanitized policy_id (":" -> "__", 공백 -> "_")
    """
    return policy_id.replace(":", "__").replace(" ", "_")


def load_baseline(baseline_path: Path) -> Optional[Dict[str, Any]]:
    """BaselineV4 로드"""
    if not baseline_path.exists():
        return None
    
    try:
        with open(baseline_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def load_candidates(candidates_path: Path) -> Optional[Dict[str, Any]]:
    """CandidateSet 로드"""
    if not candidates_path.exists():
        return None
    
    try:
        with open(candidates_path, "r", encoding="utf-8-sig") as f:
            return json.load(f)
    except Exception:
        return None


def load_policies(policies_path: Path) -> Optional[Dict[str, Any]]:
    """PolicyDraftSet 로드"""
    if not policies_path.exists():
        return None
    
    try:
        with open(policies_path, "r", encoding="utf-8-sig") as f:
            return json.load(f)
    except Exception:
        return None


def load_plan(plan_path: Path) -> Optional[Dict[str, Any]]:
    """Plan 로드 (옵션)"""
    if not plan_path.exists():
        return None
    
    try:
        with open(plan_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def find_policy(policies: Dict[str, Any], policy_id: str) -> Optional[Dict[str, Any]]:
    """
    PolicyDraftSet에서 지정된 policy_id 찾기
    
    Args:
        policies: PolicyDraftSet 데이터
        policy_id: 찾을 policy_id
    
    Returns:
        Optional[Dict]: PolicyDraft 데이터 (없으면 None)
    """
    policy_list = policies.get("policies", [])
    
    for policy in policy_list:
        if isinstance(policy, dict) and policy.get("policy_id") == policy_id:
            return policy
    
    return None


def create_plan_patch(
    run_id: str,
    policy: Dict[str, Any],
    baseline: Dict[str, Any],
    baseline_path: Path,
    candidates_path: Path,
    policies_path: Path,
    plan_path: Optional[Path] = None
) -> Dict[str, Any]:
    """
    PlanPatchV4 생성
    
    Args:
        run_id: 실행 ID
        policy: PolicyDraft 데이터
        baseline: BaselineV4 데이터
        baseline_path: baseline 파일 경로
        candidates_path: candidates 파일 경로
        policies_path: policies 파일 경로
        plan_path: plan 파일 경로 (옵션)
    
    Returns:
        Dict: PlanPatchV4 JSON 데이터
    """
    policy_id = policy.get("policy_id", "")
    applied_at = utc_now_iso()
    applied_id = f"apply_v4_step4:{run_id}:{policy_id}:{applied_at}"
    
    # inputs 생성
    inputs = {
        "baseline_path": str(baseline_path.resolve().as_posix()),
        "candidates_path": str(candidates_path.resolve().as_posix()),
        "policies_path": str(policies_path.resolve().as_posix()),
        "plan_path": str(plan_path.resolve().as_posix()) if plan_path and plan_path.exists() else None
    }
    
    # patch 생성 (change_spec.proposed_changes 그대로 복사)
    change_spec = policy.get("change_spec", {})
    proposed_changes = change_spec.get("proposed_changes", [])
    
    # change_spec.scope 검증
    if change_spec.get("scope") != "EVALUATION_ONLY":
        raise ValueError(f"Invalid change_spec.scope: {change_spec.get('scope')} (expected: EVALUATION_ONLY)")
    
    patch = {
        "mode": "PATCH_ONLY",
        "proposed_changes": proposed_changes.copy()
    }
    
    # impact_guard 생성
    impact_guard = {
        "must_not_touch": [
            "backend/output/plans/*",
            "LLM_CALL",
            "RENDER_CALL",
            "AUTO_APPLY",
            "AUTO_SELECT"
        ],
        "scope": "LIMITED"
    }
    
    # evidence 생성 (source_hashes_sha256)
    source_hashes = {}
    
    # baseline 해시
    if baseline_path.exists():
        baseline_path_str = str(baseline_path.resolve().as_posix())
        source_hashes[baseline_path_str] = sha256_file(baseline_path)
    
    # candidates 해시
    if candidates_path.exists():
        candidates_path_str = str(candidates_path.resolve().as_posix())
        source_hashes[candidates_path_str] = sha256_file(candidates_path)
    
    # policies 해시
    if policies_path.exists():
        policies_path_str = str(policies_path.resolve().as_posix())
        source_hashes[policies_path_str] = sha256_file(policies_path)
    
    # plan 해시 (있으면)
    if plan_path and plan_path.exists():
        plan_path_str = str(plan_path.resolve().as_posix())
        source_hashes[plan_path_str] = sha256_file(plan_path)
    
    # baseline_kpis_snapshot (baseline.kpis 참조 복사)
    baseline_kpis_snapshot = baseline.get("kpis", {}).copy()
    
    evidence = {
        "source_hashes_sha256": source_hashes,
        "baseline_kpis_snapshot": baseline_kpis_snapshot
    }
    
    # notes 생성
    notes = {
        "warnings": []
    }
    
    return {
        "run_id": run_id,
        "policy_id": policy_id,
        "applied_id": applied_id,
        "applied_at": applied_at,
        "inputs": inputs,
        "patch": patch,
        "impact_guard": impact_guard,
        "evidence": evidence,
        "notes": notes,
        "version": "v4_step4",
        "state": "APPLIED_PATCH_ONLY"
    }


def generate_plan_patch(
    run_id: str,
    policy_id: str,
    project_root: Optional[Path] = None
) -> tuple[Optional[Dict[str, Any]], Optional[str]]:
    """
    PlanPatchV4 생성 (전체 프로세스)
    
    Args:
        run_id: 실행 ID
        policy_id: 적용할 policy_id
        project_root: 프로젝트 루트 경로
    
    Returns:
        Tuple[Optional[Dict], Optional[str]]: (plan_patch, error_message)
    """
    if project_root is None:
        project_root = Path.cwd()
    
    # Baseline 로드
    baseline_path = project_root / "backend" / "output" / "evolution_v4" / "baselines" / f"{run_id}.json"
    baseline_lock_path = project_root / "backend" / "output" / "evolution_v4" / "baselines" / f"{run_id}.lock"
    
    if not baseline_path.exists():
        return None, f"Baseline not found: {baseline_path.resolve()}"
    
    if not baseline_lock_path.exists():
        return None, f"Baseline lock not found: {baseline_lock_path.resolve()} (baseline not frozen)"
    
    baseline = load_baseline(baseline_path)
    if baseline is None:
        return None, f"Failed to load baseline: {baseline_path.resolve()}"
    
    # Candidates 로드
    candidates_path = project_root / "backend" / "output" / "evolution_v4" / "candidates" / f"{run_id}.json"
    
    if not candidates_path.exists():
        return None, f"Candidates not found: {candidates_path.resolve()}"
    
    candidates = load_candidates(candidates_path)
    if candidates is None:
        return None, f"Failed to load candidates: {candidates_path.resolve()}"
    
    # Policies 로드
    policies_path = project_root / "backend" / "output" / "evolution_v4" / "policies" / f"{run_id}.json"
    policies_lock_path = project_root / "backend" / "output" / "evolution_v4" / "policies" / f"{run_id}.lock"
    
    if not policies_path.exists():
        return None, f"Policies not found: {policies_path.resolve()}"
    
    if not policies_lock_path.exists():
        return None, f"Policies lock not found: {policies_lock_path.resolve()} (policies not frozen)"
    
    policies = load_policies(policies_path)
    if policies is None:
        return None, f"Failed to load policies: {policies_path.resolve()}"
    
    # Policy 검증
    if policies.get("version") != "v4_step3":
        return None, f"Invalid policies version: {policies.get('version')} (expected: v4_step3)"
    
    if policies.get("state") != "POLICY_DRAFT_ONLY":
        return None, f"Invalid policies state: {policies.get('state')} (expected: POLICY_DRAFT_ONLY)"
    
    # 지정된 policy 찾기
    policy = find_policy(policies, policy_id)
    if policy is None:
        return None, f"Policy not found: {policy_id}"
    
    # change_spec.scope 검증
    change_spec = policy.get("change_spec", {})
    if change_spec.get("scope") != "EVALUATION_ONLY":
        return None, f"Invalid change_spec.scope: {change_spec.get('scope')} (expected: EVALUATION_ONLY)"
    
    # Plan 로드 (옵션)
    plan_path = project_root / "backend" / "output" / "plans" / f"{run_id}.json"
    plan = load_plan(plan_path) if plan_path.exists() else None
    
    # PlanPatch 생성
    plan_patch = create_plan_patch(
        run_id, policy, baseline, baseline_path, candidates_path, policies_path, plan_path if plan_path.exists() else None
    )
    
    return plan_patch, None

