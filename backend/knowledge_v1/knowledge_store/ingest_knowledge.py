"""
지식 적재
STEP E: Wikipedia에서 지식 문서 적재
"""

import json
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional

from backend.knowledge_v1.paths import get_root


def _fetch_wikipedia_content(keyword: str, lang: str = "ko") -> Optional[Dict[str, Any]]:
    """Wikipedia에서 콘텐츠 가져오기"""
    try:
        import urllib.request
        import urllib.parse
        
        # Wikipedia API
        base_url = f"https://{lang}.wikipedia.org/api/rest_v1/page/summary/"
        encoded_keyword = urllib.parse.quote(keyword)
        url = base_url + encoded_keyword
        
        with urllib.request.urlopen(url, timeout=10) as response:
            if response.status == 200:
                data = json.loads(response.read().decode("utf-8"))
                return {
                    "title": data.get("title", keyword),
                    "extract": data.get("extract", ""),
                    "url": data.get("content_urls", {}).get("desktop", {}).get("page", ""),
                    "lang": lang
                }
    except Exception:
        # ko 실패 시 en 시도
        if lang == "ko":
            return _fetch_wikipedia_content(keyword, lang="en")
        return None
    
    return None


def ingest_knowledge(
    promoted_keywords_file: Path,
    cycle_id: str
) -> Dict[str, Any]:
    """
    승격된 키워드에 대한 지식 문서 적재
    
    Args:
        promoted_keywords_file: promoted_keywords.jsonl 파일 경로
        cycle_id: cycle_id
    
    Returns:
        {
            "ok": bool,
            "cycle_id": str,
            "ingested_count": int,
            "documents_count": int,
            "errors": List[str]
        }
    """
    ks_dir = get_root() / "knowledge_store"
    ks_dir.mkdir(parents=True, exist_ok=True)
    manifest_file = ks_dir / "manifest.jsonl"
    
    ingested_count = 0
    documents_count = 0
    errors: List[str] = []
    
    # promoted_keywords.jsonl 읽기
    promoted_keywords: List[Dict[str, Any]] = []
    if promoted_keywords_file.exists():
        try:
            with open(promoted_keywords_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            entry = json.loads(line)
                            promoted_keywords.append(entry)
                        except Exception:
                            continue
        except Exception as e:
            errors.append(f"read_promoted_file: {type(e).__name__}")
    
    collected_at = datetime.utcnow().isoformat() + "Z"
    
    # 각 키워드당 최소 1개 문서 적재
    for entry in promoted_keywords:
        keyword = entry.get("keyword", "").strip()
        if not keyword:
            continue
        
        evidence_hash = entry.get("evidence_hash", "")
        
        # keyword_hash 계산
        keyword_hash = hashlib.sha256(keyword.encode("utf-8")).hexdigest()
        
        # Wikipedia에서 콘텐츠 가져오기
        wiki_content = _fetch_wikipedia_content(keyword)
        if not wiki_content:
            errors.append(f"wikipedia_fetch_failed: {keyword}")
            continue
        
        # doc_id 계산
        content_hash = hashlib.sha256(wiki_content["extract"].encode("utf-8")).hexdigest()
        doc_id = hashlib.sha256(
            f"wikipedia|{wiki_content['url']}|{content_hash}".encode("utf-8")
        ).hexdigest()
        
        # 문서 저장
        keyword_dir = ks_dir / keyword_hash
        keyword_dir.mkdir(parents=True, exist_ok=True)
        doc_file = keyword_dir / f"{doc_id}.json"
        
        doc_data = {
            "keyword": keyword,
            "source": "wikipedia",
            "url": wiki_content["url"],
            "collected_at": collected_at,
            "content_hash": content_hash,
            "raw_text": wiki_content["extract"],
            "summary": wiki_content["extract"][:500] if len(wiki_content["extract"]) > 500 else wiki_content["extract"],
            "evidence_hash": evidence_hash
        }
        
        with open(doc_file, "w", encoding="utf-8") as f:
            json.dump(doc_data, f, ensure_ascii=False, indent=2)
        
        # manifest.jsonl append
        manifest_entry = {
            "keyword": keyword,
            "keyword_hash": keyword_hash,
            "doc_id": doc_id,
            "source": "wikipedia",
            "url": wiki_content["url"],
            "content_hash": content_hash,
            "evidence_hash": evidence_hash,
            "collected_at": collected_at
        }
        with open(manifest_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(manifest_entry, ensure_ascii=False) + "\n")
        
        ingested_count += 1
        documents_count += 1
    
    return {
        "ok": ingested_count >= 1,
        "cycle_id": cycle_id,
        "ingested_count": ingested_count,
        "documents_count": documents_count,
        "errors": errors
    }

