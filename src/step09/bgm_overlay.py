"""STEP 09 — BGM 오버레이.

Phase 7 개선:
  - 7채널 BGM 톤 갱신 (CH2 부동산, CH4 미스터리, CH5 전쟁사)
  - bgm_generator.py 연동 (Suno AI → 로컬 WAV 폴백)
"""

import os
import shutil
from loguru import logger

from src.core.ssot import read_json, write_json, json_exists, get_run_dir
from src.core.config import BGM_DIR
from src.step08.ffmpeg_composer import overlay_bgm

CHANNEL_BGM_TONE = {
    "CH1": "차분하고_진지한_경제",
    "CH2": "안정적이고_신뢰감있는_부동산",
    "CH3": "사색적이고_따뜻한_심리",
    "CH4": "미스터리하고_긴장감있는",
    "CH5": "웅장하고_역동적인_전쟁사",
    "CH6": "미래적이고_경이로운_과학",
    "CH7": "노스탤직하고_이야기같은_역사",
}


def run_step09(channel_id: str, run_id: str) -> bool:
    run_dir    = get_run_dir(channel_id, run_id)
    s08        = run_dir / "step08"
    video_path = s08 / "video.mp4"

    if not video_path.exists():
        logger.error(f"[STEP09] video.mp4 없음: {channel_id}/{run_id}")
        return False

    # BGM 소스 결정: bgm_generator → 로컬 WAV 순서
    from src.step09.bgm_generator import generate_bgm
    bgm_src = generate_bgm(channel_id, duration_sec=720)

    if bgm_src is None or not bgm_src.exists():
        logger.warning(f"[STEP09] {channel_id}: BGM 소스 없음 — 오버레이 건너뜀")
        rr = s08 / "render_report.json"
        if json_exists(rr):
            d = read_json(rr)
            d["bgm_used"] = False
            d["bgm_category_tone"] = "MISSING"
            write_json(rr, d)
        return False

    bgm_dest = s08 / "bgm.wav"
    shutil.copy2(bgm_src, bgm_dest)

    bgm_out = s08 / "video_bgm.mp4"
    ok = overlay_bgm(video_path, bgm_dest, bgm_out)

    if ok and bgm_out.exists():
        os.replace(bgm_out, video_path)
        rr = s08 / "render_report.json"
        if json_exists(rr):
            d = read_json(rr)
            d["bgm_used"] = True
            d["bgm_category_tone"] = CHANNEL_BGM_TONE.get(channel_id, "unknown")
            d["bgm_source"] = str(bgm_src.name)
            write_json(rr, d)
        logger.info(f"[STEP09] {channel_id}/{run_id} BGM 오버레이 완료")
        return True

    return False
