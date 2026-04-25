# scripts/generate_branding/character_gen.py
"""Gemini Imagen API로 채널 캐릭터 PNG 생성

Usage:
    python scripts/generate_branding/character_gen.py              # 전체 7채널
    python scripts/generate_branding/character_gen.py --channel CH1  # CH1만 (Best-of-3)
"""
import argparse
import io
import os
import shutil
import sys
import time
from pathlib import Path

from dotenv import load_dotenv
from loguru import logger

load_dotenv()

sys.path.insert(0, str(Path(__file__).parent))

from google import genai
from google.genai import types
from gemini_image_gen import (
    generate_best_of_n_with_reference,
    generate_character_sheet,
    generate_with_reference,
)

from config import (
    CHANNEL_COLOR_GUIDE,
    CHANNELS,
    CHANNELS_DIR,
    KAS_ROOT,
    MASCOT_COSTUME,
    STYLE_PREFIX,
)

MODEL = "imagen-4.0-generate-001"

WONEE_SHEET_PATH = KAS_ROOT / "essential_branding" / "CH1_wonee_sheet.png"


def generate_wonee_character_sheet(client: genai.Client) -> bool:
    """Stage 1: 원이 캐릭터 시트 생성.

    10포즈 그리드를 한 장에 담은 레퍼런스 이미지를 생성한다.
    이후 개별 포즈 생성 시 이 시트가 스타일 레퍼런스로 사용된다.

    Returns:
        True if 성공, False if 실패 (실패 시 기존 CH1.png로 폴백)
    """
    logger.info("[Stage 1] 원이 캐릭터 시트 생성 중...")
    ok = generate_character_sheet(WONEE_SHEET_PATH, client=client)
    if ok:
        logger.info(f"[Stage 1] 시트 생성 완료: {WONEE_SHEET_PATH}")
    else:
        logger.warning("[Stage 1] 시트 생성 실패 — 기존 CH1.png로 폴백")
    return ok


def generate_character(
    client: genai.Client, ch_id: str, pose_key: str
) -> bool:
    """단일 캐릭터 포즈 PNG를 생성하고 저장한다.

    CH1: gemini-3.1-flash-image-preview (멀티모달 레퍼런스 입력)
    CH2~7: Imagen 4.0 (텍스트 전용)
    """
    cfg = CHANNELS[ch_id]
    prompt = cfg["character_prompts"][pose_key]
    out_path = CHANNELS_DIR / ch_id / "characters" / f"character_{pose_key}.png"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    # CH1 전용: Gemini 멀티모달 (레퍼런스 이미지 입력으로 두들 스타일 전이)
    if ch_id == "CH1":
        reference = KAS_ROOT / "essential_branding" / "CH1.png"
        ok = generate_with_reference(reference, prompt, out_path)
        time.sleep(1.5)
        return ok

    # CH2~7: Imagen 4.0 (기존 경로 유지)
    try:
        result = client.models.generate_images(
            model=MODEL,
            prompt=prompt,
            config=types.GenerateImagesConfig(
                number_of_images=1,
                aspect_ratio="1:1",
            ),
        )
        image_bytes = result.generated_images[0].image.image_bytes
        out_path.write_bytes(image_bytes)
        logger.info(
            f"[OK] {ch_id}/{pose_key} -> character_{pose_key}.png "
            f"({len(image_bytes):,} bytes)"
        )
        return True
    except Exception as e:
        logger.error(f"[ERR] {ch_id}/{pose_key}: {e}")
        return False
    finally:
        time.sleep(1.5)  # API rate limit 방지


def generate_ch1_characters(client: genai.Client) -> dict[str, bool]:
    """Stage 2: 원이 10포즈를 Best-of-3으로 생성.

    캐릭터 시트(CH1_wonee_sheet.png)를 스타일 레퍼런스로 사용한다.
    시트가 없으면 기존 CH1.png로 폴백한다.

    Returns:
        {pose_key: True/False} — 생성 성공 여부
    """
    cfg = CHANNELS["CH1"]
    # 레퍼런스: 새 시트 우선, 없으면 기존 CH1.png
    reference = (
        WONEE_SHEET_PATH
        if WONEE_SHEET_PATH.exists()
        else KAS_ROOT / "essential_branding" / "CH1.png"
    )
    logger.info(f"[Stage 2] 레퍼런스: {reference.name}")

    results: dict[str, bool] = {}
    for pose in cfg["characters"]:
        prompt = cfg["character_prompts"][pose]
        canonical_path = CHANNELS_DIR / "CH1" / "characters" / f"character_{pose}.png"
        canonical_path.parent.mkdir(parents=True, exist_ok=True)

        logger.info(f"[CH1/{pose}] Best-of-3 생성 중...")
        try:
            variants = generate_best_of_n_with_reference(
                reference, prompt, canonical_path, n=3, client=client
            )
            if variants:
                # variant_1.png를 canonical_path로 복사 (첫 번째 variant 사용)
                shutil.copy2(variants[0], canonical_path)
                results[pose] = True
                logger.info(f"[CH1/{pose}] 완료 ({len(variants)}개 variant 생성)")
            else:
                results[pose] = False
                logger.warning(f"[CH1/{pose}] 실패 (variant 없음)")
        except Exception as e:
            results[pose] = False
            logger.error(f"[CH1/{pose}] 오류: {e}")
        time.sleep(1.5)

    return results


