"""
STEP 08 — 이미지 생성기
google.genai (신버전 SDK) 기반 이미지 생성 → 실패 시 ffmpeg/최소PNG 플레이스홀더 폴백
"""
import shutil
import struct
import subprocess
import time
import zlib
from pathlib import Path

from google import genai
from google.genai import types
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential

from src.core.config import GEMINI_API_KEY, GEMINI_IMAGE_MODEL
from src.quota.gemini_quota import record_image, record_request, throttle_if_needed

IMAGE_PROMPT_TEMPLATE = """Create a clean background illustration for a Korean YouTube knowledge video scene.
Scene: {description}
Style: Simple doodle / flat illustration. WHITE or very light pastel background. Korean YouTube educational channel aesthetic.
Color scheme: Soft warm colors — gold, green, light blue, cream. Simple outlines, no heavy gradients.
DO include: Simple icons, arrows, small charts, relevant objects to the scene topic (coins, graphs, buildings, etc.)
DO NOT include: people, faces, realistic photos, dark backgrounds, text, watermarks, complex patterns.
The image is a BACKGROUND — a character will be composited on top, so keep the center-right area clean.
"""

BATCH_SIZE = 3
BATCH_INTERVAL_SEC = 2
_image_gen_supported: bool | None = None


def _make_client() -> genai.Client:
    return genai.Client(api_key=GEMINI_API_KEY)


def _check_image_generation_support() -> bool:
    global _image_gen_supported
    if _image_gen_supported is not None:
        return _image_gen_supported
    try:
        client = _make_client()
        response = client.models.generate_content(
            model=GEMINI_IMAGE_MODEL,
            contents="A simple blue circle on dark background",
            config=types.GenerateContentConfig(
                response_modalities=["IMAGE"],
            ),
        )
        for part in response.candidates[0].content.parts:
            if part.inline_data and part.inline_data.mime_type.startswith("image/"):
                _image_gen_supported = True
                logger.info(f"[STEP08] 이미지 생성 지원 확인: {GEMINI_IMAGE_MODEL}")
                return True
        _image_gen_supported = False
    except Exception as e:
        logger.warning(f"[STEP08] 이미지 생성 미지원 ({GEMINI_IMAGE_MODEL}): {e}")
        _image_gen_supported = False
    return _image_gen_supported


def _generate_placeholder(description: str, output_path: Path) -> bool:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    label = description[:40].replace("'", "").replace('"', "")
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg:
        cmd = [
            ffmpeg, "-y", "-f", "lavfi",
            "-i", "color=c=0x1a1a2e:size=1920x1080:rate=1",
            "-vframes", "1",
            "-vf", f"drawtext=fontsize=48:fontcolor=white"
                   f":x=(w-text_w)/2:y=(h-text_h)/2:text='{label}'",
            str(output_path),
        ]
        if subprocess.run(cmd, capture_output=True, timeout=30).returncode == 0:
            return True
    try:
        def _chunk(t, d):
            c = struct.pack(">I", len(d)) + t + d
            return c + struct.pack(">I", zlib.crc32(c[4:]) & 0xffffffff)

        png = (
            b"\x89PNG\r\n\x1a\n"
            + _chunk(
                b"IHDR",
                struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0),
            )
            + _chunk(b"IDAT", zlib.compress(b"\x00\x1a\x1a\x2e"))
            + _chunk(b"IEND", b"")
        )
        output_path.write_bytes(png)
        return True
    except Exception as e:
        logger.error(f"[STEP08] 플레이스홀더 생성 실패: {e}")
        return False


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=30))
def generate_single_image(description: str, output_path: Path) -> bool:
    if not record_image(1):
        logger.error("[STEP08] GEMINI_IMAGE_LIMIT_EXCEEDED")
        return _generate_placeholder(description, output_path)
    if not _check_image_generation_support():
        logger.warning(f"[STEP08] {GEMINI_IMAGE_MODEL} 이미지 미지원 → 플레이스홀더")
        return _generate_placeholder(description, output_path)
    throttle_if_needed()
    record_request()
    client = _make_client()
    response = client.models.generate_content(
        model=GEMINI_IMAGE_MODEL,
        contents=IMAGE_PROMPT_TEMPLATE.format(description=description),
        config=types.GenerateContentConfig(
            response_modalities=["IMAGE"],
        ),
    )
    for part in response.candidates[0].content.parts:
        if part.inline_data and part.inline_data.mime_type.startswith("image/"):
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_bytes(part.inline_data.data)
            return True
    return _generate_placeholder(description, output_path)


def generate_batch(sections: list, output_dir: Path) -> dict:
    results, batch = {}, []
    for i, sec in enumerate(sections):
        batch.append((i, sec))
        if len(batch) >= BATCH_SIZE or i == len(sections) - 1:
            for _, s in batch:
                desc = s.get("animation_prompt", f"Section {s['id']}")
                img_path = output_dir / f"section_{s['id']:03d}_frame.png"
                try:
                    results[s["id"]] = (
                        img_path
                        if generate_single_image(desc, img_path)
                        else None
                    )
                except Exception as e:
                    logger.error(f"[STEP08] IMAGE_GEN_FAIL section={s['id']}: {e}")
                    results[s["id"]] = None
            if i < len(sections) - 1:
                time.sleep(BATCH_INTERVAL_SEC)
            batch = []
    return results
