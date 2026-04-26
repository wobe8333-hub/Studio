# scripts/generate_branding/gemini_image_gen.py
"""Gemini 멀티모달 이미지 생성 헬퍼.

레퍼런스 이미지를 함께 전달해 두들 스타일 전이를 구현한다.
브랜딩 에셋(로고/마스코트/인트로/아웃트로) 생성에 사용.

사용법:
    from gemini_image_gen import generate_with_reference, generate_image
    ok = generate_with_reference(
        reference_image_path=Path("assets/characters/base_plain.png"),
        prompt="채널 마스코트 묘사...",
        output_path=Path("assets/channels/CH1/characters/character_default.png"),
    )
"""
import os
import sys
import time
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from loguru import logger

load_dotenv()

from google import genai
from google.genai import types

# ─── 모델 상수 ────────────────────────────────────────────────────────────────
# gemini-3-pro-image-preview: Pro 품질 모델 (캐릭터 시트 + 포즈 생성)
MODEL_MULTIMODAL = "gemini-3-pro-image-preview"

# ─── 예산 하드스톱 ────────────────────────────────────────────────────────────
_call_count = 0
BUDGET_LIMIT = 500  # 7채널×50종 로고 본 생성용


class BudgetExceededError(Exception):
    """API 호출 횟수가 예산 상한을 초과했을 때 발생."""


def _make_client() -> genai.Client:
    api_key = os.environ.get("GEMINI_API_KEY", "")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY 환경 변수 미설정")
    return genai.Client(api_key=api_key)


