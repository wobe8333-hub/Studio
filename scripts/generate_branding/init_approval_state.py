# scripts/generate_branding/init_approval_state.py
"""data/branding/ 디렉토리 및 초기 approval_state.json 생성.

Usage:
    python scripts/generate_branding/init_approval_state.py
"""
import io
import sys
from pathlib import Path

# ── 프로젝트 루트 sys.path 설정 ──────────────────────────────────────────────
_HERE = Path(__file__).parent          # scripts/generate_branding/
_ROOT = _HERE.parent.parent            # 프로젝트 루트
sys.path.insert(0, str(_ROOT))

from loguru import logger

from src.pipeline_v2.branding_gate import initialize_approval_state

# 7채널 목록
CHANNELS = ["CH1", "CH2", "CH3", "CH4", "CH5", "CH6", "CH7"]

# data/branding/ .gitkeep 경로
_BRANDING_ROOT = _ROOT / "data" / "branding"


def main() -> None:
    """모든 채널 approval_state.json 초기화 + .gitkeep 생성."""
    logger.info("=" * 50)
    logger.info("data/branding/ approval_state 초기화 시작")
    logger.info("=" * 50)

    # .gitkeep 생성 (디렉토리 추적용)
    _BRANDING_ROOT.mkdir(parents=True, exist_ok=True)
    gitkeep = _BRANDING_ROOT / ".gitkeep"
    if not gitkeep.exists():
        gitkeep.touch()
        logger.info(f"[OK] .gitkeep 생성: {gitkeep}")
    else:
        logger.info(f"[SKIP] .gitkeep 이미 존재: {gitkeep}")

    # 채널별 초기화
    for ch_id in CHANNELS:
        try:
            initialize_approval_state(ch_id)
            logger.info(f"  [OK] {ch_id} approval_state.json 초기화 완료")
        except Exception as e:
            logger.error(f"  [ERR] {ch_id} 초기화 실패: {e}")

    logger.info("=" * 50)
    logger.info("초기화 완료")
    logger.info("=" * 50)


if __name__ == "__main__":
    if hasattr(sys.stdout, "buffer"):
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    main()
