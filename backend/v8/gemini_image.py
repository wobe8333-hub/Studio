import base64
import json
import os
import re
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple

from urllib import request, error as urlerror

from backend.utils import run_manager
from backend.v8.hash_utils import sha256_bytes
from backend.v8 import V8GeminiError


def get_gemini_cache_root() -> Path:
    """backend/output/gemini_cache SSOT."""
    root = run_manager.get_project_root()
    return root / "backend" / "output" / "gemini_cache"


def cache_key_for_request(
    model_id: str,
    aspect_ratio: str,
    image_size: str,
    prompt_text: str,
) -> str:
    """SHA256(model_id + aspect_ratio + image_size + prompt_text)."""
    raw = f"{model_id}|{aspect_ratio}|{image_size}|{prompt_text}"
    return sha256_bytes(raw.encode("utf-8"))


def sanitize_background_prompt(prompt_text: str) -> str:
    """
    배경 전용: character/stickman/person/face 등이 포함되면 제거.
    Gemini는 배경 생성 전용, 캐릭터 생성 금지.
    """
    lower = prompt_text.lower()
    forbidden = ["character", "stickman", "person", "human", "people", "man", "woman", "face"]
    out = prompt_text
    for w in forbidden:
        if w in lower:
            out = re.sub(re.escape(w), "", out, flags=re.IGNORECASE)
            out = re.sub(r"\s+", " ", out).strip()
    return out


def _now_utc_iso() -> str:
    return datetime.utcnow().isoformat() + "Z"


def _find_inline_images(obj: Any) -> List[Tuple[str | None, str]]:
    """
    응답 JSON 전체를 탐색하면서 inlineData/inline_data 경로를 전수 스캔.
    반환: (mime_type, base64_data)
    """
    results: List[Tuple[str | None, str]] = []

    if isinstance(obj, dict):
        # inlineData / inline_data 직접 확인
        inline = None
        if "inlineData" in obj and isinstance(obj["inlineData"], dict):
            inline = obj["inlineData"]
        elif "inline_data" in obj and isinstance(obj["inline_data"], dict):
            inline = obj["inline_data"]
        if inline is not None:
            mime = inline.get("mimeType") or inline.get("mime_type")
            data = inline.get("data")
            if isinstance(data, str):
                results.append((mime, data))

        # 하위 항목 재귀 탐색
        for v in obj.values():
            results.extend(_find_inline_images(v))
    elif isinstance(obj, list):
        for item in obj:
            results.extend(_find_inline_images(item))

    return results


def call_gemini_image_api(
    model_id: str,
    prompt_text: str,
    aspect_ratio: str,
    image_size: str,
) -> Tuple[int, bytes]:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        # 상위에서 exit 72를 처리할 수 있도록 명확한 예외 사용
        raise V8GeminiError("GEMINI_API_KEY missing")

    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{model_id}:generateContent"
    )

    payload = {
        "contents": [{"parts": [{"text": prompt_text}]}],
        "generationConfig": {
            "responseModalities": ["IMAGE"],
            "imageConfig": {
                "aspectRatio": aspect_ratio,
                "imageSize": image_size,
            },
        },
    }
    data = json.dumps(payload).encode("utf-8")

    headers = {
        "x-goog-api-key": api_key,
        "Content-Type": "application/json",
    }
    req = request.Request(url, data=data, headers=headers, method="POST")

    try:
        with request.urlopen(req, timeout=60) as resp:
            status = resp.getcode()
            body = resp.read()
    except urlerror.HTTPError as e:
        status = e.code
        body = e.read() or b""
    except urlerror.URLError as e:
        raise V8GeminiError(f"Gemini HTTP error: {e}") from e

    return status, body


