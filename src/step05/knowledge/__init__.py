"""
Phase 4 — 3단계 지식 수집 파이프라인

Stage 1: AI 초벌 리서치 (Tavily + Perplexity + Gemini Deep Research)
Stage 2: 구조화 보강 (Wikipedia + Semantic Scholar + Naver)
Stage 3: 팩트체크 + 카테고리별 심화 보강
"""

from src.step05.knowledge.knowledge_package import KnowledgePackage, build_empty_package
from src.step05.knowledge.stage1_research import stage1_research
from src.step05.knowledge.stage2_enrich import stage2_enrich
from src.step05.knowledge.stage3_factcheck import stage3_factcheck

__all__ = [
    "KnowledgePackage",
    "build_empty_package",
    "stage1_research",
    "stage2_enrich",
    "stage3_factcheck",
]
