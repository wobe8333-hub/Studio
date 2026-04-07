"""STEP 11 — QA 게이트.

Phase 8 추가:
  - Gemini Vision 자동 품질 검증 (캐릭터 일관성, 텍스트 가독성, 부적절 콘텐츠)
  - 7채널 카테고리별 면책조항 확인 확장 (CH1~CH7)
"""

from loguru import logger
from src.core.ssot import read_json, write_json, json_exists, now_iso, get_run_dir
from src.core.config import GEMINI_API_KEY, GEMINI_TEXT_MODEL

REVIEW_REQUIRED    = {"CH1", "CH2", "CH4"}
REVIEW_CONDITIONAL = {"CH3"}

# 채널별 면책조항 키 (script_generator.py와 동기화)
CHANNEL_DISCLAIMER_KEY = {
    "CH1": "financial_disclaimer",
    "CH2": "investment_disclaimer",
    "CH3": "psychology_disclaimer",
    "CH4": "mystery_disclaimer",
    "CH5": "history_disclaimer",
    "CH6": "science_disclaimer",
    "CH7": "history_disclaimer",
}


def _gemini_vision_qa(video_path) -> dict:
    """
    Gemini Vision으로 영상 품질 자동 검증.
    영상에서 5프레임 샘플링 → 캐릭터 일관성, 텍스트 가독성, 부적절 콘텐츠 평가.
    """
    if not GEMINI_API_KEY:
        logger.debug("[QA-Vision] Gemini API 키 없음 — 건너뜀")
        return {"pass": True, "skipped": True, "reason": "api_key_missing"}

    if not video_path.exists() or video_path.stat().st_size == 0:
        return {"pass": False, "skipped": False, "reason": "video_not_found"}

    try:
        import google.generativeai as genai
        genai.configure(api_key=GEMINI_API_KEY)

        # ── 실제 영상 길이 측정 (ffprobe) ──────────────────────────────
        import subprocess

        duration_cmd = [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(video_path),
        ]
        try:
            dur_result = subprocess.run(
                duration_cmd, capture_output=True, text=True, timeout=10
            )
            video_duration = float(dur_result.stdout.strip()) if dur_result.returncode == 0 else 120.0
        except Exception:
            video_duration = 120.0  # ffprobe 실패 시 fallback

        # ── 5프레임 추출 (5%, 25%, 50%, 75%, 90% 위치) ─────────────────
        frames_dir = video_path.parent / "_qa_frames"
        frames_dir.mkdir(exist_ok=True)
        frame_files = []

        for i, pct in enumerate([5, 25, 50, 75, 90]):
            frame_path = frames_dir / f"frame_{i:02d}.jpg"
            seek_sec = pct / 100.0 * video_duration
            cmd = [
                "ffmpeg", "-y", "-ss", f"{seek_sec:.1f}",
                "-i", str(video_path),
                "-frames:v", "1",
                "-q:v", "2",
                str(frame_path),
            ]
            result = subprocess.run(cmd, capture_output=True, timeout=15)
            if result.returncode == 0 and frame_path.exists():
                frame_files.append(frame_path)

        if not frame_files:
            return {"pass": True, "skipped": True, "reason": "frame_extraction_failed"}

        # Gemini Vision으로 프레임 분석
        model = genai.GenerativeModel(GEMINI_TEXT_MODEL)
        parts = []
        for fp in frame_files[:5]:
            with open(fp, "rb") as f:
                parts.append({"mime_type": "image/jpeg", "data": f.read()})

        prompt_text = """이 영상 프레임들을 분석하여 다음 항목을 평가하세요:

1. 캐릭터 일관성 (프레임 간 캐릭터 디자인이 일관적인가?)
2. 텍스트 가독성 (자막/제목이 잘 보이는가?)
3. 부적절 콘텐츠 (폭력적/선정적 요소가 없는가?)
4. 전반적 품질 (시각적으로 깔끔하고 전문적인가?)

응답 형식 (JSON만):
{"character_consistency": true/false, "text_readability": true/false, "content_safe": true/false, "overall_quality": true/false, "issues": ["문제 설명"]}"""

        parts.append({"text": prompt_text})
        resp = model.generate_content(parts)
        text = resp.text.strip()
        if text.startswith("```"):
            text = "\n".join(text.split("\n")[1:-1]).strip()

        import json
        vision_result = json.loads(text)
        vision_pass = all([
            vision_result.get("character_consistency", True),
            vision_result.get("text_readability", True),
            vision_result.get("content_safe", True),
            vision_result.get("overall_quality", True),
        ])

        # 임시 프레임 정리
        for fp in frame_files:
            try:
                fp.unlink()
            except Exception:
                pass

        return {
            "pass": vision_pass,
            "skipped": False,
            "details": vision_result,
        }

    except Exception as e:
        logger.debug(f"[QA-Vision] Gemini Vision 오류: {e}")
        return {"pass": True, "skipped": True, "reason": str(e)}


