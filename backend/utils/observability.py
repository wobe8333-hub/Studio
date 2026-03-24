"""
Observability - 관측 로그

처음문서_v1.2 기준:
"관측은 비교 가능하고, 누적 가능해야 한다."
"""

import json
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime

from backend.utils.run_manager import get_run_dir


def write_event(run_id: str, event_type: str, data: Dict[str, Any], base_dir: Optional[Path] = None) -> None:
    """
    이벤트를 events.jsonl에 기록
    
    Args:
        run_id: 실행 ID
        event_type: 이벤트 타입
        data: 이벤트 데이터
        base_dir: 기본 디렉토리
    """
    run_dir = get_run_dir(run_id, base_dir)
    logs_dir = run_dir / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    
    events_path = logs_dir / "events.jsonl"
    
    event = {
        "timestamp": datetime.now().isoformat(),
        "type": event_type,
        "data": data
    }
    
    with open(events_path, "a", encoding="utf-8", newline="\n") as f:
        json_line = json.dumps(event, ensure_ascii=False, separators=(",", ":"))
        f.write(json_line + "\n")


def update_metrics(
    run_id: str,
    metrics: Dict[str, Any],
    base_dir: Optional[Path] = None
) -> Path:
    """
    metrics.json 업데이트
    
    Args:
        run_id: 실행 ID
        metrics: 메트릭 데이터
        base_dir: 기본 디렉토리
    
    Returns:
        Path: metrics.json 경로
    """
    run_dir = get_run_dir(run_id, base_dir)
    logs_dir = run_dir / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    
    metrics_path = logs_dir / "metrics.json"
    
    # 기존 metrics 로드
    existing_metrics = {}
    if metrics_path.exists():
        try:
            with open(metrics_path, "r", encoding="utf-8") as f:
                existing_metrics = json.load(f)
        except Exception:
            pass
    
    # 병합
    existing_metrics.update(metrics)
    existing_metrics["last_updated"] = datetime.now().isoformat()
    
    # 저장
    with open(metrics_path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(existing_metrics, f, ensure_ascii=False, indent=2)
    
    return metrics_path


def write_trace(
    run_id: str,
    step_name: str,
    artifact_path: str,
    base_dir: Optional[Path] = None
) -> None:
    """
    trace.jsonl에 run↔artifact 연결 기록
    
    Args:
        run_id: 실행 ID
        step_name: step 이름
        artifact_path: artifact 경로
        base_dir: 기본 디렉토리
    """
    run_dir = get_run_dir(run_id, base_dir)
    logs_dir = run_dir / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    
    trace_path = logs_dir / "trace.jsonl"
    
    trace = {
        "timestamp": datetime.now().isoformat(),
        "run_id": run_id,
        "step": step_name,
        "artifact": artifact_path
    }
    
    with open(trace_path, "a", encoding="utf-8", newline="\n") as f:
        json_line = json.dumps(trace, ensure_ascii=False, separators=(",", ":"))
        f.write(json_line + "\n")


def ensure_metrics(run_id: str, base_dir: Optional[Path] = None) -> Dict[str, Any]:
    """
    필수 메트릭 백필
    
    Args:
        run_id: 실행 ID
        base_dir: 기본 디렉토리
    
    Returns:
        Dict: metrics 데이터
    """
    run_dir = get_run_dir(run_id, base_dir)
    logs_dir = run_dir / "logs"
    metrics_path = logs_dir / "metrics.json"
    
    # 기존 metrics 로드
    metrics = {}
    if metrics_path.exists():
        try:
            with open(metrics_path, "r", encoding="utf-8") as f:
                metrics = json.load(f)
        except Exception:
            pass
    
    # 필수 키 백필
    required_keys = {
        "total_duration_ms": 0,
        "step5_verify_ms": 0,
        "scenes_count": 0,
        "rendered_videos_count": 0,
        # v1.4 Step6: scene retry 메트릭
        "scene_retry_regenerate_count": 0,
        "scene_retry_render_count": 0,
        # v1.4 Step7: process quality 메트릭
        "scene_lock_count": 0,
        "human_intervention_count": 0,
        "decision_trace_count": 0,
        "silence_signal_count": 0
    }
    
    for key, default_value in required_keys.items():
        if key not in metrics:
            metrics[key] = default_value
    
    # 저장
    if metrics_path.exists() or any(k not in metrics for k in required_keys):
        update_metrics(run_id, metrics, base_dir)
    
    return metrics


def update_bias(
    run_id: str,
    topic_tags: Dict[str, int],
    tone_tags: Dict[str, int],
    base_dir: Optional[Path] = None
) -> None:
    """
    누적 편향 요약 업데이트 (v1.4 Step7)
    
    Args:
        run_id: 실행 ID
        topic_tags: 주제 태그별 카운트 (예: {"technology": 5, "business": 3})
        tone_tags: 톤 태그별 카운트 (예: {"positive": 8, "neutral": 2})
        base_dir: 기본 디렉토리
    """
    run_dir = get_run_dir(run_id, base_dir)
    logs_dir = run_dir / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    
    bias_path = logs_dir / "bias.json"
    
    # 기존 bias 로드
    bias_data = {
        "updated_at": datetime.now().isoformat(),
        "topic_tags": {},
        "tone_tags": {}
    }
    if bias_path.exists():
        try:
            with open(bias_path, "r", encoding="utf-8") as f:
                existing_bias = json.load(f)
                bias_data["topic_tags"] = existing_bias.get("topic_tags", {})
                bias_data["tone_tags"] = existing_bias.get("tone_tags", {})
        except Exception:
            pass
    
    # 누적 업데이트 (기존 값에 더하기)
    for tag, count in topic_tags.items():
        bias_data["topic_tags"][tag] = bias_data["topic_tags"].get(tag, 0) + count
    
    for tag, count in tone_tags.items():
        bias_data["tone_tags"][tag] = bias_data["tone_tags"].get(tag, 0) + count
    
    bias_data["updated_at"] = datetime.now().isoformat()
    
    # 저장
    with open(bias_path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(bias_data, f, ensure_ascii=False, indent=2)


def append_forgetting_ledger(
    run_id: str,
    entry: Dict[str, Any],
    base_dir: Optional[Path] = None
) -> None:
    """
    의도적 망각 기록 추가 (v1.4 Step7)
    
    Args:
        run_id: 실행 ID
        entry: 망각 이벤트 데이터
        base_dir: 기본 디렉토리
    """
    run_dir = get_run_dir(run_id, base_dir)
    logs_dir = run_dir / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    
    ledger_path = logs_dir / "forgetting_ledger.jsonl"
    
    # entry에 타임스탬프 추가
    ledger_entry = {
        "timestamp": datetime.now().isoformat(),
        **entry
    }
    
    # JSONL 형식으로 append
    with open(ledger_path, "a", encoding="utf-8", newline="\n") as f:
        json_line = json.dumps(ledger_entry, ensure_ascii=False, separators=(",", ":"))
        f.write(json_line + "\n")


def record_silence_signal(
    run_id: str,
    reason: str,
    base_dir: Optional[Path] = None
) -> None:
    """
    침묵 신호 기록 (v1.4 Step7)
    
    Args:
        run_id: 실행 ID
        reason: 침묵 신호 이유
        base_dir: 기본 디렉토리
    """
    # 이벤트 로그에 기록
    write_event(
        run_id,
        "silence_signal",
        {
            "reason": reason,
            "run_id": run_id
        },
        base_dir
    )
    
    # 메트릭 업데이트
    metrics = ensure_metrics(run_id, base_dir)
    metrics["silence_signal_count"] = metrics.get("silence_signal_count", 0) + 1
    update_metrics(run_id, metrics, base_dir)

