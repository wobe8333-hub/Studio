"""FAILED 상태의 파이프라인 실행을 감지한다."""
from pathlib import Path
from loguru import logger
from src.core.ssot import read_json


def find_failed_runs(runs_dir: Path) -> list:
    """runs/ 하위 모든 manifest.json을 스캔해 FAILED 항목을 반환한다.

    Args:
        runs_dir: runs/ 루트 디렉토리 경로

    Returns:
        FAILED 상태 manifest 딕셔너리 리스트.
        각 항목: {run_id, channel_id, run_state, error, manifest_path}
    """
    failed = []
    for manifest_path in runs_dir.glob("*/*/manifest.json"):
        try:
            manifest = read_json(manifest_path)
            if manifest.get("run_state") == "FAILED":
                failed.append({
                    "run_id": manifest.get("run_id", manifest_path.parent.name),
                    "channel_id": manifest.get("channel_id", "UNKNOWN"),
                    "run_state": "FAILED",
                    "error": manifest.get("error", ""),
                    "manifest_path": str(manifest_path),
                })
        except Exception as e:
            logger.warning(f"manifest 읽기 실패: {manifest_path} — {e}")
    return failed
