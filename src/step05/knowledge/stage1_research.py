"""
Stage 1: AI 초벌 리서치
Tavily AI Search + Perplexity API + Gemini Deep Research
→ 핵심 팩트 5~7개 + 출처 URL 통합
"""

from typing import Any, Dict, List

from loguru import logger

from src.core.config import GEMINI_API_KEY, GEMINI_TEXT_MODEL
from src.step05.knowledge.knowledge_package import (
    KnowledgePackage,
    SourceEntry,
)
from src.step05.knowledge.perplexity_client import extract_key_sentences, research_topic
from src.step05.knowledge.tavily_client import extract_facts_from_results, search_topic


def _gemini_deep_research(topic: str, category: str) -> Dict[str, Any]:
    """Gemini로 주제 심층 분석 (Deep Research 프롬프트)"""
    if not GEMINI_API_KEY:
        logger.debug("[Stage1-Gemini] API 키 없음")
        return {"facts": [], "ok": False}

    try:
        from google import genai as _genai
        from google.genai import types as genai_types
        _client = _genai.Client(api_key=GEMINI_API_KEY)

        prompt = f"""주제: {topic} (카테고리: {category})

다음 형식으로 핵심 정보를 제공해주세요:

1. 핵심 팩트 1
2. 핵심 팩트 2
3. 핵심 팩트 3
4. 핵심 팩트 4
5. 핵심 팩트 5

규칙:
- 각 팩트는 구체적 수치나 사례를 포함
- 검증 가능한 사실만 포함
- 한국어로 작성
- 각 팩트는 1~2문장
"""
        resp = _client.models.generate_content(
            model=GEMINI_TEXT_MODEL,
            contents=prompt,
            config=genai_types.GenerateContentConfig(max_output_tokens=2000),
        )
        try:
            text = resp.text.strip()
        except (ValueError, AttributeError, TypeError):
            parts = resp.candidates[0].content.parts if resp.candidates else []
            texts = [p.text for p in parts if hasattr(p, "text") and p.text]
            text = texts[-1].strip() if texts else ""
        lines = [l.strip().lstrip("0123456789.-• ") for l in text.split("\n") if len(l.strip()) > 15]
        facts = [l for l in lines if l][:7]
        return {"facts": facts, "ok": True}

    except Exception as e:
        logger.debug(f"[Stage1-Gemini] 분석 실패: {e}")
        return {"facts": [], "ok": False}


def stage1_research(pkg: KnowledgePackage) -> KnowledgePackage:
    """
    Stage 1: 3개 소스에서 AI 초벌 리서치 수행
    결과를 pkg에 직접 기록 후 반환
    """
    logger.info(f"[Stage1] '{pkg.topic}' ({pkg.category}) 리서치 시작")

    all_facts: List[str] = []
    sources: List[SourceEntry] = []
    ok_count = 0

    # ── 1) Tavily AI Search ──────────────────────────────────────
    try:
        query = f"{pkg.topic} {pkg.category} 핵심 정보"
        tavily_result = search_topic(query, max_results=5)
        if tavily_result["ok"]:
            tavily_facts = extract_facts_from_results(tavily_result["results"])
            all_facts.extend(tavily_facts)
            for r in tavily_result["results"][:3]:
                sources.append(SourceEntry(
                    url=r.get("url", ""),
                    title=r.get("title", ""),
                    source_type="web",
                    reliability="MED",
                ))
            # AI 요약 답변도 팩트로 추가
            if tavily_result.get("answer"):
                all_facts.insert(0, tavily_result["answer"][:200])
            ok_count += 1
            logger.debug(f"[Stage1] Tavily: {len(tavily_facts)}개 팩트 수집")
    except Exception as e:
        logger.debug(f"[Stage1] Tavily 오류: {e}")

    # ── 2) Perplexity API ────────────────────────────────────────
    try:
        perp_result = research_topic(pkg.topic, pkg.category)
        if perp_result["ok"]:
            perp_facts = extract_key_sentences(perp_result["summary"], max_facts=5)
            all_facts.extend(perp_facts)
            for url in perp_result["citations"][:3]:
                sources.append(SourceEntry(
                    url=url,
                    title="",
                    source_type="web",
                    reliability="HIGH",
                ))
            ok_count += 1
            logger.debug(f"[Stage1] Perplexity: {len(perp_facts)}개 팩트 수집")
    except Exception as e:
        logger.debug(f"[Stage1] Perplexity 오류: {e}")

    # ── 3) Gemini Deep Research ──────────────────────────────────
    try:
        gemini_result = _gemini_deep_research(pkg.topic, pkg.category)
        if gemini_result["ok"]:
            all_facts.extend(gemini_result["facts"])
            ok_count += 1
            logger.debug(f"[Stage1] Gemini: {len(gemini_result['facts'])}개 팩트 수집")
    except Exception as e:
        logger.debug(f"[Stage1] Gemini 오류: {e}")

    # ── 결과 통합 (중복 제거, 상위 7개) ──────────────────────────
    seen: set = set()
    unique_facts: List[str] = []
    for fact in all_facts:
        key = fact[:40]
        if key not in seen and len(fact) > 10:
            seen.add(key)
            unique_facts.append(fact)

    pkg.core_facts = unique_facts[:7]
    pkg.sources.extend(sources)
    pkg.stage1_ok = len(pkg.core_facts) > 0

    # 신뢰도 초기값 (소스 수에 비례)
    pkg.confidence_score = min(0.3 * ok_count, 0.6)

    logger.info(
        f"[Stage1] 완료: 팩트={len(pkg.core_facts)}, "
        f"출처={len(sources)}, 성공소스={ok_count}/3"
    )
    return pkg
