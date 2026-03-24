"""
MemorySnapshotV3 노화/망각 관리 로직

v3-Step4: v3-Step1/2/3 산출물을 기반으로 노화/망각 관리 수행
- 메모리 객체의 상태 전이 + forgetting ledger 기록
- 정책 기반 결정적 상태 계산
- Reference-only
"""

import json
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone


def utc_now_iso() -> str:
    """UTC 현재 시간을 ISO8601 형식으로 반환"""
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def parse_iso_utc(iso_str: str) -> datetime:
    """
    ISO8601 문자열을 UTC datetime으로 파싱
    
    Args:
        iso_str: ISO8601 형식 문자열 (예: "2024-01-01T00:00:00Z")
    
    Returns:
        datetime: UTC timezone을 가진 datetime 객체
    """
    # Z를 +00:00로 변환
    if iso_str.endswith("Z"):
        iso_str = iso_str[:-1] + "+00:00"
    
    # ISO 형식 파싱
    dt = datetime.fromisoformat(iso_str)
    
    # UTC로 변환
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    else:
        dt = dt.astimezone(timezone.utc)
    
    return dt


def calculate_state(
    collected_at: str,
    valuable_failure: Optional[bool],
    deprecated_after_days: int = 30,
    archived_after_days: int = 90
) -> tuple[str, float, Dict[str, Any]]:
    """
    상태 계산 (정책 기반)
    
    Args:
        collected_at: Step1 snapshot의 collected_at (ISO8601 UTC)
        valuable_failure: verify_summary.classification.valuable_failure 값
        deprecated_after_days: DEPRECATED 임계값 (일)
        archived_after_days: ARCHIVED 임계값 (일)
    
    Returns:
        Tuple[str, float, Dict]: (new_state, age_days, reason_dict)
    """
    now_utc = datetime.now(timezone.utc)
    last_collected_at = parse_iso_utc(collected_at)
    
    age_seconds = (now_utc - last_collected_at).total_seconds()
    age_days = age_seconds / 86400.0
    
    # 기본 상태 계산
    if age_days >= archived_after_days:
        new_state = "ARCHIVED"
    elif age_days >= deprecated_after_days:
        new_state = "DEPRECATED"
    else:
        new_state = "ACTIVE"
    
    # valuable_failure 보호 규칙
    valuable_failure_protect_applied = False
    if valuable_failure is True:
        if new_state == "ARCHIVED":
            new_state = "DEPRECATED"
            valuable_failure_protect_applied = True
    
    reason = {
        "age_days": age_days,
        "thresholds": {
            "deprecated_after_days": deprecated_after_days,
            "archived_after_days": archived_after_days
        },
        "valuable_failure_protect_applied": valuable_failure_protect_applied
    }
    
    return new_state, age_days, reason


def load_previous_state(state_summary_path: Path) -> Optional[str]:
    """
    이전 상태 로드
    
    Args:
        state_summary_path: state_summary.json 경로
    
    Returns:
        Optional[str]: 이전 상태 (없으면 None)
    """
    if not state_summary_path.exists():
        return None
    
    try:
        with open(state_summary_path, "r", encoding="utf-8") as f:
            state_summary = json.load(f)
        return state_summary.get("state")
    except Exception:
        return None


def find_forgetting_candidates(indexed_dir: Path) -> List[Dict[str, Any]]:
    """
    forgetting 후보 찾기 (임시 파일만)
    
    Args:
        indexed_dir: indexed/<run_id>/ 디렉토리
    
    Returns:
        List[Dict]: forgetting 후보 리스트
    """
    candidates = []
    
    if not indexed_dir.exists():
        return candidates
    
    # 임시 파일 패턴: *.a, *.b, *.tmp
    temp_patterns = ["*.a", "*.b", "*.tmp"]
    
    for pattern in temp_patterns:
        for filepath in indexed_dir.glob(pattern):
            if filepath.is_file():
                candidates.append({
                    "kind": "temp_artifact",
                    "path": str(filepath.resolve()),
                    "rationale": f"Temporary comparison file: {filepath.name}",
                    "safe_to_forget": False
                })
    
    return candidates


def create_policy() -> Dict[str, Any]:
    """
    policy_v3_step4.json 생성
    
    Returns:
        Dict: 정책 데이터
    """
    return {
        "version": "v3_step4",
        "deprecated_after_days": 30,
        "archived_after_days": 90,
        "valuable_failure_protect_rule": "no-archive-if-valuable-failure",
        "reference_only": True
    }


