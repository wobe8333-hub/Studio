"""
v4-Step1: KPI 평가 + Read-only 무침범 검사

입력: v3 산출물 (Reference-only)
출력: KPI 값 + 증거 (sha256)
"""

import json
import hashlib
from pathlib import Path
from typing import Dict, Any, Optional, Union, List
from datetime import datetime, timezone

from backend.evolution_v4.schema import create_baseline_v4, utc_now_iso


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
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def extract_kpis(snapshot: Dict[str, Any]) -> Dict[str, Union[bool, int, float, str]]:
    """
    KPI 추출 (snapshots/<run_id>.json에서만 추출)
    
    Args:
        snapshot: Step1 snapshot 데이터
    
    Returns:
        Dict: KPI 값 dict
    """
    kpis = {}
    
    verify_summary = snapshot.get("verify_summary", {})
    structure_summary = snapshot.get("structure_summary", {})
    metrics_summary = snapshot.get("metrics_summary", {})
    
    # verify_pass
    if isinstance(verify_summary, dict) and "pass" in verify_summary:
        kpis["verify_pass"] = verify_summary["pass"]
    else:
        kpis["verify_pass"] = "missing"
    
    # failure_count
    if isinstance(verify_summary, dict) and "failures" in verify_summary:
        failures = verify_summary["failures"]
        if isinstance(failures, list):
            kpis["failure_count"] = len(failures)
        else:
            kpis["failure_count"] = "missing"
    else:
        kpis["failure_count"] = "missing"
    
    # has_valuable_failure
    if isinstance(verify_summary, dict) and "classification" in verify_summary:
        classification = verify_summary["classification"]
        if isinstance(classification, dict) and "valuable_failure" in classification:
            kpis["has_valuable_failure"] = classification["valuable_failure"]
        else:
            kpis["has_valuable_failure"] = "missing"
    else:
        kpis["has_valuable_failure"] = "missing"
    
    # scene_count (structure_summary 우선, 없으면 metrics_summary)
    if isinstance(structure_summary, dict) and "scenes_count" in structure_summary:
        kpis["scene_count"] = structure_summary["scenes_count"]
    elif isinstance(metrics_summary, dict) and "scenes_count" in metrics_summary:
        kpis["scene_count"] = metrics_summary["scenes_count"]
    else:
        kpis["scene_count"] = "missing"
    
    # total_duration_sec
    if isinstance(structure_summary, dict) and "total_duration_sec" in structure_summary:
        kpis["total_duration_sec"] = float(structure_summary["total_duration_sec"])
    else:
        kpis["total_duration_sec"] = "missing"
    
    # duration_ms
    if isinstance(metrics_summary, dict) and "total_duration_ms" in metrics_summary:
        kpis["duration_ms"] = int(metrics_summary["total_duration_ms"])
    else:
        kpis["duration_ms"] = "missing"
    
    # retry_regenerate
    if isinstance(metrics_summary, dict) and "scene_retry_regenerate_count" in metrics_summary:
        kpis["retry_regenerate"] = int(metrics_summary["scene_retry_regenerate_count"])
    else:
        kpis["retry_regenerate"] = "missing"
    
    # retry_render
    if isinstance(metrics_summary, dict) and "scene_retry_render_count" in metrics_summary:
        kpis["retry_render"] = int(metrics_summary["scene_retry_render_count"])
    else:
        kpis["retry_render"] = "missing"
    
    # lock_count
    if isinstance(metrics_summary, dict) and "scene_lock_count" in metrics_summary:
        kpis["lock_count"] = int(metrics_summary["scene_lock_count"])
    else:
        kpis["lock_count"] = "missing"
    
    # human_intervention_count
    if isinstance(metrics_summary, dict) and "human_intervention_count" in metrics_summary:
        kpis["human_intervention_count"] = int(metrics_summary["human_intervention_count"])
    else:
        kpis["human_intervention_count"] = "missing"
    
    # decision_trace_count
    if isinstance(metrics_summary, dict) and "decision_trace_count" in metrics_summary:
        kpis["decision_trace_count"] = int(metrics_summary["decision_trace_count"])
    else:
        kpis["decision_trace_count"] = "missing"
    
    # silence_signal_count
    if isinstance(metrics_summary, dict) and "silence_signal_count" in metrics_summary:
        kpis["silence_signal_count"] = int(metrics_summary["silence_signal_count"])
    else:
        kpis["silence_signal_count"] = "missing"
    
    # cost_usd (기본적으로 "missing", snapshot에 키가 없음)
    if isinstance(metrics_summary, dict) and "cost_usd" in metrics_summary:
        kpis["cost_usd"] = float(metrics_summary["cost_usd"])
    else:
        kpis["cost_usd"] = "missing"
    
    return kpis


