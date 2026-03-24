"""
MemorySnapshotV3 정규화 로직

v3-Step2: v3-Step1 스냅샷을 정규화/분해 파생 데이터로 분리 저장
- 원본 보존(immutable) + 정규화 파생 데이터 분리
- 해석/추천/선택/평가 금지
- 기계적 정규화만 수행
"""

import json
import shutil
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime, timezone

from backend.memory_v3.schema import missing_dict


def utc_now_iso() -> str:
    """UTC 현재 시간을 ISO8601 형식으로 반환"""
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def copy_snapshot_raw(snapshot_path: Path, output_dir: Path) -> Path:
    """
    snapshot_raw.json 생성 (원본 완전 복사)
    
    Args:
        snapshot_path: 입력 스냅샷 경로
        output_dir: 출력 디렉토리
    
    Returns:
        Path: 생성된 파일 경로
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    raw_path = output_dir / "snapshot_raw.json"
    
    # 원본을 그대로 복사 (key/순서/값 변경 없이)
    shutil.copy2(snapshot_path, raw_path)
    
    return raw_path


def extract_snapshot_meta(snapshot: Dict[str, Any]) -> Dict[str, Any]:
    """
    snapshot_meta.json 생성 (메타 정보만 추출)
    
    Args:
        snapshot: 스냅샷 데이터
    
    Returns:
        Dict: 메타 정보만 포함한 dict
    """
    meta = {}
    
    # 허용 필드만 기록
    if "run_id" in snapshot:
        meta["run_id"] = snapshot["run_id"]
    if "collected_at" in snapshot:
        meta["collected_at"] = snapshot["collected_at"]
    if "memory_version" in snapshot:
        meta["memory_version"] = snapshot["memory_version"]
    if "state" in snapshot:
        meta["state"] = snapshot["state"]
    
    # schema_version (있을 경우)
    run_state = snapshot.get("run_state", {})
    if isinstance(run_state, dict) and "schema_version" in run_state:
        meta["schema_version"] = run_state["schema_version"]
    
    return meta


def extract_patterns_structure(structure_summary: Dict[str, Any]) -> Dict[str, Any]:
    """
    patterns_structure.json 생성
    
    Args:
        structure_summary: structure_summary 데이터
    
    Returns:
        Dict: 구조 패턴 데이터
    """
    if not isinstance(structure_summary, dict) or structure_summary.get("status") == "missing":
        return missing_dict("structure_summary_missing")
    
    scene_count = structure_summary.get("scenes_count", 0)
    total_duration_sec = structure_summary.get("total_duration_sec", 0)
    
    # 평균/최소/최대 계산
    if scene_count > 0:
        avg_duration_sec = total_duration_sec / scene_count
        durations = []
        # structure_summary에서 개별 씬 duration 추출 불가능하므로 기본값 사용
        min_duration_sec = 0
        max_duration_sec = 0
    else:
        avg_duration_sec = 0
        min_duration_sec = 0
        max_duration_sec = 0
    
    return {
        "scene_count": scene_count,
        "total_duration_sec": total_duration_sec,
        "avg_duration_sec": avg_duration_sec,
        "min_duration_sec": min_duration_sec,
        "max_duration_sec": max_duration_sec
    }


def extract_patterns_verify(verify_summary: Dict[str, Any]) -> Dict[str, Any]:
    """
    patterns_verify.json 생성
    
    Args:
        verify_summary: verify_summary 데이터
    
    Returns:
        Dict: 검증 패턴 데이터
    """
    if not isinstance(verify_summary, dict) or verify_summary.get("status") == "missing":
        return missing_dict("verify_summary_missing")
    
    pass_fail = verify_summary.get("pass", False)
    failures = verify_summary.get("failures", [])
    failure_count = len(failures) if isinstance(failures, list) else 0
    
    # failure_taxonomy 추출 (failures에서 분류)
    failure_taxonomy = []
    if isinstance(failures, list):
        for failure in failures:
            if isinstance(failure, str):
                failure_taxonomy.append(failure)
    
    classification = verify_summary.get("classification", {})
    secondary_tags = classification.get("secondary_tags", []) if isinstance(classification, dict) else []
    valuable_failure = classification.get("valuable_failure", False) if isinstance(classification, dict) else False
    valuable_reason = classification.get("valuable_reason") if isinstance(classification, dict) else None
    
    data_signals = verify_summary.get("data_signals", {})
    
    return {
        "pass_fail": pass_fail,
        "failure_count": failure_count,
        "failure_taxonomy": failure_taxonomy,
        "secondary_tags": secondary_tags,
        "valuable_failure": valuable_failure,
        "valuable_reason": valuable_reason,
        "data_signals": data_signals
    }


def extract_patterns_metrics(metrics_summary: Dict[str, Any]) -> Dict[str, Any]:
    """
    patterns_metrics.json 생성
    
    Args:
        metrics_summary: metrics_summary 데이터
    
    Returns:
        Dict: 메트릭 패턴 데이터
    """
    if not isinstance(metrics_summary, dict) or metrics_summary.get("status") == "missing":
        return missing_dict("metrics_summary_missing")
    
    # 숫자형 필드는 그대로 유지
    patterns = {}
    
    # 허용 필드만 복사
    allowed_fields = [
        "total_duration_ms",
        "scenes_count",
        "rendered_videos_count",
        "scene_retry_regenerate_count",
        "scene_retry_render_count",
        "scene_lock_count",
        "human_intervention_count",
        "decision_trace_count",
        "silence_signal_count"
    ]
    
    for field in allowed_fields:
        if field in metrics_summary:
            patterns[field] = metrics_summary[field]
    
    return patterns


def extract_patterns_tags(tags: list, questions_seed: list) -> Dict[str, Any]:
    """
    patterns_tags.json 생성
    
    Args:
        tags: tags 리스트
        questions_seed: questions_seed 리스트
    
    Returns:
        Dict: 태그 패턴 데이터
    """
    # tags: list 그대로 복사
    tags_copy = tags.copy() if isinstance(tags, list) else []
    
    # questions_seed: text/source/kind/confidence_hint 그대로 복사
    questions_copy = []
    if isinstance(questions_seed, list):
        for q in questions_seed:
            if isinstance(q, dict):
                question_item = {}
                # 허용 필드만 복사
                if "type" in q:
                    question_item["type"] = q["type"]
                if "question" in q:
                    question_item["question"] = q["question"]
                if "context" in q:
                    question_item["context"] = q["context"]
                # text/source/kind/confidence_hint도 복사 (있는 경우)
                for field in ["text", "source", "kind", "confidence_hint"]:
                    if field in q:
                        question_item[field] = q[field]
                questions_copy.append(question_item)
    
    return {
        "tags": tags_copy,
        "questions_seed": questions_copy
    }


def create_index(run_id: str, output_dir: Path) -> Dict[str, Any]:
    """
    index.json 생성
    
    Args:
        run_id: 실행 ID
        output_dir: 출력 디렉토리
    
    Returns:
        Dict: 인덱스 데이터
    """
    normalized_at = utc_now_iso()
    
    # 경로는 normalized/<run_id>/ 기준 상대경로
    files = {
        "snapshot_raw": "snapshot_raw.json",
        "snapshot_meta": "snapshot_meta.json",
        "patterns_structure": "patterns_structure.json",
        "patterns_verify": "patterns_verify.json",
        "patterns_metrics": "patterns_metrics.json",
        "patterns_tags": "patterns_tags.json"
    }
    
    return {
        "run_id": run_id,
        "normalized_at": normalized_at,
        "files": files
    }


def normalize_snapshot(run_id: str, base_dir: Optional[Path] = None) -> tuple[Optional[Path], Optional[str]]:
    """
    MemorySnapshotV3 정규화
    
    Args:
        run_id: 실행 ID
        base_dir: 기본 디렉토리
    
    Returns:
        Tuple[Optional[Path], Optional[str]]: (output_dir, error_message)
    """
    # 입력 스냅샷 경로 확인
    if base_dir is None:
        from backend.utils.run_manager import get_project_root
        project_root = get_project_root()
        snapshots_dir = project_root / "backend" / "output" / "memory_v3" / "snapshots"
    else:
        if base_dir.name == "backend":
            output_dir = base_dir / "output"
        else:
            output_dir = base_dir / "output" if (base_dir / "output").exists() else base_dir
        snapshots_dir = output_dir / "memory_v3" / "snapshots"
    
    snapshot_path = snapshots_dir / f"{run_id}.json"
    
    # 입력 스냅샷 없으면 FAIL
    if not snapshot_path.exists():
        error_msg = f"Input snapshot not found: {snapshot_path.resolve()}"
        return None, error_msg
    
    # 스냅샷 로드
    try:
        with open(snapshot_path, "r", encoding="utf-8") as f:
            snapshot = json.load(f)
    except Exception as e:
        error_msg = f"Failed to load snapshot: {str(e)}"
        return None, error_msg
    
    # 출력 디렉토리 생성
    if base_dir is None:
        from backend.utils.run_manager import get_project_root
        project_root = get_project_root()
        output_base = project_root / "backend" / "output" / "memory_v3" / "normalized"
    else:
        if base_dir.name == "backend":
            output_base = base_dir / "output" / "memory_v3" / "normalized"
        else:
            output_base = base_dir / "output" / "memory_v3" / "normalized" if (base_dir / "output").exists() else base_dir / "memory_v3" / "normalized"
    
    output_dir = output_base / run_id
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # 1) snapshot_raw.json 생성 (원본 완전 복사)
    try:
        copy_snapshot_raw(snapshot_path, output_dir)
    except Exception as e:
        error_msg = f"Failed to copy snapshot_raw: {str(e)}"
        return None, error_msg
    
    # 2) snapshot_meta.json 생성
    try:
        meta = extract_snapshot_meta(snapshot)
        meta_path = output_dir / "snapshot_meta.json"
        with open(meta_path, "w", encoding="utf-8", newline="\n") as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)
    except Exception as e:
        error_msg = f"Failed to create snapshot_meta: {str(e)}"
        return None, error_msg
    
    # 3) patterns_structure.json 생성
    try:
        structure_summary = snapshot.get("structure_summary", {})
        patterns_structure = extract_patterns_structure(structure_summary)
        patterns_structure_path = output_dir / "patterns_structure.json"
        with open(patterns_structure_path, "w", encoding="utf-8", newline="\n") as f:
            json.dump(patterns_structure, f, ensure_ascii=False, indent=2)
    except Exception as e:
        error_msg = f"Failed to create patterns_structure: {str(e)}"
        return None, error_msg
    
    # 4) patterns_verify.json 생성
    try:
        verify_summary = snapshot.get("verify_summary", {})
        patterns_verify = extract_patterns_verify(verify_summary)
        patterns_verify_path = output_dir / "patterns_verify.json"
        with open(patterns_verify_path, "w", encoding="utf-8", newline="\n") as f:
            json.dump(patterns_verify, f, ensure_ascii=False, indent=2)
    except Exception as e:
        error_msg = f"Failed to create patterns_verify: {str(e)}"
        return None, error_msg
    
    # 5) patterns_metrics.json 생성
    try:
        metrics_summary = snapshot.get("metrics_summary", {})
        patterns_metrics = extract_patterns_metrics(metrics_summary)
        patterns_metrics_path = output_dir / "patterns_metrics.json"
        with open(patterns_metrics_path, "w", encoding="utf-8", newline="\n") as f:
            json.dump(patterns_metrics, f, ensure_ascii=False, indent=2)
    except Exception as e:
        error_msg = f"Failed to create patterns_metrics: {str(e)}"
        return None, error_msg
    
    # 6) patterns_tags.json 생성
    try:
        tags = snapshot.get("tags", [])
        questions_seed = snapshot.get("questions_seed", [])
        patterns_tags = extract_patterns_tags(tags, questions_seed)
        patterns_tags_path = output_dir / "patterns_tags.json"
        with open(patterns_tags_path, "w", encoding="utf-8", newline="\n") as f:
            json.dump(patterns_tags, f, ensure_ascii=False, indent=2)
    except Exception as e:
        error_msg = f"Failed to create patterns_tags: {str(e)}"
        return None, error_msg
    
    # 7) index.json 생성
    try:
        index = create_index(run_id, output_dir)
        index_path = output_dir / "index.json"
        with open(index_path, "w", encoding="utf-8", newline="\n") as f:
            json.dump(index, f, ensure_ascii=False, indent=2)
    except Exception as e:
        error_msg = f"Failed to create index: {str(e)}"
        return None, error_msg
    
    return output_dir, None

