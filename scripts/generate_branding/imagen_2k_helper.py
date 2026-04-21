"""Imagen 4.0 2K 호출 공통 헬퍼 — Best-of-N variant 생성 패턴.

주요 기능:
- call_imagen_2k: 2K 해상도 suffix 자동 부착 후 Imagen 4.0 단일 호출
- generate_best_of_n: n회 호출 → _candidates/ 폴더에 variant 저장
- select_best_candidate: Claude Vision 채점 대기용 fallback 선택기
- BudgetExceededError: API 호출 50회 초과 시 하드 스톱
"""

import time
from pathlib import Path

from google import genai
from google.genai import types
from loguru import logger

# ---------------------------------------------------------------------------
# 상수 / 모듈 레벨 상태
# ---------------------------------------------------------------------------

MODEL = "imagen-4.0-generate-001"

# 2K 품질 suffix — 모든 프롬프트 끝에 자동 부착
_2K_SUFFIX = (
    "\n2K resolution, ultra-detailed, hand-drawn line quality, "
    "clean edges, print-quality."
)

# API 호출 전역 카운터 (프로세스 수명 기간 누적)
_call_count: int = 0

# 예산 하드 스톱 임계값
_BUDGET_LIMIT: int = 50


# ---------------------------------------------------------------------------
# 예외
# ---------------------------------------------------------------------------


class BudgetExceededError(Exception):
    """API 호출 횟수가 예산 상한(_BUDGET_LIMIT)을 초과했을 때 발생."""


# ---------------------------------------------------------------------------
# 핵심 헬퍼
# ---------------------------------------------------------------------------


def call_imagen_2k(
    client: genai.Client,
    prompt: str,
    aspect: str = "1:1",
) -> bytes:
    """Imagen 4.0 를 2K 설정으로 단일 호출하여 이미지 바이트를 반환한다.

    Args:
        client: 초기화된 genai.Client 인스턴스.
        prompt: 원본 이미지 생성 프롬프트.
        aspect: aspect_ratio 문자열 (예: "1:1", "16:9"). 기본 "1:1".

    Returns:
        생성된 이미지의 raw bytes.

    Raises:
        BudgetExceededError: 누적 API 호출이 _BUDGET_LIMIT을 초과한 경우.
        Exception: Imagen API 호출 실패 시 원본 예외를 재발생.
    """
    global _call_count

    # 예산 체크 — 호출 전에 먼저 검사
    if _call_count >= _BUDGET_LIMIT:
        raise BudgetExceededError(
            f"API 호출 예산 초과: {_call_count}/{_BUDGET_LIMIT}회 소진. "
            "스크립트를 재시작하거나 _BUDGET_LIMIT을 조정하세요."
        )

    full_prompt = prompt + _2K_SUFFIX

    try:
        result = client.models.generate_images(
            model=MODEL,
            prompt=full_prompt,
            config=types.GenerateImagesConfig(
                number_of_images=1,
                aspect_ratio=aspect,
            ),
        )
        image_bytes: bytes = result.generated_images[0].image.image_bytes
        _call_count += 1
        logger.debug(
            f"call_imagen_2k 완료 (누적 호출: {_call_count}/{_BUDGET_LIMIT}, "
            f"크기: {len(image_bytes):,} bytes)"
        )
        return image_bytes
    except BudgetExceededError:
        raise
    except Exception as exc:
        logger.warning(f"call_imagen_2k 실패 (aspect={aspect}): {exc}")
        raise


def generate_best_of_n(
    client: genai.Client,
    prompt: str,
    canonical_path: Path,
    n: int = 3,
    aspect: str = "1:1",
) -> list[Path]:
    """n개의 variant 이미지를 생성하고 _candidates/ 폴더에 저장한다.

    저장 경로 규칙:
        canonical_path.parent.parent / "_candidates" / canonical_path.stem / variant_{i+1}.png

    예시:
        canonical_path = assets/CH1/logo/logo_main.png
        variant 1     = assets/CH1/_candidates/logo_main/variant_1.png

    Args:
        client: 초기화된 genai.Client 인스턴스.
        prompt: 이미지 생성 프롬프트.
        canonical_path: 최종 확정 파일 경로 (stem/parent 참조용).
        n: 생성할 variant 수. 기본 3.
        aspect: aspect_ratio 문자열. 기본 "1:1".

    Returns:
        저장된 variant Path 리스트 (성공한 것만 포함).

    Raises:
        BudgetExceededError: 누적 API 호출이 한도를 초과한 경우.
    """
    candidates_dir = (
        canonical_path.parent.parent / "_candidates" / canonical_path.stem
    )
    candidates_dir.mkdir(parents=True, exist_ok=True)

    saved: list[Path] = []

    for i in range(n):
        variant_path = candidates_dir / f"variant_{i + 1}.png"
        logger.info(
            f"[{i + 1}/{n}] variant 생성 중: {variant_path.name} "
            f"(누적 호출: {_call_count}/{_BUDGET_LIMIT})"
        )
        try:
            image_bytes = call_imagen_2k(client, prompt, aspect=aspect)
            variant_path.write_bytes(image_bytes)
            saved.append(variant_path)
            logger.info(f"  저장 완료 -> {variant_path} ({len(image_bytes):,} bytes)")
        except BudgetExceededError:
            logger.error("예산 초과로 Best-of-N 조기 종료.")
            raise
        except Exception as exc:
            logger.warning(f"  variant_{i + 1} 생성 실패, 건너뜀: {exc}")

        # 마지막 반복이 아닐 때만 sleep (불필요한 대기 방지)
        if i < n - 1:
            time.sleep(1.5)  # API rate limit 방지

    return saved


def select_best_candidate(candidates: list[Path], asset_name: str) -> Path:
    """Best-of-N 결과 중 최선 후보를 반환한다.

    현재 구현은 candidates[0] fallback 반환.
    실제 Claude Vision 채점은 메인 세션에서 수행한다.

    Args:
        candidates: generate_best_of_n 가 반환한 Path 리스트.
        asset_name: 로그 식별용 에셋 이름.

    Returns:
        선택된 Path (현재는 항상 candidates[0]).

    Raises:
        ValueError: candidates 가 비어 있는 경우.
    """
    if not candidates:
        raise ValueError(f"[{asset_name}] candidates 리스트가 비어 있습니다.")

    logger.info(
        f"Best-of-N {asset_name}: {len(candidates)}개 variant 생성 완료, "
        "Claude Vision 채점 대기"
    )
    return candidates[0]