def evaluate_baseline(
    run_id: str,
    project_root: Optional[Path] = None
) -> tuple[Optional[Dict[str, Any]], Optional[str]]:
    """
    Baseline 평가 (KPI 계산 + 증거 수집)
    
    Args:
        run_id: 실행 ID
        project_root: 프로젝트 루트 경로 (None이면 현재 디렉토리 기준)
    
    Returns:
        Tuple[Optional[Dict], Optional[str]]: (baseline_data, error_message)
    """
    if project_root is None:
        project_root = Path.cwd()
    
    # 입력 경로 설정
    snapshot_path = project_root / "backend" / "output" / "memory_v3" / "snapshots" / f"{run_id}.json"
    normalized_path = project_root / "backend" / "output" / "memory_v3" / "normalized" / run_id / "snapshot_raw.json"
    semantic_index_path = project_root / "backend" / "output" / "memory_v3" / "indexed" / run_id / "semantic_index.json"
    index_path = project_root / "backend" / "output" / "memory_v3" / "indexed" / run_id / "index.json"
    governance_path = project_root / "backend" / "output" / "memory_v3" / "governance" / run_id / "state_summary.json"
    plan_path = project_root / "backend" / "output" / "plans" / f"{run_id}.json"
    
    # Hard fail: snapshot 또는 normalized 없으면 즉시 FAIL
    if not snapshot_path.exists():
        return None, f"Required input not found: {snapshot_path.resolve()}"
    
    if not normalized_path.exists():
        return None, f"Required input not found: {normalized_path.resolve()}"
    
    # 입력 파일 로드
    snapshot = load_json_safe(snapshot_path)
    if snapshot is None:
        return None, f"Failed to load snapshot: {snapshot_path.resolve()}"
    
    # KPI 추출
    kpis = extract_kpis(snapshot)
    
    # 입력 경로 dict 생성 (posix 형식으로 저장)
    inputs = {
        "memory_snapshot_path": snapshot_path.resolve().as_posix(),
        "normalized_raw_path": normalized_path.resolve().as_posix(),
        "semantic_index_path": semantic_index_path.resolve().as_posix() if semantic_index_path.exists() else None,
        "governance_state_summary_path": governance_path.resolve().as_posix() if governance_path.exists() else None,
        "plan_path": plan_path.resolve().as_posix() if plan_path.exists() else None
    }
    
    # semantic_index가 없으면 index.json 허용
    if not semantic_index_path.exists() and index_path.exists():
        inputs["semantic_index_path"] = index_path.resolve().as_posix()
    
    # SHA256 계산 (존재하는 파일만, 키는 posix 형식)
    source_hashes = {}
    input_paths = [
        snapshot_path,
        normalized_path,
        semantic_index_path if semantic_index_path.exists() else index_path if index_path.exists() else None,
        governance_path if governance_path.exists() else None,
        plan_path if plan_path.exists() else None
    ]
    
    for path in input_paths:
        if path and path.exists():
            abs_path_posix = path.resolve().as_posix()
            source_hashes[abs_path_posix] = sha256_file(path)
    
    # notes 생성
    missing_inputs = []
    if not semantic_index_path.exists() and not index_path.exists():
        missing_inputs.append("semantic_index")
    if not governance_path.exists():
        missing_inputs.append("governance_state_summary")
    if not plan_path.exists():
        missing_inputs.append("plan")
    
    notes = {
        "missing_inputs": missing_inputs,
        "warnings": []
    }
    
    # evidence 생성
    evidence = {
        "source_hashes_sha256": source_hashes,
        "read_only_guarantee": True
    }
    
    # Baseline 생성
    baseline = create_baseline_v4(
        run_id=run_id,
        inputs=inputs,
        kpis=kpis,
        evidence=evidence,
        notes=notes
    )
    
    return baseline, None


def verify_read_only(
    baseline: Dict[str, Any],
    project_root: Optional[Path] = None
) -> tuple[bool, Optional[str]]:
    """
    Read-only 무침범 검증
    
    Args:
        baseline: BaselineV4 데이터
        project_root: 프로젝트 루트 경로
    
    Returns:
        Tuple[bool, Optional[str]]: (is_valid, error_message)
    """
    if project_root is None:
        project_root = Path.cwd()
    
    source_hashes = baseline.get("evidence", {}).get("source_hashes_sha256", {})
    
    # 각 경로의 현재 해시 재계산 (posix 경로를 Path로 변환)
    for abs_path_posix, expected_hash in source_hashes.items():
        # posix 경로를 Path로 변환 (Windows에서도 작동)
        path = Path(abs_path_posix)
        if not path.exists():
            return False, f"Input file disappeared: {abs_path_posix}"
        
        current_hash = sha256_file(path)
        if current_hash != expected_hash:
            return False, f"READ ONLY VIOLATION: {abs_path_posix} hash changed (expected: {expected_hash}, got: {current_hash})"
    
    return True, None

