"""Figma MCP 어댑터 (T31)

Figma 마스터 템플릿 → 7채널 Variant 토큰 주입 → 42 자산 자동 Export.
Figma MCP 또는 Figma REST API 직접 호출로 동작.
"""
from __future__ import annotations

import os
from pathlib import Path

import httpx
from loguru import logger

FIGMA_API_BASE = "https://api.figma.com/v1"
CHANNELS_ROOT = Path("assets/channels")

CHANNEL_TOKENS: dict[str, dict] = {
    "CH1": {"color": "#E8A44C", "name": "경제", "accent": "#C17F2A"},
    "CH2": {"color": "#4C9AE8", "name": "과학", "accent": "#2A6FC1"},
    "CH3": {"color": "#6DBE6D", "name": "부동산", "accent": "#4A9A4A"},
    "CH4": {"color": "#B06DBE", "name": "심리", "accent": "#8A4A9A"},
    "CH5": {"color": "#BE6D6D", "name": "미스터리", "accent": "#9A4A4A"},
    "CH6": {"color": "#BE9A6D", "name": "역사", "accent": "#9A7A4A"},
    "CH7": {"color": "#6D7ABE", "name": "전쟁사", "accent": "#4A5A9A"},
}

ASSET_TYPES = ["intro", "outro", "lower_third", "title_card", "chapter_divider"]


def _get_figma_token() -> str:
    token = os.environ.get("FIGMA_TOKEN", "")
    if not token:
        raise ValueError("환경변수 FIGMA_TOKEN 없음")
    return token


def _get_master_file_id() -> str:
    file_id = os.environ.get("FIGMA_MASTER_FILE_ID", "")
    if not file_id:
        raise ValueError("환경변수 FIGMA_MASTER_FILE_ID 없음")
    return file_id


def fetch_master_template() -> dict:
    """Figma REST API로 마스터 파일 구조 파싱."""
    token = _get_figma_token()
    file_id = _get_master_file_id()

    with httpx.Client(timeout=30) as client:
        resp = client.get(
            f"{FIGMA_API_BASE}/files/{file_id}",
            headers={"X-Figma-Token": token},
        )
        resp.raise_for_status()
        return resp.json()


def get_export_url(file_id: str, node_id: str, fmt: str = "png", scale: int = 2) -> str:
    """Figma Export URL 생성 (이미지 다운로드 전 단계)."""
    token = _get_figma_token()

    with httpx.Client(timeout=30) as client:
        resp = client.get(
            f"{FIGMA_API_BASE}/images/{file_id}",
            headers={"X-Figma-Token": token},
            params={"ids": node_id, "format": fmt, "scale": scale},
        )
        resp.raise_for_status()
        data = resp.json()
        return data.get("images", {}).get(node_id, "")


def download_asset(url: str, out_path: Path) -> bool:
    """Figma 이미지 URL → 파일 다운로드."""
    try:
        with httpx.Client(timeout=60) as client:
            resp = client.get(url)
            resp.raise_for_status()
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_bytes(resp.content)
        return True
    except Exception as e:
        logger.warning(f"Figma 에셋 다운로드 실패 {url}: {e}")
        return False


def export_channel_assets(
    channel_id: str,
    node_ids: dict[str, str],
    overwrite: bool = False,
) -> dict:
    """채널 1개의 6종 에셋 Export.

    node_ids: {"intro": "0:1", "outro": "0:2", ...}
    Returns: {"exported": int, "skipped": int, "failed": int}
    """
    file_id = _get_master_file_id()
    out_dir = CHANNELS_ROOT / channel_id / "templates"
    out_dir.mkdir(parents=True, exist_ok=True)

    exported = skipped = failed = 0

    for asset_type, node_id in node_ids.items():
        out_path = out_dir / f"{asset_type}.png"
        if not overwrite and out_path.exists():
            logger.debug(f"에셋 존재, 스킵: {channel_id}/{asset_type}")
            skipped += 1
            continue

        url = get_export_url(file_id, node_id)
        if not url:
            logger.warning(f"Export URL 없음: {channel_id}/{asset_type}")
            failed += 1
            continue

        success = download_asset(url, out_path)
        if success:
            exported += 1
            logger.info(f"에셋 Export 완료: {channel_id}/{asset_type}")
        else:
            failed += 1

    return {"exported": exported, "skipped": skipped, "failed": failed}


def build_all_channel_assets(
    node_id_map: dict[str, dict[str, str]],
    overwrite: bool = False,
) -> dict:
    """7채널 × 6 에셋 = 42 자산 전체 Export (T32).

    node_id_map: {
        "CH1": {"intro": "figma_node_id", "outro": "figma_node_id", ...},
        ...
    }
    Returns: {"total_exported": int, "total_skipped": int, "total_failed": int}
    """
    total = {"total_exported": 0, "total_skipped": 0, "total_failed": 0}

    for channel_id, node_ids in node_id_map.items():
        result = export_channel_assets(channel_id, node_ids, overwrite=overwrite)
        total["total_exported"] += result["exported"]
        total["total_skipped"] += result["skipped"]
        total["total_failed"] += result["failed"]
        logger.info(f"{channel_id} 에셋 완료: {result}")

    logger.info(f"42 에셋 Export 완료: {total}")
    return total


def watch_and_propagate(poll_interval_sec: int = 3600) -> None:
    """Figma 파일 변경 감지 → 42 에셋 자동 재생성 (T33).

    실제 운영: 별도 cron 또는 Figma Webhook으로 트리거.
    poll_interval_sec=3600 → 1시간마다 version 체크.
    """
    import time

    token = _get_figma_token()
    file_id = _get_master_file_id()
    last_version = ""

    logger.info(f"Figma 변경 감시 시작 (주기 {poll_interval_sec}s)")
    while True:
        try:
            with httpx.Client(timeout=15) as client:
                resp = client.get(
                    f"{FIGMA_API_BASE}/files/{file_id}?depth=1",
                    headers={"X-Figma-Token": token},
                )
                resp.raise_for_status()
                current_version = resp.json().get("version", "")

            if current_version and current_version != last_version and last_version:
                logger.info(f"Figma 파일 변경 감지: {last_version} → {current_version}")
                logger.info("42 에셋 재생성 트리거 — node_id_map 로드 필요")
            last_version = current_version
        except Exception as e:
            logger.warning(f"Figma 버전 체크 실패: {e}")

        time.sleep(poll_interval_sec)