def generate_with_reference(  # noqa: PLR0913
    reference_image_path: Path,
    prompt: str,
    output_path: Path,
    *,
    scene_mode: bool = False,
    client: Optional[genai.Client] = None,
) -> bool:
    """reference 이미지 스타일을 참고해 새 이미지를 생성한다.

    Args:
        reference_image_path: 스타일 참고용 레퍼런스 PNG
        prompt: 생성할 캐릭터/씬 설명
        output_path: 저장 경로
        scene_mode: True면 배경 있는 씬 생성 (로고/인트로/아웃트로용)
                    False면 캐릭터만 흰 배경으로 생성 (마스코트용, 기본값)
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

    if scene_mode:
        # 배경 있는 씬 (로고/인트로/아웃트로)
        full_prompt = (
            "Use the flat 2D hand-drawn doodle illustration style shown in the reference image "
            "for the character — same line weight (2-3px thin black marker), same wobbly hand-drawn lines, "
            "same flat coloring with NO gradients or shadows, NO shading, NO 3D effects. "
            f"Now generate this scene: {prompt}. "
            "STRICT ANATOMY for any character: exactly 2 arms, exactly 2 legs — NO extra limbs. "
            "CRITICAL TEXT BAN: NO text, NO letters, NO numbers, NO labels, NO hex codes, "
            "NO symbols, NO glyphs of any kind anywhere in the image. "
            "All icons and shapes must be pure geometric forms only. "
            "Render the complete scene exactly as described with the specified background and all elements."
        )
    else:
        # 캐릭터만 흰 배경 (마스코트)
        full_prompt = (
            "Replicate EXACTLY the flat 2D hand-drawn doodle illustration style shown "
            "in the reference image. Same line weight (2-3px thin black marker), "
            "pure white background (#FFFFFF), same wobbly hand-drawn lines, "
            "same flat coloring with NO gradients or shadows, NO shading, NO 3D effects. "
            f"Now generate: {prompt}. "
            "FULL BODY: show the entire character from head to feet, standing upright. "
            "STRICT ANATOMY: exactly 2 arms, exactly 2 legs — NO extra limbs. "
            "CRITICAL TEXT BAN: NO text, NO letters, NO numbers, NO labels, NO hex codes, "
            "NO symbols, NO glyphs of any kind anywhere in the image. "
            "All icons and shapes must be pure geometric forms only. "
            "Output ONLY the character on pure white background."
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


def generate_with_multi_reference(
    reference_image_paths: list[Path],
    prompt: str,
    output_path: Path,
    *,
    client: Optional[genai.Client] = None,
    image_config: Optional[types.ImageConfig] = None,
) -> bool:
    """여러 레퍼런스 이미지를 동시에 전달해 스타일 패턴을 학습 후 새 이미지를 생성한다.

    Args:
        reference_image_paths: 스타일 예시 PNG 목록 (few-shot)
        prompt: 생성할 이미지 설명
        output_path: 저장 경로
        client: 재사용 클라이언트
        image_config: 출력 이미지 크기/비율 설정 (예: types.ImageConfig(aspect_ratio="16:9", image_size="2K"))

    Returns:
        True if 성공, False if 실패
    """
    global _call_count
    if _call_count >= BUDGET_LIMIT:
        raise BudgetExceededError(f"API 호출 {BUDGET_LIMIT}회 초과 — 하드스톱")

    if client is None:
        client = _make_client()

    # 레퍼런스 이미지들을 parts로 변환
    ref_parts = []
    for ref_path in reference_image_paths:
        ref_bytes = ref_path.read_bytes()
        ref_parts.append(types.Part.from_bytes(data=ref_bytes, mime_type="image/png"))

    contents = ref_parts + [prompt]

    try:
        response = client.models.generate_content(
            model=MODEL_MULTIMODAL,
            contents=contents,
            config=types.GenerateContentConfig(
                response_modalities=["IMAGE"],
                image_config=image_config,
            ),
        )
        _call_count += 1
        logger.debug(f"generate_with_multi_reference 완료 (누적 호출: {_call_count}/{BUDGET_LIMIT})")

        for part in response.candidates[0].content.parts:
            if part.inline_data and part.inline_data.mime_type.startswith("image/"):
                output_path.parent.mkdir(parents=True, exist_ok=True)
                output_path.write_bytes(part.inline_data.data)
                logger.info(f"[OK] {output_path.name} ({len(part.inline_data.data):,} bytes)")
                return True

        text_parts = [
            p.text for p in response.candidates[0].content.parts if hasattr(p, "text")
        ]
        logger.warning(f"[WARN] 이미지 응답 없음. 텍스트: {' '.join(text_parts)[:200]}")
        return False

    except BudgetExceededError:
        raise
    except Exception as e:
        logger.error(f"[ERR] generate_with_multi_reference: {e}")
        return False


def generate_best_of_n_multi_reference(
    reference_image_paths: list[Path],
    prompt: str,
    output_dir: Path,
    n: int = 5,
    *,
    client: Optional[genai.Client] = None,
) -> list[Path]:
    """여러 레퍼런스 기반 Best-of-N 생성."""
    if client is None:
        client = _make_client()

    output_dir.mkdir(parents=True, exist_ok=True)
    saved: list[Path] = []

    for i in range(n):
        variant_path = output_dir / f"variant_{i + 1}.png"
        logger.info(f"[{i + 1}/{n}] multi-ref variant 생성 중: {variant_path.name}")
        try:
            ok = generate_with_multi_reference(
                reference_image_paths, prompt, variant_path, client=client,
            )
            if ok:
                saved.append(variant_path)
        except BudgetExceededError:
            logger.error("예산 초과로 Best-of-N 조기 종료.")
            raise

        if i < n - 1:
            time.sleep(1.5)

    return saved


def generate_best_of_n_with_reference(
    reference_image_path: Path,
    prompt: str,
    canonical_path: Path,
    n: int = 3,
    *,
    scene_mode: bool = False,
    client: Optional[genai.Client] = None,
) -> list[Path]:
    """reference 이미지 스타일로 n개 variant를 생성해 _candidates/ 폴더에 저장한다.

    Args:
        reference_image_path: 스타일 참고용 레퍼런스 PNG
        prompt: 생성할 이미지 설명
        canonical_path: 최종 확정 파일 경로 (stem/parent 참조용)
        n: 생성할 variant 수 (기본 3)
        scene_mode: True면 배경 있는 씬 생성 (로고/인트로/아웃트로용)
        client: 재사용 클라이언트

    Returns:
        저장된 variant Path 리스트 (성공한 것만 포함)
    """
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
                reference_image_path, prompt, variant_path,
                scene_mode=scene_mode, client=client,
            )
            if ok:
                saved.append(variant_path)
        except BudgetExceededError:
            logger.error("예산 초과로 Best-of-N 조기 종료.")
            raise

        if i < n - 1:
            time.sleep(1.5)  # API rate limit 방지

    return saved


def generate_image(
    prompt: str,
    output_path: Path,
    *,
    client: Optional[genai.Client] = None,
) -> bool:
    """레퍼런스 없이 텍스트 프롬프트만으로 이미지를 생성한다.

    Args:
        prompt: 생성할 이미지 설명
        output_path: 저장 경로
        client: 재사용 클라이언트 (None이면 신규 생성)

    Returns:
        True if 성공, False if 실패
    """
    global _call_count
    if _call_count >= BUDGET_LIMIT:
        raise BudgetExceededError(f"API 호출 {BUDGET_LIMIT}회 초과 — 하드스톱")

    if client is None:
        client = _make_client()

    try:
        response = client.models.generate_content(
            model=MODEL_MULTIMODAL,
            contents=[prompt],
            config=types.GenerateContentConfig(
                response_modalities=["IMAGE"],
            ),
        )
        _call_count += 1
        logger.debug(f"generate_image 완료 (누적 호출: {_call_count}/{BUDGET_LIMIT})")

        for part in response.candidates[0].content.parts:
            if part.inline_data and part.inline_data.mime_type.startswith("image/"):
                output_path.parent.mkdir(parents=True, exist_ok=True)
                output_path.write_bytes(part.inline_data.data)
                logger.info(f"[OK] {output_path.name} ({len(part.inline_data.data):,} bytes)")
                return True

        text_parts = [
            p.text for p in response.candidates[0].content.parts if hasattr(p, "text")
        ]
        logger.warning(f"[WARN] 이미지 응답 없음. 텍스트: {' '.join(text_parts)[:200]}")
        return False

    except BudgetExceededError:
        raise
    except Exception as e:
        logger.error(f"[ERR] generate_image: {e}")
        return False


def generate_best_of_n(
    prompt: str,
    canonical_path: Path,
    n: int = 3,
    *,
    client: Optional[genai.Client] = None,
) -> list[Path]:
    """레퍼런스 없이 Best-of-N 생성 → _candidates/ 폴더에 저장한다.

    Args:
        prompt: 생성할 이미지 설명
        canonical_path: 최종 확정 파일 경로 (stem/parent 참조용)
        n: 생성할 variant 수 (기본 3)
        client: 재사용 클라이언트

    Returns:
        저장된 variant Path 리스트 (성공한 것만 포함)
    """
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
            ok = generate_image(prompt, variant_path, client=client)
            if ok:
                saved.append(variant_path)
        except BudgetExceededError:
            logger.error("예산 초과로 Best-of-N 조기 종료.")
            raise

        if i < n - 1:
            time.sleep(1.5)

    return saved


def generate_character_sheet(
    output_path: Path,
    *,
    client: Optional[genai.Client] = None,
) -> bool:
    """원이 캐릭터 시트를 생성한다 (3단계 파이프라인 Stage 1).

    10개 포즈를 2×5 그리드로 한 장에 보여주는 캐릭터 디자인 시트를 생성한다.
    이 시트를 이후 개별 포즈 생성의 레퍼런스로 사용한다.

    Args:
        output_path: 시트 PNG 저장 경로 (보통 essential_branding/CH1_wonee_sheet.png)
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

    # NOTE: 이 시트 프롬프트는 레퍼런스 용도로 숫자(1-10)를 의도적으로 허용한다.
    # generate_with_reference의 full_prompt "NO numbers" 규칙과 달리
    # 포즈 번호는 시트를 레퍼런스로 쓸 때 AI가 구별하는 데 도움을 준다.
    sheet_prompt = (
        "Character design reference sheet for kawaii human doodle mascot '원이'. "
        "CHARACTER ANATOMY (use consistently across all 10 poses): "
        "large perfectly round circle head; short visible neck; "
        "rectangular torso with clear shoulder line slightly wider than head (like a simple white jacket); "
        "two arms from shoulders — upper arm + forearm with small rounded hand and index finger; "
        "two short legs with small rounded feet. "
        "FACE — two small round black dot eyes with white highlight dot, "
        "wide upward-curved open smile, soft golden blush circles on both cheeks. "
        "CROWN — gold (#F4C420) crown on top of round head, three rounded bumps, "
        "small lowercase 'w' written in dark color on front face of crown. "
        "Thin black outline 2px, pure white fill, pure white background, flat coloring, no shading. "
        "Show exactly 10 poses in a 2-column 5-row grid: "
        "(1) standing neutral arms relaxed at sides, "
        "(2) right arm raised pointing index finger upward (explain), "
        "(3) both arms spread wide to sides in shock (surprised), "
        "(4) jumping with both arms raised in V shape (happy), "
        "(5) body drooped forward arms hanging down with teardrop (sad), "
        "(6) one arm up with finger touching cheek (thinking), "
        "(7) one arm raised with thumbs-up (victory), "
        "(8) both arms pushed forward palms out (warning), "
        "(9) seated cross-legged (sit), "
        "(10) leaning forward in sprint sideways view (run). "
        "Small numeral 1-10 beneath each pose. "
        "ONLY text allowed: small numbers 1-10 and 'w' on crown. "
        "Gold #F4C420, outline #333333."
    )

    try:
        response = client.models.generate_content(
            model=MODEL_MULTIMODAL,
            contents=[sheet_prompt],
            config=types.GenerateContentConfig(
                response_modalities=["IMAGE"],
            ),
        )
        _call_count += 1
        logger.debug(f"generate_character_sheet 완료 (누적 호출: {_call_count}/{BUDGET_LIMIT})")

        for part in response.candidates[0].content.parts:
            if part.inline_data and part.inline_data.mime_type.startswith("image/"):
                output_path.parent.mkdir(parents=True, exist_ok=True)
                output_path.write_bytes(part.inline_data.data)
                logger.info(
                    f"[OK] 캐릭터 시트 생성: {output_path.name} ({len(part.inline_data.data):,} bytes)"
                )
                return True

        text_parts = [
            p.text for p in response.candidates[0].content.parts if hasattr(p, "text")
        ]
        logger.warning(f"[WARN] 시트 이미지 응답 없음. 텍스트: {' '.join(text_parts)[:200]}")
        return False

    except BudgetExceededError:
        raise
    except Exception as e:
        logger.error(f"[ERR] generate_character_sheet: {e}")
        return False
