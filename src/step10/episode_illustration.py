"""STEP 10 — Gemini 멀티레퍼런스 에피소드 일러스트 생성.

각 영상마다 마스코트가 토픽 핵심 장면에 등장하는
풀스크린 두들 일러스트를 Gemini Image로 생성한다.
thumbnail_generator.py 가 이 모듈을 호출해 L1 베이스 레이어로 사용.
"""
import json
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from loguru import logger

load_dotenv()

from google import genai
from google.genai import types

from src.core.ssot import read_json, write_json

_ROOT = Path(__file__).resolve().parents[2]
_IMAGE_MODEL = os.environ.get("GEMINI_IMAGE_MODEL", "gemini-3-pro-image-preview")

# ── 7채널 마스코트 페르소나 ────────────────────────────────────────────────────
CHANNEL_MASCOT_PERSONA: dict[str, str] = {
    "CH1": (
        "원이₩ — round bald kawaii doodle character with gold crown "
        "bearing lowercase 'w', wearing business suit and holding a briefcase"
    ),
    "CH2": (
        "가설낙서 scientist — neon-cyan lab coat doodle character "
        "with safety goggles and glowing test tube"
    ),
    "CH3": (
        "홈팔레트 builder — orange tool-belt doodle character "
        "with hard hat, holding blueprints and ruler"
    ),
    "CH4": (
        "오묘한심리 — lavender cardigan doodle character "
        "with round glasses, holding an open notebook"
    ),
    "CH5": (
        "검은물음표 detective — dark trench coat doodle character "
        "with magnifying glass, mysterious suspicious expression"
    ),
    "CH6": (
        "오래된두루마리 scholar — brown robe doodle character "
        "with quill pen and ancient unrolled scroll"
    ),
    "CH7": (
        "워메이징 general — red military field uniform doodle character "
        "with small flag and medal on chest"
    ),
}

# ── 채널별 메인·액센트 컬러 ────────────────────────────────────────────────────
CHANNEL_COLORS: dict[str, tuple[str, str]] = {
    "CH1": ("#F4C420", "#DC2626"),
    "CH2": ("#00E5FF", "#FFFFFF"),
    "CH3": ("#E67E22", "#2ECC71"),
    "CH4": ("#9B59B6", "#BDC3C7"),
    "CH5": ("#1C2833", "#AAAAAA"),
    "CH6": ("#A0522D", "#C4A35A"),
    "CH7": ("#C0392B", "#2C3E50"),
}

# ── 비용 추적 경로 ──────────────────────────────────────────────────────────────
_COST_FILE = _ROOT / "data" / "finance" / "api_costs_thumbnails.json"

# ── 비용 단가 추정 (USD/call) ────────────────────────────────────────────────────
_COST_PER_CALL = 0.04


def _make_client() -> genai.Client:
    api_key = os.environ.get("GEMINI_API_KEY", "")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY 환경 변수 미설정")
    return genai.Client(api_key=api_key)


def _build_prompt(channel: str, topic: str) -> str:
    persona = CHANNEL_MASCOT_PERSONA.get(channel, "cute doodle mascot character")
    main_color, accent_color = CHANNEL_COLORS.get(channel, ("#FFFFFF", "#000000"))
    return (
        f"flat 2D doodle illustration in Korean YouTube thumbnail style. "
        f"Show {persona} in a dramatic scene about: {topic}. "
        f"Channel color palette: main={main_color}, accent={accent_color}. "
        "Thin black 2px outline, NO shadows, NO gradients, NO 3D effects, "
        "wobbly hand-drawn lines, flat colors only. "
        "COMPOSITION: full-screen illustration filling the entire 16:9 frame. "
        "Mascot must be clearly visible and emotionally expressive (shocked, curious, or excited). "
        "BOTTOM 25% of the frame: keep this area visually simple with muted colors — "
        "text will be overlaid here. "
        "TOP-RIGHT corner (8% of frame): keep completely empty and clean — "
        "logo watermark will be placed here. "
        "Focal point: a single dramatic moment that triggers strong viewer curiosity. "
        "CRITICAL TEXT BAN: absolutely NO text, NO letters, NO numbers, NO labels "
        "anywhere in the image except the mascot's costume details (e.g., 'w' on the crown). "
        "Background: white or channel main color, not busy."
    )


