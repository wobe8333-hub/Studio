"""
Keyword Approval Gate - STEP4 키워드 승인 게이트
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional

from backend.knowledge_v1.paths import get_root, get_keywords_dir
from backend.knowledge_v1.schema import AuditEvent
from backend.knowledge_v1.store import append_jsonl


# 승인 게이트 상수
APPROVAL_SCORE_THRESHOLD = 3.0
MIN_SOURCE_COUNT = 2
BLACKLIST = ["scam", "fake", "clickbait"]

# 기본 카테고리 리스트
DEFAULT_CATEGORIES = ["science", "history", "common_sense", "economy", "geography", "papers"]

# 카테고리별 seed 키워드
CATEGORY_SEEDS = {
    "science": ["gravity", "quantum physics", "evolution", "climate change", "black hole", "atom", "molecule", "energy", "light", "wave"],
    "history": ["world war", "ancient rome", "renaissance", "cold war", "industrial revolution", "empire", "civilization", "medieval", "revolution", "dynasty"],
    "common_sense": ["electricity", "water cycle", "photosynthesis", "gravity", "magnetism", "light", "sound", "temperature", "pressure", "force"],
    "economy": ["inflation", "gdp", "stock market", "cryptocurrency", "trade", "currency", "bank", "finance", "economic", "market"],
    "geography": ["latitude", "longitude", "tectonic plates", "ocean currents", "climate zones", "mountain", "river", "continent", "country", "map"],
    "papers": ["transformer", "attention mechanism", "neural network", "deep learning", "llm", "ai", "machine learning", "algorithm", "nlp", "computer vision"]
}


def _is_blacklisted(keyword: str) -> bool:
    """블랙리스트 확인"""
    kw_lower = keyword.lower()
    return any(bl in kw_lower for bl in BLACKLIST)


def approve_keywords(cycle_id: str, categories: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    키워드 승인 게이트 실행
    
    Args:
        cycle_id: discovery cycle ID (또는 "latest")
        categories: 처리할 카테고리 리스트 (None이면 모든 카테고리)
    
    Returns:
        {
            "cycle_id": str,
            "started_at": str,
            "ended_at": str,
            "categories": Dict[str, Dict],
            "summary": Dict
        }
    """
    started_at = datetime.utcnow()
    
    # cycle_id가 "latest"면 가장 최신 discovery cycle 찾기
    if cycle_id == "latest":
        discovery_root = get_root() / "keyword_discovery" / "reports"
        if discovery_root.exists():
            reports = list(discovery_root.glob("keyword_discovery_*.json"))
            if reports:
                latest = max(reports, key=lambda p: p.stat().st_mtime)
                cycle_id = latest.stem.replace("keyword_discovery_", "")
            else:
                cycle_id = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        else:
            cycle_id = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    
    # 디렉토리 생성
    approval_root = get_root() / "keyword_approval"
    (approval_root / "approved").mkdir(parents=True, exist_ok=True)
    (approval_root / "rejected").mkdir(parents=True, exist_ok=True)
    (approval_root / "reports").mkdir(parents=True, exist_ok=True)
    
    # Audit: START
    audit_path = get_root() / "audit" / "audit.jsonl"
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    append_jsonl(audit_path, AuditEvent.create("KEYWORD_APPROVAL_START", {
        "cycle_id": cycle_id
    }).to_dict())
    
    # 스코어된 키워드 로드
    discovery_root = get_root() / "keyword_discovery" / "scored"
    if not discovery_root.exists():
        return {
            "cycle_id": cycle_id,
            "started_at": started_at.isoformat() + "Z",
            "ended_at": datetime.utcnow().isoformat() + "Z",
            "categories": {},
            "summary": {"total_approved": 0, "total_rejected": 0},
            "error": "scored_keywords_not_found"
        }
    
    # 카테고리별 파일 찾기
    scored_files = list(discovery_root.glob(f"*_{cycle_id}.json"))
    if not scored_files:
        # cycle_id가 정확하지 않으면 모든 파일에서 최신 찾기
        scored_files = list(discovery_root.glob("*.json"))
        if scored_files:
            latest = max(scored_files, key=lambda p: p.stat().st_mtime)
            scored_files = [latest]
    
    report = {
        "cycle_id": cycle_id,
        "started_at": started_at.isoformat() + "Z",
        "mode": "approval",
        "categories": {},
        "summary": {
            "total_approved": 0,
            "total_rejected": 0
        }
    }
    
    # 처리할 카테고리 리스트 결정
    if categories is None:
        target_categories = DEFAULT_CATEGORIES
    else:
        target_categories = categories
    
    # 카테고리별 scored 데이터 로드
    category_scored_data = {}
    for scored_file in scored_files:
        try:
            with open(scored_file, "r", encoding="utf-8") as f:
                scored = json.load(f)
            
            # 카테고리 추출 (파일명에서) - stem에서 f"_{cycle_id}"를 제거한 전체 문자열을 category로 사용
            category = scored_file.stem.replace(f"_{cycle_id}", "")
            if category in target_categories:
                category_scored_data[category] = scored
        except Exception:
            pass
    
    # 카테고리별 처리 (6개 카테고리 모두 처리 보장)
    processed_categories = set()
    
    for category in target_categories:
        scored = category_scored_data.get(category, [])
        
        try:
            
            approved_keywords = []
            rejected_keywords = []
            
            # AUTO_MINIMUM 모드 확인
            auto_approve_mode = os.getenv("KNOWLEDGE_AUTO_APPROVE_MODE", "AUTO_MINIMUM")
            auto_approve_min = int(os.getenv("KNOWLEDGE_AUTO_APPROVE_MIN", "20"))
            
            if scored:
                # scored 후보가 있으면 처리
                for item in scored:
                    keyword = item.get("keyword", "")
                    final_score = item.get("final_score", 0.0)
                    sources_count = item.get("sources_count", 0)
                    
                    # 블랙리스트 확인
                    if _is_blacklisted(keyword):
                        rejected_keywords.append({
                            "keyword": keyword,
                            "reason": "blacklisted",
                            "final_score": final_score,
                            "sources_count": sources_count
                        })
                        append_jsonl(audit_path, AuditEvent.create("KEYWORD_APPROVAL_REJECTED", {
                            "cycle_id": cycle_id,
                            "category": category,
                            "keyword": keyword,
                            "reason": "blacklisted"
                        }).to_dict())
                        continue
                    
                    # AUTO_MINIMUM 모드: 상위 N개 자동 승인
                    if auto_approve_mode == "AUTO_MINIMUM":
                        # scored를 final_score 내림차순으로 정렬
                        sorted_scored = sorted(scored, key=lambda x: x.get("final_score", 0.0), reverse=True)
                        top_n_keywords = [item.get("keyword", "") for item in sorted_scored[:auto_approve_min] if item.get("keyword", "")]
                        
                        if keyword in top_n_keywords:
                            approved_keywords.append(keyword)
                            append_jsonl(audit_path, AuditEvent.create("KEYWORD_APPROVAL_APPROVED", {
                                "cycle_id": cycle_id,
                                "category": category,
                                "keyword": keyword,
                                "final_score": final_score,
                                "sources_count": sources_count,
                                "mode": "AUTO_MINIMUM"
                            }).to_dict())
                        else:
                            rejected_keywords.append({
                                "keyword": keyword,
                                "reason": f"not_in_top_{auto_approve_min}",
                                "final_score": final_score,
                                "sources_count": sources_count
                            })
                    else:
                        # 기존 로직: 승인 조건 확인
                        if final_score >= APPROVAL_SCORE_THRESHOLD and sources_count >= MIN_SOURCE_COUNT:
                            approved_keywords.append(keyword)
                            append_jsonl(audit_path, AuditEvent.create("KEYWORD_APPROVAL_APPROVED", {
                                "cycle_id": cycle_id,
                                "category": category,
                                "keyword": keyword,
                                "final_score": final_score,
                                "sources_count": sources_count
                            }).to_dict())
                        else:
                            rejected_keywords.append({
                                "keyword": keyword,
                                "reason": f"score_too_low_or_insufficient_sources (score={final_score:.2f}, sources={sources_count})",
                                "final_score": final_score,
                                "sources_count": sources_count
                            })
                            append_jsonl(audit_path, AuditEvent.create("KEYWORD_APPROVAL_REJECTED", {
                                "cycle_id": cycle_id,
                                "category": category,
                                "keyword": keyword,
                                "reason": "score_too_low_or_insufficient_sources",
                                "final_score": final_score,
                                "sources_count": sources_count
                            }).to_dict())
            
            # 승인된 키워드 저장 (승인 0개여도 파일 생성 보장)
            approved_path = approval_root / "approved" / f"{category}.txt"
            fallback_keywords = []
            
            if approved_keywords:
                # 승인된 키워드가 있으면 사용
                final_keywords = approved_keywords
            else:
                # 승인 0개면 롤백 또는 seed 사용
                # 1) 기존 inputs/keywords 파일에서 읽기
                existing_path = get_keywords_dir() / f"{category}.txt"
                if existing_path.exists():
                    try:
                        with open(existing_path, "r", encoding="utf-8") as f:
                            existing_lines = [l.strip() for l in f if l.strip()]
                            if existing_lines:
                                fallback_keywords = existing_lines
                    except Exception:
                        pass
                
                # 2) 기존 파일이 없으면 scored 상위 1개 사용
                if not fallback_keywords and scored:
                    sorted_scored = sorted(scored, key=lambda x: x.get("final_score", 0.0), reverse=True)
                    if sorted_scored:
                        top_item = sorted_scored[0]
                        top_keyword = top_item.get("keyword", "")
                        if top_keyword:
                            fallback_keywords = [top_keyword]
                
                # 3) 그것도 없으면 seed 최소 10개로 생성
                if not fallback_keywords:
                    seeds = CATEGORY_SEEDS.get(category, [f"{category} topic"])
                    fallback_keywords = seeds[:10]
                
                final_keywords = fallback_keywords
            
            # 파일 생성 (항상 생성 보장)
            with open(approved_path, "w", encoding="utf-8") as f:
                for kw in final_keywords:
                    f.write(f"{kw}\n")
            
            # 거부된 키워드 저장
            rejected_path = approval_root / "rejected" / f"{category}.json"
            with open(rejected_path, "w", encoding="utf-8") as f:
                json.dump(rejected_keywords, f, ensure_ascii=False, indent=2)
            
            # STEP1 입력으로 연결 (approved -> inputs/keywords) - 항상 동기화 (승인 0개여도 파일 생성 보장)
            inputs_path = get_keywords_dir() / f"{category}.txt"
            inputs_path.parent.mkdir(parents=True, exist_ok=True)
            
            # approved 파일 내용을 그대로 복사 (UTF-8 overwrite)
            with open(inputs_path, "w", encoding="utf-8") as f:
                for kw in final_keywords:
                    f.write(f"{kw}\n")
            
            processed_categories.add(category)
            
            # 리포트
            report["categories"][category] = {
                "approved_count": len(approved_keywords),
                "final_keywords_count": len(final_keywords),
                "rejected_count": len(rejected_keywords),
                "rollback_maintained": len(approved_keywords) == 0,
                "auto_approve_mode": auto_approve_mode
            }
            
            report["summary"]["total_approved"] += len(approved_keywords)
            report["summary"]["total_rejected"] += len(rejected_keywords)
            
        except Exception as e:
            # 에러가 발생해도 파일은 생성 (seed 사용)
            try:
                seeds = CATEGORY_SEEDS.get(category, [f"{category} topic"])
                fallback_keywords = seeds[:10]
                
                approved_path = approval_root / "approved" / f"{category}.txt"
                with open(approved_path, "w", encoding="utf-8") as f:
                    for kw in fallback_keywords:
                        f.write(f"{kw}\n")
                
                inputs_path = get_keywords_dir() / f"{category}.txt"
                inputs_path.parent.mkdir(parents=True, exist_ok=True)
                with open(inputs_path, "w", encoding="utf-8") as f:
                    for kw in fallback_keywords:
                        f.write(f"{kw}\n")
                
                processed_categories.add(category)
            except Exception:
                pass
            
            report["categories"][category] = {
                "error": f"{type(e).__name__}: {str(e)}"
            }
    
    # 리포트 저장
    ended_at = datetime.utcnow()
    report["ended_at"] = ended_at.isoformat() + "Z"
    report["total_elapsed_seconds"] = (ended_at - started_at).total_seconds()
    
    report_path = approval_root / "reports" / f"keyword_approval_{cycle_id}.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    # Audit: END
    append_jsonl(audit_path, AuditEvent.create("KEYWORD_APPROVAL_END", {
        "cycle_id": cycle_id,
        "total_approved": report["summary"]["total_approved"],
        "total_rejected": report["summary"]["total_rejected"]
    }).to_dict())
    
    return report