def append_state_ledger(
    ledger_path: Path,
    run_id: str,
    prev_state: Optional[str],
    new_state: str,
    reason: Dict[str, Any],
    snapshot_path: Path,
    indexed_path: Path,
    normalized_path: Path
) -> None:
    """
    state_ledger.jsonl에 레코드 추가
    
    Args:
        ledger_path: state_ledger.jsonl 경로
        run_id: 실행 ID
        prev_state: 이전 상태
        new_state: 새 상태
        reason: 이유 dict
        snapshot_path: Step1 snapshot 경로
        indexed_path: Step3 indexed 디렉토리 경로
        normalized_path: Step2 normalized 디렉토리 경로
    """
    event_at = utc_now_iso()
    
    record = {
        "run_id": run_id,
        "event_at": event_at,
        "prev_state": prev_state,
        "new_state": new_state,
        "reason": reason,
        "inputs": {
            "snapshot_path": str(snapshot_path.resolve()),
            "indexed_path": str(indexed_path.resolve()),
            "normalized_path": str(normalized_path.resolve())
        },
        "reference_only": True
    }
    
    # JSONL 형식으로 append (한 줄 = 한 레코드)
    with open(ledger_path, "a", encoding="utf-8", newline="\n") as f:
        json_str = json.dumps(record, ensure_ascii=False)
        f.write(json_str + "\n")


def append_forgetting_ledger(
    ledger_path: Path,
    run_id: str,
    state_at_event: str,
    candidates: List[Dict[str, Any]]
) -> None:
    """
    forgetting_ledger.jsonl에 레코드 추가
    
    Args:
        ledger_path: forgetting_ledger.jsonl 경로
        run_id: 실행 ID
        state_at_event: 이벤트 시점의 상태
        candidates: forgetting 후보 리스트
    """
    if not candidates:
        # 후보가 없으면 레코드를 추가하지 않음 (0줄이어도 됨)
        return
    
    event_at = utc_now_iso()
    
    for candidate in candidates:
        record = {
            "run_id": run_id,
            "event_at": event_at,
            "state_at_event": state_at_event,
            "candidate": candidate,
            "reference_only": True
        }
        
        # JSONL 형식으로 append
        with open(ledger_path, "a", encoding="utf-8", newline="\n") as f:
            json_str = json.dumps(record, ensure_ascii=False)
            f.write(json_str + "\n")


def write_state_summary(
    summary_path: Path,
    run_id: str,
    state: str,
    age_days: float,
    last_collected_at: str,
    deprecated_after_days: int,
    archived_after_days: int
) -> None:
    """
    state_summary.json 작성
    
    Args:
        summary_path: state_summary.json 경로
        run_id: 실행 ID
        state: 현재 상태
        age_days: 나이 (일)
        last_collected_at: 마지막 수집 시각 (ISO8601)
        deprecated_after_days: DEPRECATED 임계값
        archived_after_days: ARCHIVED 임계값
    """
    updated_at = utc_now_iso()
    
    summary = {
        "run_id": run_id,
        "updated_at": updated_at,
        "state": state,
        "age_days": age_days,
        "last_collected_at": last_collected_at,
        "policy": {
            "deprecated_after_days": deprecated_after_days,
            "archived_after_days": archived_after_days,
            "valuable_failure_protect_rule": "no-archive-if-valuable-failure"
        },
        "reference_only": True
    }
    
    with open(summary_path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)


