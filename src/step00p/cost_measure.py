"""
cost_measure.py
STEP 00-P 파일럿 API 비용 실측 모듈.
Gemini API 토큰 소모량 및 비용을 추적하고
월 48편 기준 운영비를 산출한다.
"""

import logging
from src.core.ssot import now_iso

logger = logging.getLogger(__name__)

# Gemini 2.5 Flash 기준 단가 (KRW, 2025년 3월 기준 환율 1 USD = 1,350원 적용)
# input: $0.075/1M tokens → 0.075 * 1350 / 1_000_000 = 0.10125원/token
# output: $0.30/1M tokens → 0.30 * 1350 / 1_000_000 = 0.405원/token
GEMINI_TEXT_INPUT_KRW_PER_TOKEN  = 0.10125
GEMINI_TEXT_OUTPUT_KRW_PER_TOKEN = 0.405

# Gemini 이미지 생성 단가: $0.04/image → 0.04 * 1350 = 54원/장
GEMINI_IMAGE_KRW_PER_IMAGE = 54.0

# 월 운영 기준
MONTHLY_TARGET_VIDEOS = 48
WORKING_DAYS_PER_MONTH = 22


def calc_text_cost(input_tokens: int, output_tokens: int) -> float:
    """텍스트 생성 비용 계산 (KRW)."""
    cost = (input_tokens  * GEMINI_TEXT_INPUT_KRW_PER_TOKEN +
            output_tokens * GEMINI_TEXT_OUTPUT_KRW_PER_TOKEN)
    return round(cost, 2)


def calc_image_cost(image_count: int) -> float:
    """이미지 생성 비용 계산 (KRW)."""
    return round(image_count * GEMINI_IMAGE_KRW_PER_IMAGE, 2)


def calc_total_video_cost(
    script_input_tokens: int,
    script_output_tokens: int,
    manim_input_tokens: int,
    manim_output_tokens: int,
    title_input_tokens: int,
    title_output_tokens: int,
    image_count: int,
) -> dict:
    """
    단일 영상 생성 전체 비용 산출.
    반환값: {
        "script_cost_krw": float,
        "manim_cost_krw": float,
        "title_tag_cost_krw": float,
        "image_cost_krw": float,
        "total_krw": float,
    }
    """
    script_cost    = calc_text_cost(script_input_tokens, script_output_tokens)
    manim_cost     = calc_text_cost(manim_input_tokens, manim_output_tokens)
    title_cost     = calc_text_cost(title_input_tokens, title_output_tokens)
    image_cost     = calc_image_cost(image_count)
    total          = round(script_cost + manim_cost + title_cost + image_cost, 2)

    return {
        "script_cost_krw": script_cost,
        "manim_cost_krw": manim_cost,
        "title_tag_cost_krw": title_cost,
        "image_cost_krw": image_cost,
        "total_krw": total,
    }


def aggregate_costs(cost_list: list[dict]) -> dict:
    """
    여러 파일럿 실행의 비용 dict 리스트를 받아 평균 비용 측정값 반환.
    반환값은 manim_pilot_report.json cost_measurement 필드에 삽입 가능한 형태.
    """
    if not cost_list:
        return {
            "avg_total_cost_per_video_krw": 0.0,
            "monthly_cost_48videos_estimate_krw": 0.0,
            "operating_cost_per_channel_monthly_krw": 0.0,
            "cost_source": "measured",
        }

    totals = [c.get("total_krw", 0.0) for c in cost_list]
    avg_cost = round(sum(totals) / len(totals), 2)
    monthly_48 = round(avg_cost * MONTHLY_TARGET_VIDEOS, 2)
    per_channel = round(monthly_48 / 5, 2)  # 5채널 분산

    return {
        "avg_total_cost_per_video_krw": avg_cost,
        "monthly_cost_48videos_estimate_krw": monthly_48,
        "operating_cost_per_channel_monthly_krw": per_channel,
        "cost_source": "measured",
    }


def build_cost_measurement(pilot_results: list[dict]) -> dict:
    """
    파일럿 결과 리스트에서 cost_measurement 블록 생성.
    pilot_results 각 항목은 calc_total_video_cost 반환값.
    """
    measured = aggregate_costs(pilot_results)
    logger.info(
        f"[COST] 평균 비용/편={measured['avg_total_cost_per_video_krw']}원 "
        f"| 월 48편={measured['monthly_cost_48videos_estimate_krw']}원"
    )
    return measured
