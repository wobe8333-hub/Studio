"""HITL Gate — 사용자 승인/거부 메커니즘.

파이프라인이 영상을 생성한 뒤:
  1. write_review_request()  → hitl_review.json 생성, pipeline 일시 중단
  2. 사용자가 영상 확인 후:
       python -m src.pipeline approve CH1 <run_id>  → 인트로/아웃트로 추가
       python -m src.pipeline reject  CH1 <run_id>  → 처음부터 재생성
"""

from pathlib import Path

from loguru import logger

from src.core.config import KAS_ROOT
from src.core.ssot import get_run_dir, now_iso, read_json, write_json

# HITL 상태값
STATUS_PENDING  = "pending"
STATUS_APPROVED = "approved"
STATUS_REJECTED = "rejected"


def _review_path(run_dir: Path) -> Path:
    return run_dir / "hitl_review.json"


def write_review_request(channel_id: str, run_id: str, video_path: Path) -> None:
    """영상 검토 요청 파일 기록 (pipeline 중단 신호)."""
    run_dir = get_run_dir(channel_id, run_id)
    data = {
        "status":      STATUS_PENDING,
        "channel_id":  channel_id,
        "run_id":      run_id,
        "video_path":  str(video_path),
        "created_at":  now_iso(),
        "reviewed_at": None,
    }
    write_json(_review_path(run_dir), data)

    # 글로벌 알림 등록
    signals_path = KAS_ROOT / "data/global/notifications/hitl_signals.json"
    try:
        signals = read_json(signals_path) if signals_path.exists() else {"pending": []}
        pending = signals.get("pending", [])
        pending.append({"run_id": run_id, "channel_id": channel_id,
                        "type": "video_review", "created_at": now_iso()})
        signals["pending"] = pending
        write_json(signals_path, signals)
    except Exception as e:
        logger.warning(f"[HITL] 글로벌 알림 등록 실패 (비치명): {e}")

    logger.info(
        f"[HITL] {channel_id}/{run_id} 검토 대기 중\n"
        f"       영상 위치: {video_path}\n"
        f"       승인: python -m src.pipeline approve {channel_id} {run_id}\n"
        f"       거부: python -m src.pipeline reject  {channel_id} {run_id}"
    )


def get_review_status(channel_id: str, run_id: str) -> str:
    """pending / approved / rejected — 파일 없으면 'pending' 반환."""
    run_dir = get_run_dir(channel_id, run_id)
    path = _review_path(run_dir)
    if not path.exists():
        return STATUS_PENDING
    return read_json(path).get("status", STATUS_PENDING)


def approve_review(channel_id: str, run_id: str) -> None:
    """사용자 승인 처리."""
    run_dir = get_run_dir(channel_id, run_id)
    path = _review_path(run_dir)
    data = read_json(path) if path.exists() else {}
    data["status"]      = STATUS_APPROVED
    data["reviewed_at"] = now_iso()
    write_json(path, data)
    _remove_from_signals(run_id)
    logger.info(f"[HITL] {channel_id}/{run_id} 승인됨 → 인트로/아웃트로 추가 시작")


def reject_review(channel_id: str, run_id: str) -> None:
    """사용자 거부 처리."""
    run_dir = get_run_dir(channel_id, run_id)
    path = _review_path(run_dir)
    data = read_json(path) if path.exists() else {}
    data["status"]      = STATUS_REJECTED
    data["reviewed_at"] = now_iso()
    write_json(path, data)
    _remove_from_signals(run_id)
    logger.info(f"[HITL] {channel_id}/{run_id} 거부됨 → 썸네일부터 재생성 필요")


def _remove_from_signals(run_id: str) -> None:
    signals_path = KAS_ROOT / "data/global/notifications/hitl_signals.json"
    try:
        if not signals_path.exists():
            return
        signals = read_json(signals_path)
        signals["pending"] = [
            p for p in signals.get("pending", []) if p.get("run_id") != run_id
        ]
        write_json(signals_path, signals)
    except Exception:
        pass
