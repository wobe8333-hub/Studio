"""105장 골든 검증 스크립트.

7채널 × 3 토픽 × 5 표정 = 105장 생성 후 verification/thumbnails/ 에 저장.
사용자가 직접 확인하여 채널별 골든 표정을 선택한다.

실행:
    python scripts/verify_thumbnail_lineup.py
    python scripts/verify_thumbnail_lineup.py --channels CH1 CH2   # 일부 채널만
    python scripts/verify_thumbnail_lineup.py --dry-run             # AI 호출 없이 플레이스홀더만
"""
import argparse
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from loguru import logger

from src.step10.episode_illustration import (
    CHANNEL_MASCOT_PERSONA,
    generate_episode_illustration,
)
from src.step10.thumbnail_generator import _compose_thumbnail, _get_preferred_mode
from PIL import Image

VERIFICATION_DIR = ROOT / "verification" / "thumbnails"

TEST_TOPICS: dict[str, list[str]] = {
    "CH1": ["3가지 충격적인 부자 습관", "월급쟁이가 모르는 세금 절약법", "금리 인상의 진짜 피해자"],
    "CH2": ["지구가 멈추면 어떻게 될까", "블랙홀 안에는 무엇이 있을까", "시간 여행이 불가능한 이유"],
    "CH3": ["집값이 오르는 진짜 이유", "전세 사기 피하는 방법", "아파트 vs 빌라 뭐가 나을까"],
    "CH4": ["왜 우리는 나쁜 사람에게 끌릴까", "자존감이 낮은 사람의 특징", "트라우마에서 벗어나는 법"],
    "CH5": ["버뮤다 삼각지대의 진실", "UFO 목격 사례가 급증한 이유", "사라진 문명 아틀란티스의 비밀"],
    "CH6": ["조선왕조 멸망의 진짜 이유", "임진왜란 최후의 역전극", "세종대왕이 한글을 만든 이유"],
    "CH7": ["6.25 전쟁 최후의 반격", "노르망디 상륙작전의 숨겨진 진실", "태평양 전쟁 일본이 패망한 이유"],
}


def _slug(text: str) -> str:
    return text[:20].replace(" ", "_").replace("/", "_")


def _make_placeholder(topic: str, ch_id: str, expression: str, output_path: Path) -> bool:
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        img = Image.new("RGB", (1920, 1080), color=(40, 40, 60))
        from PIL import ImageDraw
        from src.step10.thumbnail_generator import _load_font
        draw = ImageDraw.Draw(img)
        font = _load_font(60)
        draw.text((60, 460), f"[DRY-RUN] {ch_id} / {expression}", font=font, fill=(200, 200, 200))
        draw.text((60, 540), topic[:40], font=font, fill=(180, 180, 140))
        img.save(str(output_path))
        return True
    except Exception as e:
        logger.warning(f"플레이스홀더 생성 실패: {e}")
        return False


def generate_lineup(
    channels: list[str] | None = None,
    dry_run: bool = False,
) -> dict[str, int]:
    """105장 생성. 반환값: {ch_id: 성공 수}"""
    target_channels = channels or list(TEST_TOPICS.keys())
    results: dict[str, int] = {}

    for ch_id in target_channels:
        topics = TEST_TOPICS.get(ch_id, [])
        if not ch_id in CHANNEL_MASCOT_PERSONA:
            logger.warning(f"[SKIP] {ch_id}: CHANNEL_MASCOT_PERSONA 미등록")
            continue

        info = CHANNEL_MASCOT_PERSONA[ch_id]
        expressions = info.get("expressions", ["surprised", "shocked", "curious", "amazed", "worried"])[:5]
        mode = _get_preferred_mode(ch_id)
        success_count = 0

        logger.info(f"=== {ch_id} 시작 ({len(topics)}토픽 × {len(expressions)}표정) ===")

        for topic_idx, topic in enumerate(topics, 1):
            topic_slug = _slug(topic)
            topic_dir = VERIFICATION_DIR / ch_id / f"topic_{topic_idx:02d}_{topic_slug}"

            for expr_idx, expression in enumerate(expressions, 1):
                out_path = topic_dir / f"variant_{expr_idx:02d}_{expression}.png"
                illust_path = topic_dir / f"_illust_{expression}.png"

                if out_path.exists():
                    logger.info(f"[SKIP 기존] {ch_id} / {topic_slug} / {expression}")
                    success_count += 1
                    continue

                if dry_run:
                    ok = _make_placeholder(topic, ch_id, expression, out_path)
                    if ok:
                        success_count += 1
                    continue

                # AI 일러스트 생성
                run_id = f"verify_{ch_id}_{topic_slug}"
                illust = generate_episode_illustration(
                    ch_id, topic, run_id, illust_path,
                    max_retries=1, expression=expression,
                )

                if illust is None:
                    logger.warning(f"[FAIL] {ch_id} / {expression} → 플레이스홀더")
                    _make_placeholder(topic, ch_id, expression, out_path)
                    continue

                # 3-레이어 합성
                try:
                    topic_dir.mkdir(parents=True, exist_ok=True)
                    base_img = Image.open(illust)
                    result = _compose_thumbnail(base_img, ch_id, topic, mode)
                    result.save(str(out_path))
                    success_count += 1
                    logger.info(f"[OK] {ch_id} variant_{expr_idx:02d}_{expression} → {out_path.name}")
                except Exception as e:
                    logger.warning(f"[FAIL 합성] {e}")
                    _make_placeholder(topic, ch_id, expression, out_path)

                # rate limit 준수 (Gemini Image: 분당 ~8회)
                time.sleep(7)

        results[ch_id] = success_count
        logger.info(f"=== {ch_id} 완료: {success_count}장 ===")

    return results


def print_summary(results: dict[str, int]) -> None:
    total = sum(results.values())
    target = sum(len(TEST_TOPICS.get(ch, [])) * 5 for ch in results)
    print(f"\n{'='*50}")
    print(f"골든 검증 완료: {total}/{target}장")
    print(f"저장 위치: {VERIFICATION_DIR}")
    print(f"{'='*50}")
    for ch, cnt in results.items():
        expected = len(TEST_TOPICS.get(ch, [])) * 5
        print(f"  {ch}: {cnt}/{expected}장")
    print()
    print("다음 단계:")
    print("  1. verification/thumbnails/ 폴더를 파일 탐색기로 확인")
    print("  2. 채널별로 가장 임팩트 있는 표정 1종 선택")
    print("  3. data/thumbnails/golden_expressions.json 에 기록")


def main() -> None:
    parser = argparse.ArgumentParser(description="105장 골든 검증 썸네일 생성")
    parser.add_argument("--channels", nargs="+", choices=list(TEST_TOPICS.keys()),
                        help="특정 채널만 생성 (기본: 전체)")
    parser.add_argument("--dry-run", action="store_true",
                        help="AI 호출 없이 플레이스홀더만 생성")
    args = parser.parse_args()

    if args.dry_run:
        logger.info("DRY-RUN 모드: AI 호출 없이 플레이스홀더 생성")

    results = generate_lineup(channels=args.channels, dry_run=args.dry_run)
    print_summary(results)


if __name__ == "__main__":
    main()