def generate_section_image(
    model_id: str,
    prompt_text: str,
    aspect_ratio: str,
    image_size: str,
    channel_id: str,
    content_id: str,
    run_id: str,
    section_id: str,
    assets_dir: Path,
    raw_dir: Path,
    cache_enabled: bool = False,
    background_only: bool = False,
) -> Dict[str, Any]:
    """
    단일 섹션 이미지 생성 + raw/receipt 메타 반환.
    cache_enabled 시 동일 프롬프트면 캐시 재사용(cache_hit 기록).
    background_only 시 프롬프트에서 character/stickman/person 등 제거.
    """
    assets_dir.mkdir(parents=True, exist_ok=True)
    raw_dir.mkdir(parents=True, exist_ok=True)

    if background_only:
        prompt_text = sanitize_background_prompt(prompt_text)

    out_path = assets_dir / f"{section_id}.png"
    raw_path = raw_dir / f"{section_id}.json"

    if cache_enabled:
        cache_root = get_gemini_cache_root()
        cache_root.mkdir(parents=True, exist_ok=True)
        key = cache_key_for_request(model_id, aspect_ratio, image_size, prompt_text)
        cache_png = cache_root / f"{key}.png"
        cache_json = cache_root / f"{key}.json"
        if cache_png.is_file() and cache_json.is_file():
            shutil.copy2(cache_png, out_path)
            shutil.copy2(cache_json, raw_path)
            image_sha = sha256_bytes(out_path.read_bytes())
            meta = json.loads(cache_json.read_text(encoding="utf-8"))
            receipt = {
                "ts_utc": _now_utc_iso(),
                "channel_id": channel_id,
                "content_id": content_id,
                "run_id": run_id,
                "section_id": section_id,
                "model_id": model_id,
                "aspect_ratio": aspect_ratio,
                "image_size": image_size,
                "prompt_text": prompt_text,
                "cache_hit": True,
                "cache_key": key,
                "response_sha256": meta.get("response_sha256", ""),
                "raw_path": raw_path.as_posix(),
                "image_sha256": image_sha,
                "out_path": out_path.as_posix(),
                "mime_type": "image/png",
            }
            return receipt

    status, body = call_gemini_image_api(
        model_id=model_id,
        prompt_text=prompt_text,
        aspect_ratio=aspect_ratio,
        image_size=image_size,
    )

    try:
        raw_path.write_bytes(body)
    except Exception:
        raise V8GeminiError(f"failed to write raw Gemini response: {raw_path}")

    response_sha = sha256_bytes(body)

    try:
        parsed = json.loads(body.decode("utf-8"))
    except Exception as e:
        raise V8GeminiError(f"Gemini response is not valid JSON: {e}")

    candidates = _find_inline_images(parsed)
    chosen_bytes: bytes | None = None
    chosen_mime: str | None = None

    for mime, b64 in candidates:
        if mime and not str(mime).lower().startswith("image/"):
            continue
        try:
            img_bytes = base64.b64decode(b64)
        except Exception:
            continue
        if img_bytes:
            chosen_bytes = img_bytes
            chosen_mime = str(mime) if mime else "image/png"
            break

    if chosen_bytes is None:
        raise V8GeminiError("no inline image data found in Gemini response")

    try:
        out_path.write_bytes(chosen_bytes)
    except Exception as e:
        raise V8GeminiError(f"failed to write image bytes: {e}")

    image_sha = sha256_bytes(chosen_bytes)

    if cache_enabled:
        cache_root = get_gemini_cache_root()
        cache_root.mkdir(parents=True, exist_ok=True)
        key = cache_key_for_request(model_id, aspect_ratio, image_size, prompt_text)
        cache_png = cache_root / f"{key}.png"
        cache_json = cache_root / f"{key}.json"
        cache_png.write_bytes(chosen_bytes)
        cache_json.write_text(
            json.dumps(
                {
                    "response_sha256": response_sha,
                    "image_sha256": image_sha,
                    "model_id": model_id,
                    "prompt_text": prompt_text,
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

    receipt = {
        "ts_utc": _now_utc_iso(),
        "channel_id": channel_id,
        "content_id": content_id,
        "run_id": run_id,
        "section_id": section_id,
        "model_id": model_id,
        "aspect_ratio": aspect_ratio,
        "image_size": image_size,
        "prompt_text": prompt_text,
        "cache_hit": False,
        "http_status": status,
        "response_sha256": response_sha,
        "raw_path": raw_path.as_posix(),
        "image_sha256": image_sha,
        "out_path": out_path.as_posix(),
        "mime_type": chosen_mime or "image/png",
    }
    return receipt

