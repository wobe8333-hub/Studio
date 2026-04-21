"""자동 처리 범위를 초과한 이벤트에 대해 HITL 신호를 기록한다.

자동 처리 가능:
  - 스키마 동기화 누락 감지 → UiUxAgent 위임 알림
  - 헬스체크 결과 로깅

운영자 확인 필요 (HITL):
  - pytest 실패 → 회귀 가능성, 직접 검토 필요
  - FAILED 실행 N건 이상 → 원인 불명, 직접 로그 분석 필요
"""
import uuid
from datetime import datetime, timezone
from pathlib import Path

from loguru import logger

from src.core.ssot import read_json, write_json

_SIGNALS_FILE = "hitl_signals.json"

# 운영자 확인이 필요한 임계값
FAILED_RUNS_THRESHOLD = 1  # FAILED 실행이 1건 이상이면 HITL


def emit_hitl_signal(
    signals_dir: Path,
    signal_type: str,
    details: dict,
) -> None:
    """HITL 신호를 hitl_signals.json 에 추가한다.

    Args:
        signals_dir: 신호 파일을 저장할 디렉토리
        signal_type: 신호 유형 ("pytest_failure", "pipeline_failure", "schema_mismatch")
        details: 신호 상세 정보
    """
    signals_dir.mkdir(parents=True, exist_ok=True)
    signals_path = signals_dir / _SIGNALS_FILE

    signals = read_json(signals_path) if signals_path.exists() else []
    if not isinstance(signals, list):
        signals = []

    entry = {
        "id": str(uuid.uuid4()),
        "type": signal_type,
        "details": details,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "resolved": False,
    }
    signals.append(entry)
    write_json(signals_path, signals)
    logger.warning(f"[HITL] 운영자 확인 필요 — {signal_type}: {details}")


def get_unresolved_signals(signals_dir: Path) -> list:
    """미해결 HITL 신호 목록을 반환한다."""
    signals_path = signals_dir / _SIGNALS_FILE
    if not signals_path.exists():
        return []
    signals = read_json(signals_path)
    if not isinstance(signals, list):
        return []
    return [s for s in signals if not s.get("resolved", False)]