def run_all(channels: list[str] | None = None) -> None:
    """모든 채널 또는 지정 채널의 캐릭터 PNG를 순차 생성한다.

    CH1은 Best-of-3 variant 경로, CH2~7은 표준 단일 생성 경로.
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        logger.error("GEMINI_API_KEY 환경변수가 없습니다.")
        sys.exit(1)

    client = genai.Client(api_key=api_key)
    logger.info(f"Gemini Imagen API 준비 완료 (모델: {MODEL})")

    target = channels or list(CHANNELS.keys())
    total = 0
    success = 0
    failures: list[str] = []

    for ch_id in target:
        cfg = CHANNELS[ch_id]
        logger.info(f"\n[{ch_id}] {cfg['name']} ({cfg['domain']}) 캐릭터 생성 시작...")

        if ch_id == "CH1":
            # Stage 1: 캐릭터 시트 생성 (없는 경우에만)
            if not WONEE_SHEET_PATH.exists():
                generate_wonee_character_sheet(client)
            else:
                logger.info(f"[Stage 1] 기존 시트 재사용: {WONEE_SHEET_PATH.name}")
            # Stage 2: 개별 포즈 10종 Best-of-3
            ch1_results = generate_ch1_characters(client)
            for pose, ok in ch1_results.items():
                total += 1
                if ok:
                    success += 1
                else:
                    failures.append(f"CH1/{pose}")
        else:
            # CH2~7: 표준 단일 생성
            for pose in cfg["characters"]:
                total += 1
                if generate_character(client, ch_id, pose):
                    success += 1
                else:
                    failures.append(f"{ch_id}/{pose}")

    logger.info(f"\n[완료] {success}/{total}개 캐릭터 PNG/variant 생성")
    if failures:
        logger.warning(f"[실패 목록] {failures}")
    else:
        logger.info("[실패 없음] 모든 포즈 생성 성공")


def generate_channel_mascot(
    channel_id: str,
    overwrite: bool = False,
) -> tuple[Path, Path]:
    """채널 마스코트 PNG 생성 — 인트로/아웃트로·QC 레이어 공용 이미지.

    base_plain.png를 레퍼런스로 받아 채널별 의상·컬러가 적용된 마스코트를 생성한다.
    성공 시 동일 이미지를 두 경로에 저장:
      - assets/channels/{ch}/characters/character_default.png  (인트로/아웃트로용)
      - assets/characters/{ch}/narrator_ref.png               (QC layer1 일관성 검증용)

    Args:
        channel_id: 채널 ID (예: "CH1")
        overwrite: 이미 파일이 존재해도 덮어쓸지 여부 (기본 False)

    Returns:
        (character_default_path, narrator_ref_path) 튜플

    Raises:
        RuntimeError: 3회 재시도 후 모두 실패 시
    """
    # 출력 경로 설정
    char_default = CHANNELS_DIR / channel_id / "characters" / "character_default.png"
    narrator_ref = KAS_ROOT / "assets" / "channels" / channel_id / "characters" / "narrator_ref.png"

    # 이미 존재하고 덮어쓰기 비활성화 → 조기 반환
    if char_default.exists() and narrator_ref.exists() and not overwrite:
        logger.info(f"[{channel_id}] 마스코트 이미 존재 — 건너뜀 (--force 사용 시 재생성)")
        return char_default, narrator_ref

    # base_plain.png 경로 확인
    base_plain = KAS_ROOT / "assets" / "shared" / "base_plain.png"
    if not base_plain.exists():
        raise RuntimeError(
            f"base_plain.png 없음: {base_plain}\n"
            "assets/shared/base_plain.png 파일이 필요합니다."
        )

    # 프롬프트 조합: STYLE_PREFIX + 의상 + 포즈 + 컬러 가이드
    costume = MASCOT_COSTUME.get(channel_id, "casual outfit")
    color_guide = CHANNEL_COLOR_GUIDE.get(channel_id, "")
    prompt = (
        f"{STYLE_PREFIX}"
        f"Outfit: {costume}. "
        "Neutral front-facing pose, friendly smile. "
        f"{color_guide}"
    )

    # 출력 디렉토리 생성
    char_default.parent.mkdir(parents=True, exist_ok=True)
    narrator_ref.parent.mkdir(parents=True, exist_ok=True)

    # 최대 3회 재시도
    last_error: Exception | None = None
    for attempt in range(1, 4):
        try:
            logger.info(f"[{channel_id}] 마스코트 생성 시도 {attempt}/3...")
            ok = generate_with_reference(base_plain, prompt, char_default)
            if not ok:
                raise RuntimeError("generate_with_reference 반환값이 False")
            # narrator_ref.png = character_default.png 동일 이미지 복사
            shutil.copy2(char_default, narrator_ref)
            logger.info(
                f"[{channel_id}] 마스코트 생성 완료\n"
                f"  character_default → {char_default}\n"
                f"  narrator_ref      → {narrator_ref}"
            )
            return char_default, narrator_ref
        except Exception as e:
            last_error = e
            logger.warning(f"[{channel_id}] 시도 {attempt}/3 실패: {e}")
            if attempt < 3:
                time.sleep(3.0)

    raise RuntimeError(
        f"[{channel_id}] 마스코트 생성 3회 실패. 마지막 오류: {last_error}"
    )


if __name__ == "__main__":
    # Windows 콘솔 인코딩 UTF-8 설정 (직접 실행 시에만 적용)
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description="채널 캐릭터 PNG 생성")
    parser.add_argument("--channel", default=None, help="단일 채널 ID (예: CH1)")
    args = parser.parse_args()
    channels = [args.channel] if args.channel else None
    run_all(channels)