def create_governance_index(
    index_path: Path,
    run_id: str,
    governed_at: str
) -> None:
    """
    governance_index.json 생성
    
    Args:
        index_path: governance_index.json 경로
        run_id: 실행 ID
        governed_at: governance 실행 시각 (ISO8601)
    """
    index = {
        "run_id": run_id,
        "step": "v3_step4",
        "governed_at": governed_at,
        "files": {
            "policy": "policy_v3_step4.json",
            "state_ledger": "state_ledger.jsonl",
            "state_summary": "state_summary.json",
            "forgetting_ledger": "forgetting_ledger.jsonl",
            "governance_index": "governance_index.json"
        }
    }
    
    with open(index_path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(index, f, ensure_ascii=False, indent=2)


def govern_memory(
    run_id: str,
    snapshot_path: Path,
    normalized_dir: Path,
    indexed_dir: Path,
    output_dir: Path,
    deprecated_after_days: int = 30,
    archived_after_days: int = 90
) -> Optional[str]:
    """
    v3-Step4 메모리 노화/망각 관리 실행
    
    Args:
        run_id: 실행 ID
        snapshot_path: Step1 snapshot 경로
        normalized_dir: Step2 normalized 디렉토리
        indexed_dir: Step3 indexed 디렉토리
        output_dir: Step4 출력 디렉토리 (governance/<run_id>/)
        deprecated_after_days: DEPRECATED 임계값
        archived_after_days: ARCHIVED 임계값
    
    Returns:
        Optional[str]: error_message (성공 시 None)
    """
    # 출력 디렉토리 생성
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # 필수 입력 파일 확인
    if not snapshot_path.exists():
        return f"Step1 snapshot not found: {snapshot_path.resolve()}"
    
    if not normalized_dir.exists():
        return f"Step2 normalized directory not found: {normalized_dir.resolve()}"
    
    if not indexed_dir.exists():
        return f"Step3 indexed directory not found: {indexed_dir.resolve()}"
    
    # Step1 snapshot 로드
    try:
        with open(snapshot_path, "r", encoding="utf-8") as f:
            snapshot = json.load(f)
    except Exception as e:
        return f"Failed to load snapshot: {str(e)}"
    
    # collected_at 추출
    collected_at = snapshot.get("collected_at")
    if not collected_at:
        return "snapshot.collected_at is missing"
    
    # valuable_failure 추출
    verify_summary = snapshot.get("verify_summary", {})
    classification = verify_summary.get("classification", {}) if isinstance(verify_summary, dict) else {}
    valuable_failure = classification.get("valuable_failure") if isinstance(classification, dict) else None
    
    # 상태 계산
    new_state, age_days, reason = calculate_state(
        collected_at,
        valuable_failure,
        deprecated_after_days,
        archived_after_days
    )
    
    # 이전 상태 로드
    state_summary_path = output_dir / "state_summary.json"
    prev_state = load_previous_state(state_summary_path)
    
    # 1) policy_v3_step4.json 생성
    try:
        policy = create_policy()
        policy_path = output_dir / "policy_v3_step4.json"
        with open(policy_path, "w", encoding="utf-8", newline="\n") as f:
            json.dump(policy, f, ensure_ascii=False, indent=2)
        print("POLICY_WRITTEN")
    except Exception as e:
        return f"Failed to create policy_v3_step4.json: {str(e)}"
    
    # 2) state_ledger.jsonl에 레코드 추가
    try:
        ledger_path = output_dir / "state_ledger.jsonl"
        append_state_ledger(
            ledger_path,
            run_id,
            prev_state,
            new_state,
            reason,
            snapshot_path,
            indexed_dir,
            normalized_dir
        )
        print("STATE_LEDGER_APPENDED")
    except Exception as e:
        return f"Failed to append state_ledger: {str(e)}"
    
    # 3) state_summary.json 작성
    try:
        write_state_summary(
            state_summary_path,
            run_id,
            new_state,
            age_days,
            collected_at,
            deprecated_after_days,
            archived_after_days
        )
        print("STATE_SUMMARY_WRITTEN")
    except Exception as e:
        return f"Failed to create state_summary.json: {str(e)}"
    
    # 4) forgetting_ledger.jsonl에 레코드 추가
    try:
        forgetting_ledger_path = output_dir / "forgetting_ledger.jsonl"
        candidates = find_forgetting_candidates(indexed_dir)
        if candidates:
            append_forgetting_ledger(
                forgetting_ledger_path,
                run_id,
                new_state,
                candidates
            )
            print("FORGETTING_LEDGER_APPENDED")
        else:
            print("FORGETTING_LEDGER_EMPTY")
    except Exception as e:
        return f"Failed to append forgetting_ledger: {str(e)}"
    
    # 5) governance_index.json 생성
    try:
        index_path = output_dir / "governance_index.json"
        governed_at = utc_now_iso()
        create_governance_index(index_path, run_id, governed_at)
        print("GOVERNANCE_INDEX_WRITTEN")
    except Exception as e:
        return f"Failed to create governance_index.json: {str(e)}"
    
    return None

