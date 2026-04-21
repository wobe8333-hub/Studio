"""
KnowledgePackage — 지식 수집 결과 스키마 및 CRUD
Stage 1~3 결과를 통합하여 Step08 스크립트 생성에 제공
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

from src.core.config import KNOWLEDGE_DIR
from src.core.ssot import now_iso, write_json


@dataclass
class SourceEntry:
    """출처 항목"""
    url: str = ""
    title: str = ""
    source_type: str = ""     # "web", "wiki", "scholar", "news", "api"
    reliability: str = "MED"  # HIGH / MED / LOW
    retrieved_at: str = ""


@dataclass
class KnowledgePackage:
    """지식 패키지 — Stage 1~3 통합 결과물"""
    topic: str = ""
    category: str = ""
    channel_id: str = ""

    # 핵심 팩트 (5~7개)
    core_facts: List[str] = field(default_factory=list)

    # 연대표 항목 (선택)
    timeline: List[Dict[str, str]] = field(default_factory=list)

    # 수치/통계 (선택)
    statistics: List[Dict[str, str]] = field(default_factory=list)

    # 전문가 인용구 (선택)
    expert_quotes: List[str] = field(default_factory=list)

    # 반론/다른 시각 (선택)
    counterpoints: List[str] = field(default_factory=list)

    # 출처 목록
    sources: List[SourceEntry] = field(default_factory=list)

    # 신뢰도 점수 (0.0~1.0)
    confidence_score: float = 0.0

    # 메타 정보
    created_at: str = field(default_factory=now_iso)
    stage1_ok: bool = False
    stage2_ok: bool = False
    stage3_ok: bool = False


def build_empty_package(topic: str, category: str, channel_id: str) -> KnowledgePackage:
    """빈 패키지 생성"""
    return KnowledgePackage(
        topic=topic,
        category=category,
        channel_id=channel_id,
        created_at=now_iso(),
    )


def package_to_dict(pkg: KnowledgePackage) -> dict:
    """dataclass → JSON 직렬화 가능 dict 변환"""
    d = asdict(pkg)
    return d


def save_package(pkg: KnowledgePackage) -> Path:
    """
    knowledge_store/{channel_id}/packages/{topic_slug}.json 에 저장
    Returns: 저장된 파일 경로
    """
    slug = pkg.topic.replace(" ", "_").replace("/", "-")[:60]
    pkg_dir = KNOWLEDGE_DIR / pkg.channel_id / "packages"
    pkg_dir.mkdir(parents=True, exist_ok=True)
    out_path = pkg_dir / f"{slug}.json"
    write_json(out_path, package_to_dict(pkg))
    return out_path


def load_package(channel_id: str, topic: str) -> Optional[KnowledgePackage]:
    """저장된 패키지 불러오기 (없으면 None)"""
    slug = topic.replace(" ", "_").replace("/", "-")[:60]
    path = KNOWLEDGE_DIR / channel_id / "packages" / f"{slug}.json"
    if not path.exists():
        return None
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    sources = [SourceEntry(**s) for s in data.get("sources", [])]
    data["sources"] = sources
    return KnowledgePackage(**data)
