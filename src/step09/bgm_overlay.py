"""STEP 09 — BGM 오버레이."""
import os, shutil, logging
from src.core.ssot import read_json, write_json, json_exists, get_run_dir
from src.core.config import BGM_DIR
from src.step08.ffmpeg_composer import overlay_bgm

logger = logging.getLogger(__name__)
CHANNEL_BGM_TONE = {
    "CH1":"차분하고_진지한","CH2":"밝고_과학적",
    "CH3":"미스터리하고_사색적","CH4":"긴박하고_현실적","CH5":"미래적이고_역동적",
}

def run_step09(channel_id: str, run_id: str) -> bool:
    run_dir    = get_run_dir(channel_id, run_id)
    s08        = run_dir / "step08"
    video_path = s08 / "video.mp4"
    bgm_src    = BGM_DIR / f"{channel_id}_bgm.wav"
    bgm_dest   = s08 / "bgm.wav"
    if not video_path.exists():
        logger.error(f"[STEP09] video.mp4 없음: {channel_id}/{run_id}")
        return False
    if not bgm_src.exists():
        logger.warning(f"[STEP09] BGM 없음: {bgm_src}")
        rr = s08 / "render_report.json"
        if json_exists(rr):
            d = read_json(rr); d["bgm_used"]=False; d["bgm_category_tone"]="MISSING"
            write_json(rr, d)
        return False
    shutil.copy2(bgm_src, bgm_dest)
    bgm_out = s08 / "video_bgm.mp4"
    ok = overlay_bgm(video_path, bgm_dest, bgm_out)
    if ok and bgm_out.exists():
        os.replace(bgm_out, video_path)
        rr = s08 / "render_report.json"
        if json_exists(rr):
            d = read_json(rr)
            d["bgm_used"]=True; d["bgm_category_tone"]=CHANNEL_BGM_TONE.get(channel_id,"unknown")
            write_json(rr, d)
        logger.info(f"[STEP09] {channel_id}/{run_id} BGM 완료")
        return True
    return False