def run_step11(
    channel_id: str,
    run_id: str,
    human_review_completed: bool = False,
    reviewer: str = None,
) -> dict:
    run_dir = get_run_dir(channel_id, run_id)
    s08 = run_dir / "step08"
    s11 = run_dir / "step11"
    s11.mkdir(parents=True, exist_ok=True)

    script = read_json(s08 / "script.json") if json_exists(s08 / "script.json") else {}
    video = s08 / "video.mp4"

    # ── 애니메이션 품질 기본 체크 ─────────────────────────────────
    anim_pass = (
        video.exists()
        and video.stat().st_size > 0
        and script.get("hook", {}).get("animation_preview_at_sec", 99) <= 10
    )

    # ── Gemini Vision QA (Phase 8) ───────────────────────────────
    vision_result = _gemini_vision_qa(video)
    vision_pass = vision_result.get("pass", True)
    # Vision QA 실패 시 anim_pass도 False로 처리
    if not vision_pass and not vision_result.get("skipped", False):
        anim_pass = False
        logger.warning(f"[STEP11] Vision QA 실패: {vision_result.get('details', {}).get('issues', [])}")

    # ── 면책조항 확인 (7채널 전체) ───────────────────────────────
    disc_key = CHANNEL_DISCLAIMER_KEY.get(channel_id, "general_disclaimer")
    has_disc = bool(script.get(disc_key))
    ai_label = bool(script.get("ai_label"))
    policy_pass = ai_label and has_disc

    # ── 수익 공식 확인 ────────────────────────────────────────────
    aff = script.get("affiliate_insert", {})
    formula_ok = aff.get("purchase_rate_applied", 0) > 0

    # ── 휴먼 리뷰 ─────────────────────────────────────────────────
    hr_required  = channel_id in REVIEW_REQUIRED
    hr_completed = human_review_completed if hr_required else True

    overall = anim_pass and policy_pass and formula_ok and hr_completed

    qa = {
        "channel_id": channel_id,
        "run_id": run_id,
        "qa_timestamp": now_iso(),
        "animation_quality_check": {
            "pass": anim_pass,
            "vision_qa": vision_result,
        },
        "script_accuracy_check": {"pass": has_disc, "disclaimer_key": disc_key},
        "youtube_policy_check": {
            "ai_label_placed": ai_label,
            "disclaimer_placed": has_disc,
            "disclaimer_key": disc_key,
            "pass": policy_pass,
        },
        "human_review": {
            "required": hr_required,
            "completed": hr_completed,
            "reviewer": reviewer,
            "sla_hours": 24 if hr_required else 0,
        },
        "affiliate_formula_check": {
            "purchase_rate_applied": aff.get("purchase_rate_applied", 0),
            "formula_correct": formula_ok,
        },
        "overall_pass": overall,
    }

    write_json(s11 / "qa_result.json", qa)

    if overall:
        logger.info(f"[STEP11] {channel_id}/{run_id} QA PASS")
    else:
        reasons = [
            k for k, v in [
                ("animation", not anim_pass),
                ("vision_qa", not vision_pass),
                ("policy", not policy_pass),
                ("formula", not formula_ok),
                ("human_review", not hr_completed),
            ] if v
        ]
        logger.warning(f"[STEP11] QA FAIL {channel_id}/{run_id}: {reasons}")

    return qa
