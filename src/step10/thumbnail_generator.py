"""STEP 10 — 썸네일 3종 생성."""
import base64, logging
from pathlib import Path
from tenacity import retry, stop_after_attempt, wait_exponential
import google.generativeai as genai
from src.core.config import GEMINI_API_KEY, GEMINI_IMAGE_MODEL
from src.quota.gemini_quota import throttle_if_needed, record_request, record_image
from src.step08.image_generator import _generate_placeholder

genai.configure(api_key=GEMINI_API_KEY)
logger = logging.getLogger(__name__)

CHANNEL_THUMBNAIL_STYLE = {
    "CH1":"숫자/그래프 강조, 임팩트 텍스트, 다크 배경, 골드/레드 색상",
    "CH2":"신체 관련 비주얼, 경고/안심 색상 대비, 클린한 의료 스타일",
    "CH3":"사람 실루엣/표정, 질문형 텍스트, 퍼플/블루 색상",
    "CH4":"건물/부동산 비주얼, 손실/이익 대비, 레드/그린 색상",
    "CH5":"AI/테크 비주얼, 데이터 흐름, 사이버 블루/민트 색상",
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
