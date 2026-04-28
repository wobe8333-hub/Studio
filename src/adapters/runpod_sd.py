"""RunPod Serverless — SD XL + LoRA 캐릭터 생성 어댑터.

환경변수:
  RUNPOD_API_KEY      — RunPod API 키
  RUNPOD_ENDPOINT_ID  — Serverless 엔드포인트 ID (SD XL + LoRA 구성)
"""
from __future__ import annotations

import base64
import os
import time
from pathlib import Path
from typing import Optional

from loguru import logger

_RUNPOD_BASE = "https://api.runpod.ai/v2"
_POLL_INTERVAL = 3.0
_MAX_WAIT = 300  # 최대 5분 대기


def _api_key() -> str:
    key = os.environ.get("RUNPOD_API_KEY", "")
    if not key:
        raise RuntimeError("RUNPOD_API_KEY 환경 변수 미설정")
    return key


def _endpoint_id() -> str:
    eid = os.environ.get("RUNPOD_ENDPOINT_ID", "")
    if not eid:
        raise RuntimeError("RUNPOD_ENDPOINT_ID 환경 변수 미설정")
    return eid


def generate_character_runpod(
    positive_prompt: str,
    negative_prompt: str,
    seed: int = 42,
    width: int = 512,
    height: int = 768,
    lora_url: Optional[str] = None,
    lora_scale: float = 0.8,
    steps: int = 25,
    guidance_scale: float = 7.5,
) -> Optional[bytes]:
    """RunPod Serverless로 캐릭터 이미지 생성.

    Returns:
        PNG 이미지 bytes, 실패 시 None
    """
    try:
        import requests
    except ImportError:
        logger.warning("[RunPod] requests 패키지 없음 — pip install requests")
        return None

    try:
        api_key = _api_key()
        endpoint_id = _endpoint_id()
    except RuntimeError as e:
        logger.warning(f"[RunPod] {e}")
        return None

    payload: dict = {
        "input": {
            "prompt": positive_prompt,
            "negative_prompt": negative_prompt,
            "width": width,
            "height": height,
            "num_inference_steps": steps,
            "guidance_scale": guidance_scale,
            "seed": seed,
            # SDXL 2.1.1 워커 필수 파라미터
            "scheduler": "K_EULER",
            "num_images": 1,
            "refiner_inference_steps": 40,
            "high_noise_frac": 0.8,
            "strength": 0.3,
            "image_url": None,
        }
    }
    if lora_url:
        payload["input"]["lora_url"] = lora_url
        payload["input"]["lora_scale"] = lora_scale

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    # 잡 제출
    try:
        resp = requests.post(
            f"{_RUNPOD_BASE}/{endpoint_id}/run",
            json=payload,
            headers=headers,
            timeout=30,
        )
        resp.raise_for_status()
        job_id = resp.json().get("id")
        if not job_id:
            logger.warning("[RunPod] 잡 ID 없음")
            return None
        logger.info(f"[RunPod] 잡 제출: {job_id}")
    except Exception as e:
        logger.warning(f"[RunPod] 잡 제출 실패: {e}")
        return None

    # 폴링 (최대 _MAX_WAIT 초)
    deadline = time.time() + _MAX_WAIT
    while time.time() < deadline:
        try:
            status_resp = requests.get(
                f"{_RUNPOD_BASE}/{endpoint_id}/status/{job_id}",
                headers=headers,
                timeout=15,
            )
            status_resp.raise_for_status()
            result = status_resp.json()
            status = result.get("status")

            if status == "COMPLETED":
                output = result.get("output", {})
                # 엔드포인트에 따라 "image" 또는 "images" 키로 반환됨
                image_b64 = output.get("image") or (output.get("images") or [None])[0]
                if not image_b64:
                    logger.warning("[RunPod] 출력에 이미지 없음")
                    return None
                # data:image/png;base64,... 헤더 제거
                if "," in image_b64:
                    image_b64 = image_b64.split(",", 1)[1]
                img_bytes = base64.b64decode(image_b64)
                logger.info(f"[RunPod] 생성 완료: {len(img_bytes):,} bytes")
                return img_bytes

            elif status in ("FAILED", "CANCELLED"):
                logger.warning(
                    f"[RunPod] 잡 실패: {status} | {result.get('error', '')}"
                )
                return None

            logger.debug(f"[RunPod] 상태: {status}")
        except Exception as e:
            logger.warning(f"[RunPod] 폴링 오류: {e}")

        time.sleep(_POLL_INTERVAL)

    logger.warning(f"[RunPod] 타임아웃 ({_MAX_WAIT}초)")
    return None


def generate_character_to_file(
    positive_prompt: str,
    negative_prompt: str,
    output_path: Path,
    seed: int = 42,
    width: int = 512,
    height: int = 768,
    lora_url: Optional[str] = None,
    lora_scale: float = 0.8,
) -> bool:
    """RunPod 캐릭터 생성 후 파일 저장.

    Returns:
        저장 성공 여부. RunPod 미설정이면 False 반환 (graceful fallback).
    """
    img_bytes = generate_character_runpod(
        positive_prompt=positive_prompt,
        negative_prompt=negative_prompt,
        seed=seed,
        width=width,
        height=height,
        lora_url=lora_url,
        lora_scale=lora_scale,
    )
    if img_bytes is None:
        return False

    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(img_bytes)
        return True
    except Exception as e:
        logger.warning(f"[RunPod] 파일 저장 실패: {e}")
        return False
