"""HITL 게이트 훅 — 파이프라인 3 게이트 진입 시 hitl_queue INSERT

게이트 3종:
  series_approval  — 월간 시리즈 테마 승인 (Track A 완료 후)
  thumbnail_veto   — 썸네일 A/B/C 거부권 (Track C 완료 후)
  final_preview    — 최종 영상 프리뷰 (QC 통과 후, 업로드 전)

구현 방식: 비차단(non-blocking) 신호 방식
  1. Supabase hitl_queue 테이블에 INSERT (대시보드 표시)
  2. data/global/notifications/hitl_signals.json 로컬 기록 (SSOT)
  3. 파이프라인은 계속 진행 (auto-approved) — 운영자는 대시보드에서 사후 검토

  *완전 차단 게이트는 Phase 2에서 구현 예정 (Supabase Realtime polling 기반)
"""
from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from loguru import logger

from src.core.ssot import read_json, write_json

HITL_SIGNALS_PATH = Path("data/global/notifications/hitl_signals.json")


def _supabase_insert(record: dict[str, Any]) -> bool:
    """Supabase hitl_queue에 INSERT. 환경변수 없으면 스킵."""
    url = os.getenv("NEXT_PUBLIC_SUPABASE_URL", "")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
    if not url or not key or "xxxxxxxxxxxx" in url:
        logger.debug("Supabase 미연결 — hitl_queue INSERT 스킵")
        return False

    try:
        import json as _json
        import urllib.request

        payload = _json.dumps(record).encode()
        req = urllib.request.Request(
            f"{url}/rest/v1/hitl_queue",
            data=payload,
            headers={
                "apikey": key,
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json",
                "Prefer": "return=minimal",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            return resp.status in (200, 201)
    except Exception as exc:
        logger.warning(f"hitl_queue INSERT 실패 (무시): {exc}")
        return False


def _write_local_signal(record: dict[str, Any]) -> None:
    """SSOT: data/global/notifications/hitl_signals.json 에 신호 기록."""
    HITL_SIGNALS_PATH.parent.mkdir(parents=True, exist_ok=True)
    try:
        existing = read_json(str(HITL_SIGNALS_PATH))
        if not isinstance(existing, list):
            existing = []
    except Exception:
        existing = []

    existing.append(record)
    # 최근 100건만 유지
    write_json(str(HITL_SIGNALS_PATH), existing[-100:])


def trigger_series_approval(
    channel_id: str,
    series_id: str,
    episode_titles: list[str],
) -> None:
    """시리즈 승인 게이트 — Track A 완료 직후 호출.

    Args:
        channel_id: 채널 ID (CH1~CH7)
        series_id: 시리즈 ID
        episode_titles: 이번 시리즈 에피소드 제목 목록
    """
    now = datetime.now(timezone.utc).isoformat()
    record: dict[str, Any] = {
        "hitl_type": "series_approval",
        "channel_id": channel_id,
        "series_id": series_id,
        "payload": {
            "episode_titles": episode_titles,
            "episode_count": len(episode_titles),
        },
        "status": "pending",
        "created_at": now,
    }

    inserted = _supabase_insert(record)
    _write_local_signal(record)
    logger.info(
        f"[HITL Gate] series_approval 트리거: {channel_id}/{series_id} "
        f"({len(episode_titles)}편) | Supabase={'OK' if inserted else 'SKIP'}"
    )


def trigger_thumbnail_veto(
    channel_id: str,
    episode_id: str,
    thumbnail_urls: list[str],
) -> None:
    """썸네일 거부권 게이트 — Track C 완료 직후 호출.

    Args:
        channel_id: 채널 ID
        episode_id: 에피소드 ID
        thumbnail_urls: A/B/C 후보 이미지 경로 (최대 3개)
    """
    now = datetime.now(timezone.utc).isoformat()
    record: dict[str, Any] = {
        "hitl_type": "thumbnail_veto",
        "channel_id": channel_id,
        "episode_id": episode_id,
        "payload": {
            "thumbnail_candidates": thumbnail_urls[:3],
            "candidate_count": len(thumbnail_urls[:3]),
        },
        "status": "pending",
        "created_at": now,
    }

    inserted = _supabase_insert(record)
    _write_local_signal(record)
    logger.info(
        f"[HITL Gate] thumbnail_veto 트리거: {channel_id}/{episode_id} "
        f"({len(thumbnail_urls[:3])}종) | Supabase={'OK' if inserted else 'SKIP'}"
    )


def trigger_final_preview(
    channel_id: str,
    episode_id: str,
    video_path: str,
    title: str,
    description: str = "",
) -> None:
    """최종 프리뷰 게이트 — QC 통과 후 업로드 직전 호출.

    Args:
        channel_id: 채널 ID
        episode_id: 에피소드 ID
        video_path: 최종 영상 파일 경로
        title: YouTube 제목
        description: YouTube 설명 (선택)
    """
    now = datetime.now(timezone.utc).isoformat()
    record: dict[str, Any] = {
        "hitl_type": "final_preview",
        "channel_id": channel_id,
        "episode_id": episode_id,
        "payload": {
            "video_path": video_path,
            "title": title,
            "description": description[:200],
        },
        "status": "pending",
        "created_at": now,
    }

    inserted = _supabase_insert(record)
    _write_local_signal(record)
    logger.info(
        f"[HITL Gate] final_preview 트리거: {channel_id}/{episode_id} "
        f"| title='{title[:40]}' | Supabase={'OK' if inserted else 'SKIP'}"
    )