def _record_cost(run_id: str, channel: str, calls: int, success: bool) -> None:
    try:
        _COST_FILE.parent.mkdir(parents=True, exist_ok=True)
        try:
            data = read_json(_COST_FILE)
        except (FileNotFoundError, json.JSONDecodeError, Exception):
            data = {"records": [], "total_calls": 0, "total_cost_usd": 0.0}

        record = {
            "run_id": run_id,
            "channel": channel,
            "gemini_calls": calls,
            "cost_usd": round(calls * _COST_PER_CALL, 4),
            "success": success,
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }
        data.setdefault("records", []).append(record)
        data["total_calls"] = data.get("total_calls", 0) + calls
        data["total_cost_usd"] = round(
            data.get("total_cost_usd", 0.0) + record["cost_usd"], 4
        )
        write_json(_COST_FILE, data)
    except Exception as e:
        logger.warning(f"[STEP10-ILLUST] 비용 기록 실패 (무시): {e}")


def generate_episode_illustration(
    channel: str,
    topic: str,
    run_id: str,
    output_path: Path,
    max_retries: int = 2,
    *,
    client: Optional[genai.Client] = None,
) -> Path | None:
    """에피소드별 마스코트 통합 풀스크린 일러스트 생성.

    레퍼런스 이미지(두들 스타일 4장 + 채널 로고 + 마스코트)를 few-shot으로
    전달해 일관된 두들 스타일을 확보한다.

    Returns:
        성공 시 output_path, 실패(모든 재시도 소진) 시 None
    """
    ref_dir = _ROOT / "assets" / "references"
    style_refs = [
        ref_dir / "logo_ref_01.png",
        ref_dir / "logo_ref_02.png",
        ref_dir / "logo_ref_03.png",
        ref_dir / "logo_ref_04.png",
    ]
    channel_refs = [
        _ROOT / "assets" / "channels" / channel / "logo" / "logo.png",
        _ROOT / "assets" / "channels" / channel / "characters" / "character_default.png",
    ]

    refs = [p for p in style_refs + channel_refs if p.exists()]
    if not refs:
        logger.warning(f"[STEP10-ILLUST] 레퍼런스 이미지 없음 ({channel}) — 폴백으로 진행")
        return None

    prompt = _build_prompt(channel, topic)
    if client is None:
        client = _make_client()

    calls = 0
    for attempt in range(max_retries + 1):
        try:
            ref_parts = [
                types.Part.from_bytes(data=p.read_bytes(), mime_type="image/png")
                for p in refs
            ]
            response = client.models.generate_content(
                model=_IMAGE_MODEL,
                contents=ref_parts + [prompt],
                config=types.GenerateContentConfig(
                    response_modalities=["IMAGE"],
                ),
            )
            calls += 1

            for part in response.candidates[0].content.parts:
                if part.inline_data and part.inline_data.mime_type.startswith("image/"):
                    output_path.parent.mkdir(parents=True, exist_ok=True)
                    output_path.write_bytes(part.inline_data.data)
                    logger.info(
                        f"[STEP10-ILLUST] 생성 성공: {output_path.name} "
                        f"({len(part.inline_data.data):,} bytes, 시도={attempt+1})"
                    )
                    _record_cost(run_id, channel, calls, True)
                    return output_path

            logger.warning(
                f"[STEP10-ILLUST] 이미지 응답 없음 (시도 {attempt+1}/{max_retries+1})"
            )

        except Exception as e:
            calls += 1
            logger.warning(f"[STEP10-ILLUST] 생성 실패 (시도 {attempt+1}): {e}")

        if attempt < max_retries:
            time.sleep(2.0)

    _record_cost(run_id, channel, calls, False)
    logger.warning(f"[STEP10-ILLUST] {max_retries+1}회 모두 실패 → 폴백 사용 ({channel})")
    return None
