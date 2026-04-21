"""
Stage 3: 팩트체크 + 신뢰도 평가
Gemini로 Stage 1~2 팩트 교차 검증 → 수치/날짜/인물 정확도 확인
"""

from typing import List

from loguru import logger

from src.core.config import GEMINI_API_KEY, GEMINI_TEXT_MODEL
from src.step05.knowledge.knowledge_package import KnowledgePackage, SourceEntry


def _gemini_factcheck(facts: List[str], topic: str, category: str) -> dict:
    """Gemini로 팩트 교차 검증"""
    if not GEMINI_API_KEY or not facts:
        return {"verified_facts": facts, "flagged": [], "ok": False}

    try:
        from google import genai as _genai
        from google.genai import types as genai_types
        _client = _genai.Client(api_key=GEMINI_API_KEY)

        facts_text = "\n".join(f"{i+1}. {f}" for i, f in enumerate(facts))
        prompt = f"""주제: {topic} (카테고리: {category})

다음 팩트들을 검토하고 각 항목을 평가해주세요:

{facts_text}

응답 형식 (각 줄에 하나씩):
VERIFIED: [팩트 번호] [팩트 내용]  ← 정확한 팩트
MODIFIED: [팩트 번호] [수정된 내용]  ← 부정확하지만 수정 가능
FLAGGED: [팩트 번호] [이유]  ← 명백히 틀렸거나 검증 불가

규칙:
- 불확실하면 VERIFIED로 표시 (보수적으로 검증)
- 근거 없는 삭제 금지
- 한국어로 응답
"""
        resp = _client.models.generate_content(
            model=GEMINI_TEXT_MODEL,
            contents=prompt,
            config=genai_types.GenerateContentConfig(max_output_tokens=2000),
        )
        try:
            text = resp.text.strip()
        except (ValueError, AttributeError, TypeError):
            cparts = resp.candidates[0].content.parts if resp.candidates else []
            texts = [p.text for p in cparts if hasattr(p, "text") and p.text]
            text = texts[-1].strip() if texts else ""

        verified: List[str] = []
        flagged: List[str] = []

        for line in text.split("\n"):
            line = line.strip()
            if line.startswith("VERIFIED:"):
                content = line[len("VERIFIED:"):].strip()
                # "1 팩트내용" 형태에서 번호 제거
                cparts2 = content.split(" ", 1)
                fact = cparts2[1] if len(cparts2) > 1 and cparts2[0].isdigit() else content
                if fact:
                    verified.append(fact)
            elif line.startswith("MODIFIED:"):
                content = line[len("MODIFIED:"):].strip()
                cparts2 = content.split(" ", 1)
                fact = cparts2[1] if len(cparts2) > 1 and cparts2[0].isdigit() else content
                if fact:
                    verified.append(fact)
            elif line.startswith("FLAGGED:"):
                content = line[len("FLAGGED:"):].strip()
                flagged.append(content)

        # 검증된 팩트가 없으면 원본 반환 (보수적)
        if not verified:
            verified = facts

        return {"verified_facts": verified[:7], "flagged": flagged, "ok": True}

    except Exception as e:
        logger.debug(f"[Stage3-Gemini] 팩트체크 실패: {e}")
        return {"verified_facts": facts, "flagged": [], "ok": False}


def _rate_source_reliability(sources: List[SourceEntry]) -> List[SourceEntry]:
    """출처 신뢰도 재평가"""
    rated = []
    for s in sources:
        url = s.url.lower()
        if any(domain in url for domain in [
            "wikipedia.org", "naver.com", "gov.kr",
            "doi.org", "semanticscholar.org", "arxiv.org", "nasa.gov"
        ]):
            s.reliability = "HIGH"
        elif any(domain in url for domain in [
            "blog.", "cafe.", "dcinside", "reddit.com", "namu.wiki"
        ]):
            s.reliability = "LOW"
        else:
            s.reliability = "MED"
        rated.append(s)
    return rated


def stage3_factcheck(pkg: KnowledgePackage) -> KnowledgePackage:
    """
    Stage 3: Gemini 교차 검증 + 출처 신뢰도 평가
    - 팩트 검증 (VERIFIED/MODIFIED/FLAGGED)
    - 출처 신뢰도 재평가
    - 최종 confidence_score 확정
    """
    logger.info(f"[Stage3] '{pkg.topic}' 팩트체크 시작")

    # ── 1) 팩트 교차 검증 ──────────────────────────────────────────
    if pkg.core_facts:
        result = _gemini_factcheck(pkg.core_facts, pkg.topic, pkg.category)
        if result["ok"]:
            pkg.core_facts = result["verified_facts"]
            if result["flagged"]:
                logger.debug(f"[Stage3] 플래그 항목: {result['flagged']}")
            # 팩트 검증 성공 시 신뢰도 상향
            pkg.confidence_score = min(pkg.confidence_score + 0.15, 1.0)
            logger.debug(f"[Stage3] 검증 팩트={len(pkg.core_facts)}, 플래그={len(result['flagged'])}")
        else:
            logger.debug("[Stage3] Gemini 팩트체크 실패 — 원본 유지")
    else:
        logger.warning(f"[Stage3] '{pkg.topic}' 팩트 없음 — 검증 건너뜀")

    # ── 2) 출처 신뢰도 재평가 ─────────────────────────────────────
    pkg.sources = _rate_source_reliability(pkg.sources)
    high_count = sum(1 for s in pkg.sources if s.reliability == "HIGH")
    if high_count >= 2:
        pkg.confidence_score = min(pkg.confidence_score + 0.05, 1.0)

    # ── 3) 최소 팩트 보장 (Gemini 폴백) ──────────────────────────
    if len(pkg.core_facts) < 3:
        logger.warning(f"[Stage3] 팩트 부족 ({len(pkg.core_facts)}개) — Gemini 보충")
        try:
            from google import genai as _genai
            from google.genai import types as genai_types
            _client = _genai.Client(api_key=GEMINI_API_KEY)
            resp = _client.models.generate_content(
                model=GEMINI_TEXT_MODEL,
                contents=f"{pkg.topic}에 대한 핵심 사실 5가지를 한국어로 간결하게 나열해주세요.",
                config=genai_types.GenerateContentConfig(max_output_tokens=1000),
            )
            try:
                raw = resp.text.strip()
            except (ValueError, AttributeError, TypeError):
                cparts = resp.candidates[0].content.parts if resp.candidates else []
                texts = [p.text for p in cparts if hasattr(p, "text") and p.text]
                raw = texts[-1].strip() if texts else ""
            lines = [l.strip().lstrip("0123456789.-• ") for l in raw.split("\n")
                     if len(l.strip()) > 15]
            pkg.core_facts.extend([l for l in lines if l][:5])
        except Exception as e:
            logger.debug(f"[Stage3] Gemini 보충 실패: {e}")

    pkg.stage3_ok = True

    logger.info(
        f"[Stage3] 완료: 최종팩트={len(pkg.core_facts)}, "
        f"confidence={pkg.confidence_score:.2f}"
    )
    return pkg
