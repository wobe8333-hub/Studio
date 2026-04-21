"""저작권 사전 체크 통합 — Step11 기존 로직 이식 (T44)

업로드 전 Content ID 위험 감지. 기존 src/step11/copyright_checker.py 재사용.
"""
from __future__ import annotations

from loguru import logger

from src.pipeline_v2.episode_schema import EpisodeMeta

COPYRIGHT_RISK_THRESHOLD = 0.70


def check_episode_copyright(meta: EpisodeMeta, script: str, upload_meta: dict) -> dict:
    """업로드 전 저작권 위험 체크.

    Returns: {"safe": bool, "risk_score": float, "reasons": [str], "blocked": bool}
    """
    try:
        from src.step11.copyright_checker import check_copyright_risk
        result = check_copyright_risk(script)
    except ImportError:
        logger.warning("step11.copyright_checker 미설치 — 저작권 체크 스킵")
        return {"safe": True, "risk_score": 0.0, "reasons": [], "blocked": False}
    except Exception as e:
        logger.warning(f"저작권 체크 실패: {e}")
        return {"safe": True, "risk_score": 0.0, "reasons": [str(e)], "blocked": False}

    risk_score = result.get("risk_score", 0.0)
    reasons = result.get("reasons", [])

    title = upload_meta.get("title", "")
    if any(kw in title for kw in ["공식", "Original", "© ", "®"]):
        risk_score = min(1.0, risk_score + 0.2)
        reasons.append("제목에 저작권 표시 키워드 포함")

    safe = risk_score < COPYRIGHT_RISK_THRESHOLD
    blocked = risk_score >= 0.9

    if blocked:
        logger.error(f"저작권 위험 심각: {meta.episode_id} score={risk_score:.2f} — 업로드 차단")
        _emit_copyright_hitl_signal(meta, risk_score, reasons)
    elif not safe:
        logger.warning(f"저작권 위험 주의: {meta.episode_id} score={risk_score:.2f}")

    return {
        "safe": safe,
        "risk_score": round(risk_score, 3),
        "reasons": reasons,
        "blocked": blocked,
    }


def _emit_copyright_hitl_signal(meta: EpisodeMeta, risk_score: float, reasons: list[str]) -> None:
    """저작권 위험 심각 시 HITL 웹 대시보드 알림."""
    from datetime import datetime, timezone
    from pathlib import Path

    from src.core.ssot import read_json, write_json

    path = Path("data/global/notifications/hitl_signals.json")
    path.parent.mkdir(parents=True, exist_ok=True)
    existing = []
    if path.exists():
        try:
            existing = read_json(path)
            if not isinstance(existing, list):
                existing = []
        except Exception:
            existing = []

    existing.append({
        "type": "copyright_block",
        "episode_id": meta.episode_id,
        "channel_id": meta.channel_id,
        "risk_score": risk_score,
        "reasons": reasons,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "status": "pending",
    })
    write_json(path, existing[-100:])
