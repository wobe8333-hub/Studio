"""
STEP 09 — AI BGM 자동 생성기.

Phase 7 추가:
  Suno AI API로 카테고리별 분위기 BGM 자동 생성.
  Suno API 없거나 실패 시 로컬 WAV 폴백.
"""

from pathlib import Path

from loguru import logger

from src.core.config import BGM_DIR

# 채널(카테고리)별 BGM 분위기 정의
CHANNEL_BGM_STYLE = {
    "CH1": {"mood": "calm professional", "genre": "cinematic", "tempo": "moderate", "description": "차분하고 신뢰감 있는 경제 뉴스 배경음"},
    "CH2": {"mood": "wonder futuristic", "genre": "electronic ambient", "tempo": "moderate", "description": "과학의 신비로움을 표현하는 배경음"},
    "CH3": {"mood": "trustworthy stable", "genre": "corporate", "tempo": "moderate", "description": "안정적인 부동산 정보 배경음"},
    "CH4": {"mood": "curious empathetic", "genre": "ambient", "tempo": "slow", "description": "심리 탐구의 따뜻하고 사색적인 배경음"},
    "CH5": {"mood": "mysterious suspense", "genre": "dark ambient", "tempo": "slow", "description": "미스터리 서스펜스 긴장감 있는 배경음"},
    "CH6": {"mood": "nostalgic storytelling", "genre": "cinematic folk", "tempo": "slow-moderate", "description": "역사의 이야기를 담은 배경음"},
    "CH7": {"mood": "dramatic epic", "genre": "orchestral", "tempo": "moderate-fast", "description": "웅장하고 역동적인 전쟁사 배경음"},
}


def generate_bgm(channel_id: str, duration_sec: int = 720) -> Path:
    """
    AI BGM 생성 (Suno AI → 로컬 WAV 폴백).

    Args:
        channel_id: CH1~CH7
        duration_sec: 영상 길이 (초)

    Returns:
        생성된 BGM 파일 경로 (없으면 None)
    """
    style = CHANNEL_BGM_STYLE.get(channel_id, CHANNEL_BGM_STYLE["CH1"])
    out_path = BGM_DIR / f"{channel_id}_bgm_ai.wav"
    BGM_DIR.mkdir(parents=True, exist_ok=True)

    # 1차: 기존 로컬 WAV 있으면 재사용
    existing = BGM_DIR / f"{channel_id}_bgm.wav"
    if existing.exists():
        logger.debug(f"[BGM] 로컬 WAV 재사용: {existing.name}")
        return existing

    # 2차: Suno AI API 시도
    suno_result = _try_suno_api(style, duration_sec, out_path)
    if suno_result:
        return out_path

    # 3차: 생성 불가 — None 반환 (bgm_overlay.py에서 처리)
    logger.warning(f"[BGM] {channel_id}: BGM 생성 불가 (Suno API 없음, 로컬 WAV 없음)")
    return None


def _try_suno_api(style: dict, duration_sec: int, out_path: Path) -> bool:
    """Suno AI API로 BGM 생성 시도."""
    try:
        import os

        import httpx

        suno_api_key = os.getenv("SUNO_API_KEY", "")
        if not suno_api_key:
            logger.debug("[BGM-Suno] API 키 없음 — 건너뜀")
            return False

        # Suno API 요청 (unofficial wrapper 형태)
        prompt = (
            f"{style['genre']} music, {style['mood']}, "
            f"{style['tempo']} tempo, instrumental only, no vocals, "
            f"background music for YouTube video, {duration_sec} seconds"
        )

        headers = {
            "Authorization": f"Bearer {suno_api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "prompt": prompt,
            "duration": min(duration_sec, 240),  # Suno 최대 240초
            "make_instrumental": True,
        }

        with httpx.Client(timeout=120) as client:
            resp = client.post(
                "https://api.suno.ai/v1/generate",
                headers=headers,
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()

        audio_url = data.get("audio_url", "")
        if not audio_url:
            return False

        # 오디오 다운로드
        with httpx.Client(timeout=60) as client:
            audio_resp = client.get(audio_url)
            audio_resp.raise_for_status()

        out_path.write_bytes(audio_resp.content)
        logger.info(f"[BGM-Suno] BGM 생성 완료: {out_path.name}")
        return True

    except Exception as e:
        logger.debug(f"[BGM-Suno] API 실패: {e}")
        return False
