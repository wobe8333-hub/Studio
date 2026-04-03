"""STEP 10 — 썸네일 3종 생성."""
import base64
from pathlib import Path
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential
import google.generativeai as genai
from src.core.config import GEMINI_API_KEY, GEMINI_IMAGE_MODEL
from src.quota.gemini_quota import throttle_if_needed, record_request, record_image
from src.step08.image_generator import _generate_placeholder

genai.configure(api_key=GEMINI_API_KEY)
CHANNEL_THUMBNAIL_STYLE = {
    "CH1": "숫자/그래프 강조, 임팩트 텍스트, 다크 배경, 골드/레드 색상, 귀여운 경제 캐릭터",
    "CH2": "부동산 건물/지도 비주얼, 손실/이익 대비, 레드/그린 색상, 귀여운 부동산 캐릭터",
    "CH3": "사람 실루엣/표정, 질문형 텍스트, 퍼플/블루 색상, 귀여운 심리 캐릭터",
    "CH4": "미스터리/서스펜스 비주얼, 어두운 배경, 그림자 효과, 귀여운 탐정 캐릭터",
    "CH5": "전쟁/역사 비주얼, 강렬한 색상 대비, 드라마틱한 구도, 귀여운 군인 캐릭터",
    "CH6": "우주/과학 비주얼, 데이터 흐름, 사이버 블루/민트 색상, 귀여운 과학자 캐릭터",
    "CH7": "역사 유물/지도 비주얼, 세피아/골드 색상, 고전적 분위기, 귀여운 역사학자 캐릭터",
}
THUMBNAIL_MODES = {
    "01":"채널 스타일 강조 + 애니메이션 요소",
    "02":"숫자/데이터/결과 강조",
    "03":"강렬한 질문/텍스트 강조",
}

@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=30))
def generate_thumbnail(channel_id: str, title: str, mode: str, output_path: Path) -> bool:
    if not record_image(1): return _generate_placeholder(title, output_path)
    throttle_if_needed(); record_request()
    style = CHANNEL_THUMBNAIL_STYLE.get(channel_id,"")
    mode_desc = THUMBNAIL_MODES.get(mode,"")
    prompt = (f"YouTube thumbnail for Korean knowledge animation. "
              f"Title: {title}. Style: {style}. Mode: {mode_desc}. "
              f"1920x1080, bold Korean text, high contrast, NO faces.")
    try:
        model    = genai.GenerativeModel(GEMINI_IMAGE_MODEL)
        response = model.generate_content(
            prompt, generation_config=genai.GenerationConfig(response_mime_type="image/png"),
        )
        for part in response.parts:
            if hasattr(part,"inline_data") and part.inline_data:
                output_path.parent.mkdir(parents=True, exist_ok=True)
                output_path.write_bytes(base64.b64decode(part.inline_data.data))
                return True
    except Exception as e:
        logger.warning(f"[STEP10] 썸네일 실패 -> 플레이스홀더: {e}")
    return _generate_placeholder(title, output_path)
