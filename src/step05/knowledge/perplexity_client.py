"""
Perplexity API 클라이언트
AI 리서치 + 출처 추적 — 주제에 대한 심층 AI 요약 및 인용 출처 수집
"""

from typing import Dict, Any, List
from loguru import logger

from src.core.config import PERPLEXITY_API_KEY

PERPLEXITY_API_URL = "https://api.perplexity.ai/chat/completions"


def research_topic(topic: str, category: str) -> Dict[str, Any]:
    """
    Perplexity API로 주제 리서치

    Returns:
        {
            "summary": str,
            "citations": [str],  # 출처 URL 목록
            "ok": bool
        }
    """
    if not PERPLEXITY_API_KEY:
        logger.debug("[Perplexity] API 키 없음 — 건너뜀")
        return {"summary": "", "citations": [], "ok": False}

    try:
        import httpx

        # 카테고리별 질문 프레임 조정
        category_prompts = {
            "economy": f"{topic}의 경제적 원리, 최근 동향, 핵심 수치 데이터를 설명해주세요.",
            "realestate": f"{topic}이 부동산 시장에 미치는 영향과 최근 사례를 설명해주세요.",
            "psychology": f"{topic}의 심리학적 원리와 실생활 적용 방법을 설명해주세요.",
            "mystery": f"{topic}에 관한 알려진 사실과 미해결 의문점을 설명해주세요.",
            "war_history": f"{topic}의 역사적 전개 과정과 주요 사건들을 설명해주세요.",
            "science": f"{topic}의 과학적 원리와 최신 연구 동향을 설명해주세요.",
            "history": f"{topic}의 역사적 의미와 배경, 현대에 미치는 영향을 설명해주세요.",
        }
        prompt = category_prompts.get(category, f"{topic}에 대해 핵심 팩트 5가지를 설명해주세요.")

        headers = {
            "Authorization": f"Bearer {PERPLEXITY_API_KEY}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": "llama-3.1-sonar-large-128k-online",
            "messages": [
                {"role": "system", "content": "한국어로 정확한 정보를 제공하는 AI 리서처입니다. 출처를 명시하고 사실만 제공하세요."},
                {"role": "user", "content": prompt},
            ],
            "return_citations": True,
            "max_tokens": 1000,
        }

        with httpx.Client(timeout=30) as client:
            resp = client.post(PERPLEXITY_API_URL, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()

        summary = data["choices"][0]["message"]["content"]
        citations = data.get("citations", [])
        return {"summary": summary, "citations": citations, "ok": True}

    except Exception as e:
        logger.debug(f"[Perplexity] 리서치 실패: {e}")
        return {"summary": "", "citations": [], "ok": False}


def extract_key_sentences(summary: str, max_facts: int = 5) -> List[str]:
    """Perplexity 요약에서 핵심 문장 추출"""
    if not summary:
        return []
    sentences = [s.strip() for s in summary.split("\n") if len(s.strip()) > 20]
    clean = [s.lstrip("0123456789.-• ") for s in sentences]
    return [s for s in clean if s][:max_facts]
