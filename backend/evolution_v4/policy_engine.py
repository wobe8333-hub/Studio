"""
v4-Step3: Policy Engine

기능:
- BaselineV4 + CandidateSet을 입력으로 받아 PolicyDraft 생성
- 자동 선택/추천/랭킹 금지
- 정책 초안만 제공 (반영 금지)
"""

import json
import hashlib
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

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


def load_baseline(baseline_path: Path) -> Optional[Dict[str, Any]]:
    """
    BaselineV4 로드
    
    Args:
        baseline_path: baseline JSON 경로
    
    Returns:
        Optional[Dict]: baseline 데이터 (실패 시 None)
    """
    if not baseline_path.exists():
        return None
    
    try:
        with open(baseline_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def load_candidates(candidates_path: Path) -> Optional[Dict[str, Any]]:
    """
    CandidateSet 로드
    
    Args:
        candidates_path: candidates JSON 경로
    
    Returns:
        Optional[Dict]: candidates 데이터 (실패 시 None)
    """
    if not candidates_path.exists():
        return None
    
    try:
        with open(candidates_path, "r", encoding="utf-8-sig") as f:
            return json.load(f)
    except Exception:
        return None


def generate_policy_from_candidate(
    candidate: Dict[str, Any],
    baseline: Dict[str, Any],
    policy_index: int,
    candidates_path: Path
) -> Dict[str, Any]:
    """
    Candidate로부터 PolicyDraft 생성
    
    Args:
        candidate: Candidate 데이터
        baseline: BaselineV4 데이터
        policy_index: 정책 인덱스
        candidates_path: candidates 파일 경로
    
    Returns:
        Dict: PolicyDraft 데이터
    """
    candidate_id = candidate.get("candidate_id", f"cand_unknown:{policy_index}")
    candidate_type = candidate.get("type", "UNKNOWN")
    
    # policy_id 생성
    policy_id = f"policy_v4_step3:{candidate_id}:{policy_index}"
    
    # intent 생성 (제안 문장, 금지 표현 사용 금지)
    intent = candidate.get("description", "")
    # 금지 표현 제거/대체는 하지 않음 (입력 그대로 사용)
    
    # change_spec 생성
    proposed_changes = []
    # candidate의 constraints.allowed_scope를 기반으로 proposed_changes 생성
    allowed_scope = candidate.get("constraints", {}).get("allowed_scope", [])
    if allowed_scope:
        # 일반적인 변경 영역 제안 (실제 변경 금지)
        proposed_changes.append({
            "key": "policy_consideration",
            "description": f"Step3 정책 엔진에서 {candidate_type} 관점의 변경을 고려할 수 있습니다."
        })
    else:
        # 기본 변경 제안
        proposed_changes.append({
            "key": "policy_consideration",
            "description": f"Baseline KPI 기반 {candidate_type} 관점의 변경을 고려할 수 있습니다."
        })
    
    # impact_guard 생성
    baseline_path_str = baseline.get("inputs", {}).get("memory_snapshot_path", "")
    if baseline_path_str:
        baseline_path_resolved = str(Path(baseline_path_str).resolve().as_posix())
    else:
        baseline_path_resolved = ""
    
    candidates_path_str = str(candidates_path.resolve().as_posix())
    
    impact_guard = {
        "max_effect": "LIMITED",
        "must_not_touch": [
            "backend/output/plans/*",
            "LLM_CALL",
            "RENDER_CALL",
            "AUTO_APPLY",
            "AUTO_SELECT"
        ],
        "read_only_inputs": [
            baseline_path_resolved,
            candidates_path_str
        ]
    }
    
    # rationale 생성
    based_on_kpis = candidate.get("based_on", {}).get("kpis", [])
    observed_signals = candidate.get("based_on", {}).get("signals", [])
    
    # baseline.kpis와 교집합 중심으로 based_on_kpis 정제
    baseline_kpis = baseline.get("kpis", {})
    refined_kpis = [kpi for kpi in based_on_kpis if kpi in baseline_kpis]
    if not refined_kpis:
        refined_kpis = list(baseline_kpis.keys())[:3]  # 최대 3개
    
    why_now = f"Baseline에서 {', '.join(refined_kpis[:2])} 관련 신호가 관측되었습니다."
    if observed_signals:
        why_now += f" 관측된 신호: {', '.join(observed_signals[:2])}."
    
    rationale = {
        "based_on_kpis": refined_kpis,
        "observed_signals": observed_signals,
        "why_now": why_now
    }
    
    # evidence 생성
    baseline_kpis_snapshot = {}
    for kpi in refined_kpis:
        if kpi in baseline_kpis:
            baseline_kpis_snapshot[kpi] = baseline_kpis[kpi]
    
    # baseline.evidence.source_hashes_sha256 복사
    source_hashes = baseline.get("evidence", {}).get("source_hashes_sha256", {}).copy()
    
    # candidates 파일 sha256 추가
    if candidates_path.exists():
        candidates_hash = sha256_file(candidates_path)
        candidates_path_str = str(candidates_path.resolve().as_posix())
        source_hashes[candidates_path_str] = candidates_hash
    
    source_paths = []
    baseline_inputs = baseline.get("inputs", {})
    for key, path in baseline_inputs.items():
        if path:
            source_paths.append(str(Path(path).resolve().as_posix()))
    source_paths.append(str(candidates_path.resolve().as_posix()))
    
    evidence = {
        "baseline_kpis_snapshot": baseline_kpis_snapshot,
        "source_paths": source_paths,
        "source_hashes_sha256": source_hashes
    }
    
    # notes 생성
    notes = candidate.get("notes", {}).copy()
    
    return {
        "policy_id": policy_id,
        "candidate_id": candidate_id,
        "candidate_type": candidate_type,
        "title": candidate.get("title", ""),
        "intent": intent,
        "change_spec": {
            "scope": "EVALUATION_ONLY",
            "proposed_changes": proposed_changes
        },
        "impact_guard": impact_guard,
        "rationale": rationale,
        "evidence": evidence,
        "notes": notes
    }


def generate_policies(
    baseline: Dict[str, Any],
    candidates: Dict[str, Any],
    candidates_path: Path
) -> List[Dict[str, Any]]:
    """
    PolicyDraft 리스트 생성
    
    Args:
        baseline: BaselineV4 데이터
        candidates: CandidateSet 데이터
        candidates_path: candidates 파일 경로
    
    Returns:
        List[Dict]: PolicyDraft 리스트
    """
    policies = []
    candidate_list = candidates.get("candidates", [])
    
    if not candidate_list:
        return policies
    
    # 타입별로 그룹화
    failure_candidates = [c for c in candidate_list if c.get("type") == "FAILURE_AVOID"]
    success_candidates = [c for c in candidate_list if c.get("type") == "SUCCESS_REINFORCE"]
    diversity_candidates = [c for c in candidate_list if c.get("type") == "DIVERSITY_EXPLORE"]
    
    policy_index = 1
    
    # 각 타입에서 최소 1개씩 policy 생성
    # FAILURE_AVOID
    if failure_candidates:
        for candidate in failure_candidates[:2]:  # 최대 2개
            policy = generate_policy_from_candidate(candidate, baseline, policy_index, candidates_path)
            policies.append(policy)
            policy_index += 1
    else:
        # 기본 FAILURE_AVOID policy 생성
        default_candidate = {
            "candidate_id": f"cand_v4_step2:FAILURE_AVOID:default",
            "type": "FAILURE_AVOID",
            "title": "일반적 실패 회피 정책",
            "description": "Baseline KPI를 기반으로 실패 패턴 회피를 고려할 수 있습니다.",
            "based_on": {"kpis": list(baseline.get("kpis", {}).keys())[:3], "signals": []},
            "constraints": {"allowed_scope": ["Step3 정책 엔진에서 고려 가능"]},
            "notes": {"risk": "회피 전략 시 다른 영역 변화 가능", "open_questions": []}
        }
        policy = generate_policy_from_candidate(default_candidate, baseline, policy_index, candidates_path)
        policies.append(policy)
        policy_index += 1
    
    # SUCCESS_REINFORCE
    if success_candidates:
        for candidate in success_candidates[:2]:  # 최대 2개
            policy = generate_policy_from_candidate(candidate, baseline, policy_index, candidates_path)
            policies.append(policy)
            policy_index += 1
    else:
        # 기본 SUCCESS_REINFORCE policy 생성
        default_candidate = {
            "candidate_id": f"cand_v4_step2:SUCCESS_REINFORCE:default",
            "type": "SUCCESS_REINFORCE",
            "title": "일반적 성공 유지 강화 정책",
            "description": "Baseline KPI를 기반으로 성공 패턴 유지·강화를 고려할 수 있습니다.",
            "based_on": {"kpis": list(baseline.get("kpis", {}).keys())[:3], "signals": []},
            "constraints": {"allowed_scope": ["Step3 정책 엔진에서 고려 가능"]},
            "notes": {"risk": "유지 강화 시 다른 영역 변화 가능", "open_questions": []}
        }
        policy = generate_policy_from_candidate(default_candidate, baseline, policy_index, candidates_path)
        policies.append(policy)
        policy_index += 1
    
    # DIVERSITY_EXPLORE
    if diversity_candidates:
        for candidate in diversity_candidates[:2]:  # 최대 2개
            policy = generate_policy_from_candidate(candidate, baseline, policy_index, candidates_path)
            policies.append(policy)
            policy_index += 1
    else:
        # 기본 DIVERSITY_EXPLORE policy 생성
        default_candidate = {
            "candidate_id": f"cand_v4_step2:DIVERSITY_EXPLORE:default",
            "type": "DIVERSITY_EXPLORE",
            "title": "일반적 다양성 탐색 정책",
            "description": "Baseline KPI를 기반으로 다양성 확보를 위한 대안적 시도를 고려할 수 있습니다.",
            "based_on": {"kpis": list(baseline.get("kpis", {}).keys())[:3], "signals": []},
            "constraints": {"allowed_scope": ["Step3 정책 엔진에서 고려 가능"]},
            "notes": {"risk": "다양성 확보 시 안정성 변화 가능", "open_questions": []}
        }
        policy = generate_policy_from_candidate(default_candidate, baseline, policy_index, candidates_path)
        policies.append(policy)
        policy_index += 1
    
    # 최대 7개 제한
    if len(policies) > 7:
        policies = policies[:7]
    
    return policies


def create_policy_draft_set(
    run_id: str,
    baseline: Dict[str, Any],
    candidates: Dict[str, Any],
    policies: List[Dict[str, Any]],
    baseline_path: Path,
    candidates_path: Path
) -> Dict[str, Any]:
    """
    PolicyDraftSet 생성
    
    Args:
        run_id: 실행 ID
        baseline: BaselineV4 데이터
        candidates: CandidateSet 데이터
        policies: PolicyDraft 리스트
        baseline_path: baseline 파일 경로
        candidates_path: candidates 파일 경로
    
    Returns:
        Dict: PolicyDraftSet JSON 데이터
    """
    baseline_path_str = str(baseline_path.resolve().as_posix())
    candidates_path_str = str(candidates_path.resolve().as_posix())
    
    return {
        "run_id": run_id,
        "baseline_ref": {
            "baseline_id": baseline.get("baseline_id", ""),
            "baseline_path": baseline_path_str
        },
        "candidates_ref": {
            "candidates_path": candidates_path_str,
            "candidates_version": "v4_step2"
        },
        "created_at": utc_now_iso(),
        "policies": policies,
        "notes": {
            "warnings": []
        },
        "version": "v4_step3",
        "state": "POLICY_DRAFT_ONLY"
    }


def generate_policy_draft_set(
    run_id: str,
    project_root: Optional[Path] = None
) -> tuple[Optional[Dict[str, Any]], Optional[str]]:
    """
    PolicyDraftSet 생성 (전체 프로세스)
    
    Args:
        run_id: 실행 ID
        project_root: 프로젝트 루트 경로
    
    Returns:
        Tuple[Optional[Dict], Optional[str]]: (policy_draft_set, error_message)
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
    
    # Candidates 검증
    if candidates.get("version") != "v4_step2":
        return None, f"Invalid candidates version: {candidates.get('version')} (expected: v4_step2)"
    
    if candidates.get("state") != "CANDIDATES_ONLY":
        return None, f"Invalid candidates state: {candidates.get('state')} (expected: CANDIDATES_ONLY)"
    
    # Policies 생성
    policies = generate_policies(baseline, candidates, candidates_path)
    
    if len(policies) < 3:
        return None, f"Insufficient policies generated: {len(policies)} (minimum: 3)"
    
    # PolicyDraftSet 생성
    policy_draft_set = create_policy_draft_set(
        run_id, baseline, candidates, policies, baseline_path, candidates_path
    )
    
    return policy_draft_set, None

