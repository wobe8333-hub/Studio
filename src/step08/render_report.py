"""
render_report.py
STEP 08 렌더 결과 리포트 CRUD 모듈.
render_report.json 의 생성/읽기/갱신을 담당한다.
실제 render_report.json 최초 생성은 step08/__init__.py _generate_metadata_files 에서 수행.
이 모듈은 다른 STEP(09, 11, 15 등)이 render_report.json 을 읽거나 갱신할 때 사용한다.
"""

from pathlib import Path

from src.core.ssot import get_run_dir, json_exists, now_iso, read_json, write_json


def get_render_report_path(channel_id: str, run_id: str) -> Path:
    """render_report.json 경로 반환."""
    return get_run_dir(channel_id, run_id) / "step08" / "render_report.json"


def read_render_report(channel_id: str, run_id: str) -> dict:
    """render_report.json 읽기. 없으면 빈 dict 반환."""
    path = get_render_report_path(channel_id, run_id)
    if not json_exists(path):
        return {}
    return read_json(path)


def update_render_report(channel_id: str, run_id: str, updates: dict) -> None:
    """render_report.json 에 updates 딕셔너리를 머지(덮어쓰기)하여 저장."""
    path = get_render_report_path(channel_id, run_id)
    data = {}
    if json_exists(path):
        data = read_json(path)
    data.update(updates)
    data["updated_at"] = now_iso()
    write_json(path, data)


def mark_bgm_applied(channel_id: str, run_id: str, bgm_tone: str) -> None:
    """BGM 적용 완료 기록. step09에서 호출."""
    update_render_report(channel_id, run_id, {
        "bgm_used": True,
        "bgm_category_tone": bgm_tone,
    })


def mark_bgm_missing(channel_id: str, run_id: str) -> None:
    """BGM 파일 없음 기록. step09에서 호출."""
    update_render_report(channel_id, run_id, {
        "bgm_used": False,
        "bgm_category_tone": "MISSING",
    })


def get_video_spec(channel_id: str, run_id: str) -> dict:
    """video_spec 반환. 없으면 빈 dict."""
    report = read_render_report(channel_id, run_id)
    return report.get("video_spec", {})


def get_target_duration(channel_id: str, run_id: str) -> int:
    """target_duration_sec 반환. 없으면 720."""
    report = read_render_report(channel_id, run_id)
    return report.get("target_duration_sec", 720)
