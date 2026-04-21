"""LLM 텍스트 생성 단일 진입점.

Gemini를 우선 사용하고, 실패 시 Claude(Anthropic)로 자동 전환한다.
호출자는 어떤 LLM이 응답했는지 알 필요 없다.

사용법:
    from src.core.llm_client import generate_text

    text = generate_text("프롬프트 텍스트")
    text = generate_text("프롬프트", model="gemini-2.5-flash")  # Gemini 모델 지정
"""
import os

from loguru import logger


def _call_gemini(prompt: str, model: str | None = None) -> str:
    """Gemini 텍스트 생성 호출."""
    import google.generativeai as genai
    _model = model or os.getenv("GEMINI_TEXT_MODEL", "gemini-2.5-flash")
    genai.configure(api_key=os.getenv("GEMINI_API_KEY", ""))
    response = genai.GenerativeModel(_model).generate_content(prompt)
    return response.text


def _call_claude(prompt: str) -> str:
    """Claude 텍스트 생성 호출 (Gemini fallback).

    비용 효율적인 claude-haiku-4-5 모델을 사용한다.
    """
    import anthropic
    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY", ""))
    message = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}],
    )
    return message.content[0].text


def generate_text(prompt: str, model: str | None = None) -> str:
    """텍스트 생성. Gemini 실패 시 Claude로 자동 전환.

    Args:
        prompt: 생성 프롬프트
        model: Gemini 모델명 (None이면 GEMINI_TEXT_MODEL 환경변수 사용)

    Returns:
        생성된 텍스트

    Raises:
        RuntimeError: Gemini와 Claude 모두 실패한 경우
    """
    try:
        result = _call_gemini(prompt, model)
        logger.debug("[LLM] Gemini 응답 성공")
        return result
    except Exception as e_gemini:
        logger.warning(f"[LLM] Gemini 실패 → Claude fallback: {e_gemini}")
        try:
            result = _call_claude(prompt)
            logger.info("[LLM] Claude fallback 응답 성공")
            return result
        except Exception as e_claude:
            logger.error(f"[LLM] Claude도 실패: {e_claude}")
            raise RuntimeError(
                f"LLM_ALL_PROVIDERS_FAILED gemini={e_gemini} claude={e_claude}"
            )
