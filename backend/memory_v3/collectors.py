"""
MemorySnapshotV3 데이터 수집 로직

기능:
- 기존 run 산출물로부터 관측 데이터 수집
- Reference-only (읽기 전용)
- 생성 파이프라인 영향 금지
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple

from backend.utils.run_manager import get_runs_root, get_run_dir, load_run_manifest
from backend.memory_v3.schema import MemorySnapshotV3, missing_dict, utc_now_iso


def resolve_step5_report_path(run_id: str, manifest: Dict[str, Any], run_dir: Path) -> Optional[Path]:
    """
    step5_report.json 경로 해결
    
    우선순위:
    1) manifest.steps.step5.artifacts.step5_report
    2) run_dir/verify/step5_report.json
    3) run_dir/step5/step5_report.json
    
    Args:
        run_id: 실행 ID
        manifest: run manifest
        run_dir: run 디렉토리
    
    Returns:
        Optional[Path]: step5_report.json 경로 (없으면 None)
    """
    # 1) manifest.steps.step5.artifacts.step5_report
    if manifest:
        steps = manifest.get("steps", {})
        step5 = steps.get("step5", {})
        artifacts = step5.get("artifacts", {})
        if isinstance(artifacts, dict):
            step5_report_path_str = artifacts.get("step5_report")
            if step5_report_path_str:
                if isinstance(step5_report_path_str, str):
                    if Path(step5_report_path_str).is_absolute():
                        path = Path(step5_report_path_str)
                    else:
                        # 상대경로면 run_dir 기준
                        path = run_dir / step5_report_path_str
                    if path.exists():
                        return path
    
    # 2) run_dir/verify/step5_report.json
    path = run_dir / "verify" / "step5_report.json"
    if path.exists():
        return path
    
    # 3) run_dir/step5/step5_report.json
    path = run_dir / "step5" / "step5_report.json"
    if path.exists():
        return path
    
    return None


def resolve_metrics_path(run_dir: Path) -> Optional[Path]:
    """
    metrics.json 경로 해결
    
    우선순위:
    1) run_dir/logs/metrics.json
    2) run_dir/metrics.json
    3) run_dir/step7/metrics.json
    4) run_dir/verify/metrics.json
    
    Args:
        run_dir: run 디렉토리
    
    Returns:
        Optional[Path]: metrics.json 경로 (없으면 None)
    """
    # 1) run_dir/logs/metrics.json
    path = run_dir / "logs" / "metrics.json"
    if path.exists():
        return path
    
    # 2) run_dir/metrics.json
    path = run_dir / "metrics.json"
    if path.exists():
        return path
    
    # 3) run_dir/step7/metrics.json
    path = run_dir / "step7" / "metrics.json"
    if path.exists():
        return path
    
    # 4) run_dir/verify/metrics.json
    path = run_dir / "verify" / "metrics.json"
    if path.exists():
        return path
    
    return None


def resolve_structure_path(run_id: str, run_dir: Path) -> Optional[Path]:
    """
    structure 파일 경로 해결
    
    우선순위:
    1) run_dir/step3/scenes_fixed.json
    2) run_dir/step3/scenes.json
    3) backend/output/plans/<run_id>.json
    
    Args:
        run_id: 실행 ID
        run_dir: run 디렉토리
    
    Returns:
        Optional[Path]: structure 파일 경로 (없으면 None)
    """
    # 1) run_dir/step3/scenes_fixed.json
    path = run_dir / "step3" / "scenes_fixed.json"
    if path.exists():
        return path
    
    # 2) run_dir/step3/scenes.json
    path = run_dir / "step3" / "scenes.json"
    if path.exists():
        return path
    
    # 3) backend/output/plans/<run_id>.json
    from backend.utils.run_manager import get_project_root
    project_root = get_project_root()
    path = project_root / "backend" / "output" / "plans" / f"{run_id}.json"
    if path.exists():
        return path
    
    return None


def resolve_plan_path(run_id: str) -> Optional[Path]:
    """
    plan 파일 경로 해결
    
    Args:
        run_id: 실행 ID
    
    Returns:
        Optional[Path]: plan 파일 경로 (없으면 None)
    """
    from backend.utils.run_manager import get_project_root
    project_root = get_project_root()
    path = project_root / "backend" / "output" / "plans" / f"{run_id}.json"
    if path.exists():
        return path
    
    return None


def collect_source_paths(run_id: str, manifest: Dict[str, Any], run_dir: Path) -> Dict[str, Any]:
    """
    source_paths 수집
    
    Args:
        run_id: 실행 ID
        manifest: run manifest
        run_dir: run 디렉토리
    
    Returns:
        Dict: source_paths 데이터
    """
    manifest_path = run_dir / "manifest.json"
    step5_report_path = resolve_step5_report_path(run_id, manifest, run_dir)
    metrics_path = resolve_metrics_path(run_dir)
    structure_path = resolve_structure_path(run_id, run_dir)
    plan_path = resolve_plan_path(run_id)
    
    return {
        "manifest": str(manifest_path.resolve()) if manifest_path.exists() else None,
        "step5_report": str(step5_report_path.resolve()) if step5_report_path else None,
        "metrics": str(metrics_path.resolve()) if metrics_path else None,
        "structure": str(structure_path.resolve()) if structure_path else None,
        "plan": str(plan_path.resolve()) if plan_path else None
    }


def collect_run_state(manifest: Dict[str, Any]) -> Dict[str, Any]:
    """
    run_state 수집
    
    Args:
        manifest: run manifest
    
    Returns:
        Dict: run_state 데이터
    """
    if not manifest:
        return missing_dict("manifest_missing")
    
    return {
        "run_id": manifest.get("run_id", "missing"),
        "created_at": manifest.get("created_at", "missing"),
        "schema_version": manifest.get("schema_version", "missing"),
        "status": manifest.get("status", "missing")
    }


def collect_step_status_map(manifest: Dict[str, Any]) -> Dict[str, Any]:
    """
    step_status_map 수집
    
    Args:
        manifest: run manifest
    
    Returns:
        Dict: step_status_map 데이터
    """
    if not manifest:
        return missing_dict("manifest_missing")
    
    steps = manifest.get("steps", {})
    step_status_map = {}
    
    for step_name in ["step1", "step2", "step3", "step4", "step5", "step6", "step7", "step8", "step12"]:
        step_data = steps.get(step_name, {})
        step_status = step_data.get("status", "missing")
        step_status_map[step_name] = step_status
    
    return step_status_map


def collect_artifacts_index(manifest: Dict[str, Any], run_dir: Path) -> Dict[str, Any]:
    """
    artifacts_index 수집
    
    Args:
        manifest: run manifest
        run_dir: run 디렉토리
    
    Returns:
        Dict: artifacts_index 데이터
    """
    if not manifest:
        return missing_dict("manifest_missing")
    
    steps = manifest.get("steps", {})
    artifacts_index = {}
    
    for step_name in ["step1", "step2", "step3", "step4", "step5", "step6", "step7", "step8", "step12"]:
        step_data = steps.get(step_name, {})
        artifacts = step_data.get("artifacts", {})
        if isinstance(artifacts, dict):
            artifacts_index[step_name] = artifacts
        else:
            artifacts_index[step_name] = {}
    
    return artifacts_index


def collect_verify_summary(step5_report_path: Optional[Path]) -> Dict[str, Any]:
    """
    verify_summary 수집
    
    Args:
        step5_report_path: step5_report.json 경로
    
    Returns:
        Dict: verify_summary 데이터
    """
    if not step5_report_path or not step5_report_path.exists():
        return missing_dict("step5_report_file_missing")
    
    try:
        with open(step5_report_path, "r", encoding="utf-8") as f:
            step5_report = json.load(f)
        
        return {
            "pass": step5_report.get("pass", False),
            "failures": step5_report.get("failures", []),
            "classification": step5_report.get("classification", {}),
            "data_signals": step5_report.get("data_signals", {})
        }
    except Exception as e:
        return missing_dict(f"step5_report_load_error: {str(e)}")


def collect_metrics_summary(metrics_path: Optional[Path]) -> Dict[str, Any]:
    """
    metrics_summary 수집
    
    Args:
        metrics_path: metrics.json 경로
    
    Returns:
        Dict: metrics_summary 데이터
    """
    if not metrics_path or not metrics_path.exists():
        return missing_dict("metrics_file_missing")
    
    try:
        with open(metrics_path, "r", encoding="utf-8") as f:
            metrics = json.load(f)
        
        return {
            "total_duration_ms": metrics.get("total_duration_ms", 0),
            "scenes_count": metrics.get("scenes_count", 0),
            "rendered_videos_count": metrics.get("rendered_videos_count", 0),
            "scene_retry_regenerate_count": metrics.get("scene_retry_regenerate_count", 0),
            "scene_retry_render_count": metrics.get("scene_retry_render_count", 0),
            "scene_lock_count": metrics.get("scene_lock_count", 0),
            "human_intervention_count": metrics.get("human_intervention_count", 0),
            "decision_trace_count": metrics.get("decision_trace_count", 0),
            "silence_signal_count": metrics.get("silence_signal_count", 0)
        }
    except Exception as e:
        return missing_dict(f"metrics_load_error: {str(e)}")


def collect_structure_summary(structure_path: Optional[Path]) -> Dict[str, Any]:
    """
    structure_summary 수집
    
    Args:
        structure_path: structure 파일 경로
    
    Returns:
        Dict: structure_summary 데이터
    """
    if not structure_path or not structure_path.exists():
        return missing_dict("structure_file_missing")
    
    try:
        with open(structure_path, "r", encoding="utf-8") as f:
            structure_data = json.load(f)
        
        # scenes_fixed.json 또는 scenes.json 형식
        scenes = structure_data.get("scenes", [])
        
        return {
            "scenes_count": len(scenes),
            "total_duration_sec": sum(s.get("duration_sec", 0) for s in scenes if isinstance(s, dict)),
            "structure_type": "scenes_fixed" if "scenes_fixed" in str(structure_path) else "scenes"
        }
    except Exception as e:
        return missing_dict(f"structure_load_error: {str(e)}")


def collect_tags(manifest: Dict[str, Any], verify_summary: Dict[str, Any]) -> List[str]:
    """
    tags 수집
    
    Args:
        manifest: run manifest
        verify_summary: verify_summary 데이터
    
    Returns:
        List[str]: tags 리스트
    """
    tags = []
    
    # manifest에서 tags 추출
    if manifest:
        manifest_tags = manifest.get("tags", [])
        if isinstance(manifest_tags, list):
            tags.extend(manifest_tags)
    
    # verify_summary에서 classification 추출
    if isinstance(verify_summary, dict) and verify_summary.get("status") != "missing":
        classification = verify_summary.get("classification", {})
        if isinstance(classification, dict):
            secondary_tags = classification.get("secondary_tags", [])
            if isinstance(secondary_tags, list):
                tags.extend(secondary_tags)
    
    # 중복 제거 (순서 유지)
    seen = set()
    unique_tags = []
    for tag in tags:
        if tag not in seen:
            seen.add(tag)
            unique_tags.append(tag)
    
    return unique_tags


def collect_questions_seed(verify_summary: Dict[str, Any], structure_summary: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    questions_seed 수집
    
    Args:
        verify_summary: verify_summary 데이터
        structure_summary: structure_summary 데이터
    
    Returns:
        List[Dict]: questions_seed 리스트
    """
    questions = []
    
    # verify_summary에서 valuable_failure 추출
    if isinstance(verify_summary, dict) and verify_summary.get("status") != "missing":
        valuable_failure = verify_summary.get("classification", {}).get("valuable_failure", False)
        valuable_reason = verify_summary.get("classification", {}).get("valuable_reason")
        
        if valuable_failure and valuable_reason:
            questions.append({
                "type": "failure_analysis",
                "question": f"Why did this run fail? {valuable_reason}",
                "context": "verify_summary"
            })
    
    # structure_summary에서 scenes_count 기반 질문
    if isinstance(structure_summary, dict) and structure_summary.get("status") != "missing":
        scenes_count = structure_summary.get("scenes_count", 0)
        if scenes_count > 0:
            questions.append({
                "type": "structure_analysis",
                "question": f"How many scenes were generated? {scenes_count}",
                "context": "structure_summary"
            })
    
    return questions


