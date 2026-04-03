"""STEP 08 — 나레이션 생성기.

Phase 6 전환:
  1차 시도: ElevenLabs Multilingual v2 (채널별 고유 보이스)
  폴백: gTTS (ElevenLabs 키 없거나 실패 시)
"""

from pathlib import Path
from loguru import logger

from src.core.config import GEMINI_API_KEY, GTTS_LANG, ELEVENLABS_API_KEY, CHANNEL_VOICE_IDS


def _build_narration_text(script: dict) -> str:
    """스크립트 dict에서 전체 나레이션 텍스트 조합"""
    parts = [
        script.get("hook", {}).get("text", ""),
        script.get("promise", ""),
    ]
    for s in script.get("sections", []):
        parts.append(s.get("narration_text", ""))
    cta = script.get("cta", {}).get("text", "")
    if cta:
        parts.append(cta)
    return "\n\n".join(p for p in parts if p)


def _generate_elevenlabs(text: str, channel_id: str, output_path: Path) -> bool:
    """ElevenLabs Multilingual v2로 TTS 생성"""
    if not ELEVENLABS_API_KEY:
        logger.debug("[Narration] ElevenLabs API 키 없음 — gTTS 폴백")
        return False

    voice_id = CHANNEL_VOICE_IDS.get(channel_id, "")
    if not voice_id:
        logger.debug(f"[Narration] {channel_id} 보이스 ID 미등록 — gTTS 폴백")
        return False

    try:
        from elevenlabs.client import ElevenLabs
        from elevenlabs import VoiceSettings

        client = ElevenLabs(api_key=ELEVENLABS_API_KEY)
        audio_gen = client.text_to_speech.convert(
            voice_id=voice_id,
            text=text,
            model_id="eleven_multilingual_v2",
            voice_settings=VoiceSettings(
                stability=0.5,
                similarity_boost=0.75,
                style=0.4,
                use_speaker_boost=True,
            ),
        )
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "wb") as f:
            for chunk in audio_gen:
                f.write(chunk)

        logger.info(f"[Narration] ElevenLabs TTS 완료: {output_path.name} (채널={channel_id})")
        return True

    except Exception as e:
        logger.warning(f"[Narration] ElevenLabs 실패: {e} — gTTS 폴백")
        return False


def _generate_gtts(text: str, output_path: Path) -> bool:
    """gTTS 폴백"""
    try:
        from gtts import gTTS
        tts = gTTS(text=text, lang=GTTS_LANG, slow=False)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        tts.save(str(output_path))
        logger.info(f"[Narration] gTTS 완료: {output_path.name}")
        return True
    except Exception as e:
        logger.error(f"[Narration] gTTS 실패: {e}")
        return False


def generate_narration(script: dict, output_path: Path, channel_id: str = "") -> bool:
    """
    나레이션 생성.

    ElevenLabs(채널별 보이스) → gTTS 폴백 순서로 시도.

    Args:
        script: step08 스크립트 dict
        output_path: 출력 오디오 경로 (.mp3)
        channel_id: CH1~CH7 (ElevenLabs 보이스 매핑용)

    Returns:
        True: 성공, False: 실패
    """
    text = _build_narration_text(script)
    if not text:
        logger.error("[Narration] 나레이션 텍스트 없음")
        return False

    # ElevenLabs 우선 시도
    if channel_id and _generate_elevenlabs(text, channel_id, output_path):
        return True

    # gTTS 폴백
    return _generate_gtts(text, output_path)
