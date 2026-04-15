# scripts/generate_branding/nano_banana_helper.py
"""Gemini 멀티모달 이미지 생성 헬퍼.

Imagen 4.0 (텍스트 전용) 대신 reference 이미지를 함께 전달해
두들 스타일 전이를 시도한다.

사용법:
    from nano_banana_helper import generate_with_reference
    ok = generate_with_reference(
        reference_image_path=Path("essential_branding/CH1.png"),
        prompt="cute doodle economist character...",
        output_path=Path("assets/channels/CH1/characters/character_explain.png"),
    )
"""
import os
import sys
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from loguru import logger

load_dotenv()

from google import genai
from google.genai import types

# ─── 모델 상수 ────────────────────────────────────────────────────────────────
# gemini-3.1-flash-image-preview: 사용자 선택 확정 모델 (두들 스타일 재현 우수)
MODEL_MULTIMODAL = "gemini-3.1-flash-image-preview"

# ─── 예산 하드스톱 ────────────────────────────────────────────────────────────
_call_count = 0
BUDGET_LIMIT = 30  # 프로세스 수명 기간 최대 API 호출 수


class BudgetExceededError(Exception):
    """API 호출 횟수가 예산 상한을 초과했을 때 발생."""


def _make_client() -> genai.Client:
    api_key = os.environ.get("GEMINI_API_KEY", "")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY 환경 변수 미설정")
    return genai.Client(api_key=api_key)


def generate_with_reference(
    reference_image_path: Path,
    prompt: str,
    output_path: Path,
    *,
    client: Optional[genai.Client] = None,
) -> bool:
    """reference 이미지 스타일을 참고해 새 이미지를 생성한다.

    Args:
        reference_image_path: 스타일 참고용 레퍼런스 PNG (essential_branding/CH1.png 등)
        prompt: 생성할 캐릭터/자산 설명
        output_path: 저장 경로
        client: 재사용 클라이언트 (None이면 신규 생성)

    Returns:
        True if 성공, False if 실패

    Raises:
        BudgetExceededError: API 호출 상한 초과 시
    """
    global _call_count
    if _call_count >= BUDGET_LIMIT:
        raise BudgetExceededError(f"API 호출 {BUDGET_LIMIT}회 초과 — 하드스톱")

    if client is None:
        client = _make_client()

    # reference 이미지 읽기
    ref_bytes = reference_image_path.read_bytes()
    ref_part = types.Part.from_bytes(data=ref_bytes, mime_type="image/png")

    full_prompt = (
        "Replicate EXACTLY the flat 2D hand-drawn doodle illustration style shown "
        "in the reference image. Same line weight (2-3px thin black marker), "
        "pure white background (#FFFFFF), same wobbly hand-drawn lines, "
        "same flat coloring with NO gradients or shadows, NO shading, NO 3D effects. "
        f"Now generate: {prompt}. "
        "IMPORTANT ANATOMY RULES: exactly 2 arms, exactly 2 hands, exactly 2 legs — "
        "NO extra limbs, NO third arm, NO floating hands. "
        "Output ONLY the character on pure white background, NO text, NO labels, NO hex codes."
    )

    try:
        response = client.models.generate_content(
            model=MODEL_MULTIMODAL,
            contents=[ref_part, full_prompt],
            config=types.GenerateContentConfig(
                response_modalities=["IMAGE"],
            ),
        )
        _call_count += 1
        logger.debug(f"generate_with_reference 완료 (누적 호출: {_call_count}/{BUDGET_LIMIT})")

        # 이미지 bytes 추출
        for part in response.candidates[0].content.parts:
            if part.inline_data and part.inline_data.mime_type.startswith("image/"):
                output_path.parent.mkdir(parents=True, exist_ok=True)
                output_path.write_bytes(part.inline_data.data)
                logger.info(
                    f"[OK] {output_path.name} ({len(part.inline_data.data):,} bytes)"
                )
                return True

        # 이미지 없이 텍스트만 반환된 경우
        text_parts = [
            p.text for p in response.candidates[0].content.parts if hasattr(p, "text")
        ]
        logger.warning(
            f"[WARN] 이미지 응답 없음. 텍스트 응답: {' '.join(text_parts)[:200]}"
        )
        return False

    except BudgetExceededError:
        raise
    except Exception as e:
        logger.error(f"[ERR] generate_with_reference: {e}")
        return False


def generate_best_of_n_with_reference(
    reference_image_path: Path,
    prompt: str,
    canonical_path: Path,
    n: int = 3,
    *,
    client: Optional[genai.Client] = None,
) -> list[Path]:
    """reference 이미지 스타일로 n개 variant를 생성해 _candidates/ 폴더에 저장한다.

    Args:
        reference_image_path: 스타일 참고용 레퍼런스 PNG
        prompt: 생성할 이미지 설명
        canonical_path: 최종 확정 파일 경로 (stem/parent 참조용)
        n: 생성할 variant 수 (기본 3)
        client: 재사용 클라이언트

    Returns:
        저장된 variant Path 리스트 (성공한 것만 포함)
    """
    import time

    if client is None:
        client = _make_client()

    candidates_dir = (
        canonical_path.parent.parent / "_candidates" / canonical_path.stem
    )
    candidates_dir.mkdir(parents=True, exist_ok=True)

    saved: list[Path] = []
    for i in range(n):
        variant_path = candidates_dir / f"variant_{i + 1}.png"
        logger.info(f"[{i + 1}/{n}] variant 생성 중: {variant_path.name}")
        try:
            ok = generate_with_reference(
                reference_image_path, prompt, variant_path, client=client
            )
            if ok:
                saved.append(variant_path)
        except BudgetExceededError:
            logger.error("예산 초과로 Best-of-N 조기 종료.")
            raise

        if i < n - 1:
            time.sleep(1.5)  # API rate limit 방지

    return saved