def collect_snapshot(run_id: str, base_dir: Optional[Path] = None) -> Tuple[Optional[MemorySnapshotV3], Optional[str]]:
    """
    MemorySnapshotV3 수집
    
    Args:
        run_id: 실행 ID
        base_dir: 기본 디렉토리
    
    Returns:
        Tuple[MemorySnapshotV3, Optional[str]]: (snapshot, error_message)
    """
    # runs_root 확인
    runs_root = get_runs_root(base_dir)
    run_dir = get_run_dir(run_id, base_dir)
    manifest_path = run_dir / "manifest.json"
    
    # manifest.json 필수 확인 (없으면 FAIL)
    if not manifest_path.exists():
        error_msg = f"manifest.json not found: {manifest_path.resolve()}"
        return None, error_msg
    
    # manifest 로드
    manifest = load_run_manifest(run_id, base_dir)
    if manifest is None:
        error_msg = f"manifest.json load failed: {manifest_path.resolve()}"
        return None, error_msg
    
    # source_paths 수집
    source_paths = collect_source_paths(run_id, manifest, run_dir)
    step5_report_path = Path(source_paths["step5_report"]) if source_paths.get("step5_report") else None
    metrics_path = Path(source_paths["metrics"]) if source_paths.get("metrics") else None
    structure_path = Path(source_paths["structure"]) if source_paths.get("structure") else None
    
    # 각 섹션 수집
    run_state = collect_run_state(manifest)
    step_status_map = collect_step_status_map(manifest)
    artifacts_index = collect_artifacts_index(manifest, run_dir)
    verify_summary = collect_verify_summary(step5_report_path)
    metrics_summary = collect_metrics_summary(metrics_path)
    structure_summary = collect_structure_summary(structure_path)
    tags = collect_tags(manifest, verify_summary)
    questions_seed = collect_questions_seed(verify_summary, structure_summary)
    
    # MemorySnapshotV3 생성
    snapshot = MemorySnapshotV3(
        run_id=run_id,
        collected_at=utc_now_iso(),
        source_paths=source_paths,
        run_state=run_state,
        step_status_map=step_status_map,
        artifacts_index=artifacts_index,
        verify_summary=verify_summary,
        metrics_summary=metrics_summary,
        structure_summary=structure_summary,
        tags=tags,
        questions_seed=questions_seed,
        memory_version="v3_step1",
        state="ACTIVE"
    )
    
    return snapshot, None

