"""
V8 Pipeline package - 채널별 자동 영상/업로드 패키지 생성.

이 패키지는 기존 V7 코드를 변경하지 않고, runs SSOT(run_manager),
FFmpeg 기반 렌더링, Gemini 이미지 생성, 해시/레지스트리/상태머신을
포함한 V8 파이프라인만을 담당한다.
"""

from enum import Enum
from pathlib import Path
from typing import Dict, Any
import json
from datetime import datetime


class V8Stage(str, Enum):
    INIT = "init"
    SCRIPT_BUILT = "script_built"
    IMAGES_GENERATED = "images_generated"
    AUDIO_GENERATED = "audio_generated"
    SUBTITLES_GENERATED = "subtitles_generated"
    VIDEO_RENDERED = "video_rendered"
    THUMBNAIL_BUILT = "thumbnail_built"
    PACKAGE_BUILT = "package_built"
    UPLOAD_SYNCED = "upload_synced"
    VERIFIED = "verified"


class V8ValidationError(Exception):
    """채널/스타일/스크립트 등 사전 검증 실패."""


class V8FFmpegNotFound(Exception):
    """FFmpeg를 찾을 수 없을 때 사용 (exit 71)."""


class V8GeminiError(Exception):
    """Gemini 이미지 생성 실패 (exit 73)."""


class V8ThumbnailPolicyError(Exception):
    """썸네일 텍스트 정책상 실패해야 하는 경우 (exit 74)."""


def _now_utc_iso() -> str:
    return datetime.utcnow().isoformat() + "Z"


def update_render_state(run_root: Path, run_id: str, stage: V8Stage) -> None:
    """
    `<run_root>/v8/state/render_state.json` 상태머신 업데이트.

    stage 전이 시마다 호출하여 감사/재개 기준을 남긴다.
    """
    v8_root = run_root / "v8"
    state_dir = v8_root / "state"
    state_dir.mkdir(parents=True, exist_ok=True)
    state_path = state_dir / "render_state.json"

    data: Dict[str, Any]
    if state_path.exists():
        try:
            data = json.loads(state_path.read_text(encoding="utf-8"))
        except Exception:
            data = {}
    else:
        data = {}

    schema_version = "v1.0"
    stages = data.get("stages") or {}

    if stage.value not in stages:
        stages[stage.value] = {
            "stage": stage.value,
            "first_entered_at_utc": _now_utc_iso()
        }
    else:
        stages[stage.value]["last_updated_at_utc"] = _now_utc_iso()

    data.update(
        {
            "schema_version": schema_version,
            "run_id": run_id,
            "run_root": run_root.as_posix(),
            "v8_root": v8_root.as_posix(),
            "current_stage": stage.value,
            "stages": stages,
        }
    )

    state_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

