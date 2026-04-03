"""
speed_measure.py
STEP 00-P 파일럿 생산 속도 측정 모듈.
각 파이프라인 단계별 소요 시간을 측정하고,
월 48편 생산 가능 여부를 산출한다.
"""

from loguru import logger
import time
from typing import Callable, Any

# 월 기준 (일 22일 × 스케줄러 1대 기준)
WORKING_DAYS_PER_MONTH = 22
SCHEDULER_HOURS_PER_DAY = 20  # 1일 20시간 가동 기준 (유지보수 4시간 제외)
MONTHLY_TARGET_VIDEOS = 48


def measure_step(step_name: str, func: Callable, *args, **kwargs) -> tuple[Any, float]:
    """
    단일 파이프라인 단계 실행 시간 측정.
    반환값: (결과값, 소요시간_초)
    """
    start = time.time()
    try:
        result = func(*args, **kwargs)
    except Exception as e:
        elapsed = time.time() - start
        logger.error(f"SPEED_MEASURE_FAIL [{step_name}]: {e}")
        return None, elapsed
    elapsed = time.time() - start
    logger.debug(f"[SPEED] {step_name}: {elapsed:.2f}초")
    return result, elapsed


def calc_production_speed(timings: dict) -> dict:
    """
    단계별 소요시간(초) 딕셔너리를 받아 생산 속도 지표 산출.

    timings 예시:
    {
        "script_gen_sec": 12.3,
        "image_gen_sec": 45.1,
        "manim_code_gen_sec": 8.2,
        "manim_render_sec": 90.0,
        "ffmpeg_merge_sec": 15.5,
    }
    """
    script_gen   = timings.get("script_gen_sec", 0.0)
    image_gen    = timings.get("image_gen_sec", 0.0)
    manim_code   = timings.get("manim_code_gen_sec", 0.0)
    manim_render = timings.get("manim_render_sec", 0.0)
    ffmpeg_merge = timings.get("ffmpeg_merge_sec", 0.0)

    avg_total_sec = script_gen + image_gen + manim_code + manim_render + ffmpeg_merge

    if avg_total_sec <= 0:
        return {
            "avg_total_sec": 0.0,
            "avg_script_gen_sec": script_gen,
            "avg_image_gen_sec": image_gen,
            "avg_manim_code_gen_sec": manim_code,
            "avg_manim_render_sec": manim_render,
            "avg_ffmpeg_merge_sec": ffmpeg_merge,
            "videos_per_day_per_scheduler": 0.0,
            "monthly_feasible_per_scheduler": 0.0,
            "required_schedulers_for_48": 999,
            "monthly_target_48_feasible": False,
            "bottleneck_step": "UNKNOWN",
        }

    available_sec_per_day = SCHEDULER_HOURS_PER_DAY * 3600
    videos_per_day = available_sec_per_day / avg_total_sec
    monthly_feasible = videos_per_day * WORKING_DAYS_PER_MONTH

    required_schedulers = 1
    while (monthly_feasible * required_schedulers) < MONTHLY_TARGET_VIDEOS:
        required_schedulers += 1
        if required_schedulers > 10:
            break

    feasible = required_schedulers <= 5

    # 병목 단계 판별
    step_times = {
        "script_gen": script_gen,
        "image_gen": image_gen,
        "manim_code_gen": manim_code,
        "manim_render": manim_render,
        "ffmpeg_merge": ffmpeg_merge,
    }
    bottleneck = max(step_times, key=step_times.get)

    return {
        "avg_total_sec": round(avg_total_sec, 2),
        "avg_script_gen_sec": round(script_gen, 2),
        "avg_image_gen_sec": round(image_gen, 2),
        "avg_manim_code_gen_sec": round(manim_code, 2),
        "avg_manim_render_sec": round(manim_render, 2),
        "avg_ffmpeg_merge_sec": round(ffmpeg_merge, 2),
        "videos_per_day_per_scheduler": round(videos_per_day, 2),
        "monthly_feasible_per_scheduler": round(monthly_feasible, 1),
        "required_schedulers_for_48": required_schedulers,
        "monthly_target_48_feasible": feasible,
        "bottleneck_step": bottleneck,
    }


def aggregate_timings(timing_list: list[dict]) -> dict:
    """
    여러 파일럿 실행의 timing 딕셔너리 리스트를 받아
    각 단계별 평균값 dict 반환.
    """
    if not timing_list:
        return {}
    keys = timing_list[0].keys()
    averaged = {}
    for k in keys:
        values = [t[k] for t in timing_list if k in t and isinstance(t[k], (int, float))]
        averaged[k] = round(sum(values) / len(values), 2) if values else 0.0
    return averaged
