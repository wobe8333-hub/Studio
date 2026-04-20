"""LLM 이중화 클라이언트 테스트 (Plan C-1 T8).

Gemini 우선 → 실패 시 Claude fallback → 둘 다 실패 시 RuntimeError.
"""
import pytest
from unittest.mock import patch


def test_generate_text_uses_gemini_first():
    """generate_text는 Gemini를 우선 호출해야 한다."""
    from src.core.llm_client import generate_text

    with patch("src.core.llm_client._call_gemini", return_value="Gemini 응답") as mock_g, \
         patch("src.core.llm_client._call_claude") as mock_c:
        result = generate_text("테스트 프롬프트")

    mock_g.assert_called_once()
    mock_c.assert_not_called()
    assert result == "Gemini 응답"


def test_generate_text_falls_back_to_claude_on_gemini_failure():
    """Gemini 실패 시 Claude로 자동 전환되어야 한다."""
    from src.core.llm_client import generate_text

    with patch("src.core.llm_client._call_gemini", side_effect=Exception("Gemini API 오류")), \
         patch("src.core.llm_client._call_claude", return_value="Claude 응답") as mock_c:
        result = generate_text("테스트 프롬프트")

    mock_c.assert_called_once()
    assert result == "Claude 응답"


def test_generate_text_raises_when_both_fail():
    """Gemini와 Claude 모두 실패하면 RuntimeError를 발생시켜야 한다."""
    from src.core.llm_client import generate_text

    with patch("src.core.llm_client._call_gemini", side_effect=Exception("Gemini 실패")), \
         patch("src.core.llm_client._call_claude", side_effect=Exception("Claude 실패")):
        with pytest.raises(RuntimeError, match="LLM_ALL_PROVIDERS_FAILED"):
            generate_text("테스트 프롬프트")
