"""
STEP 08 — Stable Diffusion XL + LoRA 이미지 생성기.

Phase 5 추가:
  GPU 감지 → SD XL + LoRA (GPU 있을 때)
  GPU 없음  → Gemini 이미지 폴백

캐릭터 일관성: character_manager.py의 채널별 LoRA + 시드 사용
"""

from pathlib import Path
from typing import Any, List, Optional

from loguru import logger

from src.step08.character_manager import build_character_prompt, get_lora_path

_SD_PIPELINE: Optional[Any] = None  # SD XL 파이프라인 싱글턴 (최초 1회만 로드)


def _detect_gpu() -> bool:
    """GPU 사용 가능 여부 확인"""
    try:
        import torch
        return torch.cuda.is_available()
    except Exception:
        # ImportError 외에도 OSError (WinError 1114 DLL 로드 실패) 등 처리
        return False


def _get_sd_pipeline(device: str, dtype: Any) -> Any:
    """SD XL 파이프라인 싱글턴 반환 — 최초 1회만 로드 후 재사용."""
    global _SD_PIPELINE
    if _SD_PIPELINE is None:
        from diffusers import StableDiffusionXLPipeline
        _SD_PIPELINE = StableDiffusionXLPipeline.from_pretrained(
            "stabilityai/stable-diffusion-xl-base-1.0",
            torch_dtype=dtype,
            use_safetensors=True,
            variant="fp16" if device == "cuda" else None,
        )
        _SD_PIPELINE = _SD_PIPELINE.to(device)
        _SD_PIPELINE.enable_attention_slicing()
        logger.info("[SD] 파이프라인 최초 로드 완료 (싱글턴 캐싱)")
    return _SD_PIPELINE


def _generate_sd_image(
    prompt: str,
    negative_prompt: str,
    output_path: Path,
    seed: int = 42,
    width: int = 1920,
    height: int = 1080,
    lora_path: Optional[Path] = None,
) -> bool:
    """SD XL로 단일 이미지 생성."""
    try:
        import torch

        device = "cuda" if torch.cuda.is_available() else "cpu"
        dtype = torch.float16 if device == "cuda" else torch.float32

        # 파이프라인 싱글턴 (재사용으로 모델 재로드 방지)
        pipe = _get_sd_pipeline(device, dtype)

        # LoRA 로드
        if lora_path and lora_path.exists():
            try:
                pipe.load_lora_weights(str(lora_path.parent), weight_name=lora_path.name)
                logger.debug(f"[SD] LoRA 로드: {lora_path.name}")
            except Exception as lora_err:
                logger.warning(f"[SD] LoRA 로드 실패 (스킵): {lora_err}")

        # 이미지 생성
        generator = torch.Generator(device=device).manual_seed(seed)
        result = pipe(
            prompt=prompt,
            negative_prompt=negative_prompt,
            width=width,
            height=height,
            num_inference_steps=25,
            guidance_scale=7.5,
            generator=generator,
        )

        output_path.parent.mkdir(parents=True, exist_ok=True)
        result.images[0].save(str(output_path))
        logger.debug(f"[SD] 이미지 생성 완료: {output_path.name}")
        return True

    except Exception as e:
        logger.debug(f"[SD] SD XL 생성 실패: {e}")
        return False


def _generate_gemini_image(prompt: str, output_path: Path) -> bool:
    """Gemini 이미지 생성 폴백."""
    try:
        import base64

        import google.generativeai as genai

        from src.core.config import GEMINI_API_KEY, GEMINI_IMAGE_MODEL

        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel(GEMINI_IMAGE_MODEL)

        # Gemini 이미지 생성
        resp = model.generate_content(
            [f"Generate a cute anime-style illustration: {prompt}"],
            generation_config=genai.GenerationConfig(
                response_mime_type="image/png",
            ),
        )

        output_path.parent.mkdir(parents=True, exist_ok=True)
        # 이미지 데이터 저장
        for part in resp.parts:
            if hasattr(part, "inline_data") and part.inline_data:
                image_data = base64.b64decode(part.inline_data.data)
                output_path.write_bytes(image_data)
                logger.debug(f"[SD-Gemini] 이미지 생성 완료: {output_path.name}")
                return True

        return False
    except Exception as e:
        logger.debug(f"[SD-Gemini] Gemini 이미지 실패: {e}")
        return False


def generate_scene_images(
    channel_id: str,
    sections: List[dict],
    output_dir: Path,
    use_gpu: bool = None,
) -> List[Path]:
    """
    섹션별 캐릭터 장면 이미지 생성.

    Args:
        channel_id: CH1~CH7
        sections: script["sections"] 리스트
        output_dir: 이미지 저장 디렉토리
        use_gpu: None이면 자동 감지

    Returns:
        생성된 이미지 파일 경로 리스트
    """
    has_gpu = _detect_gpu() if use_gpu is None else use_gpu
    lora_path = get_lora_path(channel_id)
    output_dir.mkdir(parents=True, exist_ok=True)

    logger.info(f"[SD] {channel_id}: {len(sections)}개 섹션 이미지 생성 시작 (GPU={has_gpu})")

    generated: List[Path] = []
    for i, section in enumerate(sections):
        out_path = output_dir / f"scene_{i:03d}.png"
        if out_path.exists():
            generated.append(out_path)
            continue

        # character_directions에서 표정/포즈 추출
        char_dir = section.get("character_directions", {})
        expression = char_dir.get("expression", "happy")
        pose = char_dir.get("pose", "explaining")
        scene_ctx = section.get("animation_prompt", "")[:100]

        prompts = build_character_prompt(channel_id, expression, pose, scene_ctx)

        # SD XL (GPU 있을 때) 또는 Gemini 폴백
        ok = False
        if has_gpu and lora_path:
            ok = _generate_sd_image(
                prompt=prompts["positive"],
                negative_prompt=prompts["negative"],
                output_path=out_path,
                seed=prompts["seed"] + i,
                lora_path=lora_path,
            )

        if not ok:
            # Gemini 폴백
            ok = _generate_gemini_image(prompts["positive"], out_path)

        if ok:
            generated.append(out_path)
        else:
            logger.warning(f"[SD] 섹션 {i} 이미지 생성 실패")

    logger.info(f"[SD] {channel_id}: {len(generated)}/{len(sections)} 이미지 생성 완료")
    return generated
