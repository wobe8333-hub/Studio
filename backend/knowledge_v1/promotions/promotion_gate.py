"""
승격 게이트 (증거 2+)
STEP E: 증거 소스 2개 이상인 키워드 승격
"""

import json
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Set
from collections import Counter

from backend.knowledge_v1.paths import get_root


def _read_keywords_from_file(file_path: Path) -> List[str]:
    """파일에서 키워드 리스트 읽기"""
    keywords: List[str] = []
    try:
        if file_path.suffix == ".jsonl":
            with open(file_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        data = json.loads(line)
                        # 다양한 필드에서 키워드 추출
                        kw = data.get("keyword") or data.get("title") or data.get("name")
                        if kw and isinstance(kw, str):
                            keywords.append(kw.strip())
                    except Exception:
                        continue
        else:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                # global_candidates, candidates, keywords 등 다양한 필드 지원
                if isinstance(data, list):
                    for item in data:
                        if isinstance(item, str):
                            keywords.append(item.strip())
                        elif isinstance(item, dict):
                            kw = item.get("keyword") or item.get("title") or item.get("name")
                            if kw and isinstance(kw, str):
                                keywords.append(kw.strip())
                elif isinstance(data, dict):
                    for key in ["global_candidates", "candidates", "keywords", "items"]:
                        if key in data:
                            items = data[key]
                            if isinstance(items, list):
                                for item in items:
                                    if isinstance(item, str):
                                        keywords.append(item.strip())
                                    elif isinstance(item, dict):
                                        kw = item.get("keyword") or item.get("title") or item.get("name")
                                        if kw and isinstance(kw, str):
                                            keywords.append(kw.strip())
    except Exception:
        pass
    return keywords


def promote_keywords(
    cycle_id: str,
    snapshot_dir: Path,
    anchor_file: Optional[Path] = None
) -> Dict[str, Any]:
    """
    증거 소스 2개 이상인 키워드 승격
    
    Args:
        cycle_id: cycle_id
        snapshot_dir: snapshots/<cycle_id> 디렉토리
        anchor_file: STEP D 앵커 파일 (선택)
    
    Returns:
        {
            "ok": bool,
            "cycle_id": str,
            "promoted_count": int,
            "promoted_keywords": List[str],
            "evidence_summary": Dict
        }
    """
    kd_root = get_root() / "keyword_discovery"
    promo_dir = kd_root / "promotions"
    promo_dir.mkdir(parents=True, exist_ok=True)
    
    # 증거 소스별 키워드 수집
    keyword_evidence: Dict[str, Set[str]] = {}  # keyword -> set of sources
    
    # S1: yt-dlp 기반 후보 (v7 산출물 전체)
    source1_keywords: List[str] = []
    for pattern in ["global_keywords_candidates.json", "global_context_candidates.jsonl", 
                    "kr_trend_keywords.json", "*_youtube.json", "*_trends.json", "*_dataset.json"]:
        for p in snapshot_dir.glob(pattern):
            kws = _read_keywords_from_file(p)
            source1_keywords.extend(kws)
            for kw in kws:
                if kw not in keyword_evidence:
                    keyword_evidence[kw] = set()
                keyword_evidence[kw].add("YTDLP")
    
    # S2: STEP D 앵커
    if anchor_file and anchor_file.exists():
        try:
            with open(anchor_file, "r", encoding="utf-8") as f:
                anchor_data = json.load(f)
                anchor_keywords = anchor_data.get("keywords", [])
                for kw in anchor_keywords:
                    if isinstance(kw, str) and kw.strip():
                        kw_clean = kw.strip()
                        if kw_clean not in keyword_evidence:
                            keyword_evidence[kw_clean] = set()
                        keyword_evidence[kw_clean].add("YOUTUBE_DATA_API")
        except Exception:
            pass
    
    # 승격 규칙: evidence_sources >= 2
    promoted_keywords: List[str] = []
    for kw, sources in keyword_evidence.items():
        if len(sources) >= 2:
            promoted_keywords.append(kw)
    
    promoted_at = datetime.utcnow().isoformat() + "Z"
    
    # promoted_keywords.jsonl 생성
    promoted_file = promo_dir / "promoted_keywords.jsonl"
    with open(promoted_file, "w", encoding="utf-8") as f:
        for kw in promoted_keywords:
            sources_list = sorted(list(keyword_evidence[kw]))
            evidence_hash = hashlib.sha256(
                f"{kw}|{','.join(sources_list)}|{cycle_id}".encode("utf-8")
            ).hexdigest()
            
            entry = {
                "keyword": kw,
                "evidence_sources": sources_list,
                "evidence_hash": evidence_hash,
                "cycle_id": cycle_id,
                "promoted_at": promoted_at
            }
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    
    # promoted_summary.json 생성
    summary = {
        "cycle_id": cycle_id,
        "promoted_count": len(promoted_keywords),
        "promoted_at": promoted_at
    }
    summary_file = promo_dir / "promoted_summary.json"
    with open(summary_file, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    
    return {
        "ok": len(promoted_keywords) >= 1,
        "cycle_id": cycle_id,
        "promoted_count": len(promoted_keywords),
        "promoted_keywords": promoted_keywords,
        "evidence_summary": {
            "ytdlp_count": len(source1_keywords),
            "anchor_count": len(keyword_evidence) - len(source1_keywords) if anchor_file else 0,
            "total_unique": len(keyword_evidence)
        }
    }

