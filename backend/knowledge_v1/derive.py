"""
Knowledge v1 Derive - 정규화·분해
"""

import json
import re
from typing import List
from backend.knowledge_v1.schema import KnowledgeAsset, DerivedChunk
from backend.knowledge_v1.store import append_jsonl, atomic_write_json
from backend.knowledge_v1.paths import get_chunks_path, get_store_root, ensure_dirs
from backend.knowledge_v1.audit import log_event


def derive(asset: KnowledgeAsset) -> List[DerivedChunk]:
    """
    자산을 정규화·분해하여 청크 생성
    
    Returns:
        List[DerivedChunk]: 생성된 청크 리스트 (최소 1건 보장)
    """
    chunks = []
    payload = asset.payload
    
    # 텍스트 추출 (우선순위: text → summary → content → 전체 JSON)
    text = ""
    if "text" in payload and payload["text"]:
        text = str(payload["text"])
    elif "summary" in payload and payload["summary"]:
        text = str(payload["summary"])
    elif "content" in payload and payload["content"]:
        text = str(payload["content"])
    else:
        text = json.dumps(payload, ensure_ascii=False)
    
    # fallback asset의 경우 텍스트가 짧을 수 있으므로 전체를 하나의 청크로 처리
    is_fallback = (hasattr(asset, 'license_source') and asset.license_source == "INTERNAL_SYNTHETIC") or asset.source_id == "fallback_synthetic"
    
    # fallback asset은 전체 텍스트를 하나의 청크로 처리
    if is_fallback:
        chunk_texts = [text] if text else [json.dumps(payload, ensure_ascii=False)]
    else:
        # v7 적재량 증대: 멀티 청크 생성 (1 asset → 3~5 chunks)
        # 청크 크기 범위: 400~800자 (평균 600자)
        min_chunk_size = 400
        max_chunk_size = 800
        target_chunk_size = 600  # 평균 타겟
        target_chunk_count = 3  # 최소 목표 청크 수
        
        chunk_texts = []
        
        # 문장 경계로 분할 시도
        sentences = re.split(r'[.!?]\s+', text)
        current_chunk = ""
        
        for sentence in sentences:
            if len(current_chunk) + len(sentence) < target_chunk_size:
                current_chunk += sentence + ". "
            else:
                if current_chunk:
                    chunk_texts.append(current_chunk.strip())
                current_chunk = sentence + ". "
        
        if current_chunk:
            chunk_texts.append(current_chunk.strip())
        
        # 청크가 없거나 너무 길면 길이로 분할
        if not chunk_texts:
            for i in range(0, len(text), target_chunk_size):
                chunk_texts.append(text[i:i+target_chunk_size])
        
        # v7 멀티 청크 확장: 청크 수가 부족하면 더 작은 청크로 분할
        if len(chunk_texts) < target_chunk_count and len(text) > min_chunk_size * target_chunk_count:
            # 기존 청크들을 더 작게 분할
            expanded_chunks = []
            split_size = max(min_chunk_size, len(text) // target_chunk_count)
            for existing_chunk in chunk_texts:
                if len(existing_chunk) > split_size:
                    for i in range(0, len(existing_chunk), split_size):
                        expanded_chunks.append(existing_chunk[i:i+split_size])
                else:
                    expanded_chunks.append(existing_chunk)
            
            # 목표 청크 수에 맞춰 조정 (최대 5개)
            if len(expanded_chunks) > 5:
                chunk_texts = expanded_chunks[:5]
            elif len(expanded_chunks) >= target_chunk_count:
                chunk_texts = expanded_chunks
    
    # 태그 생성
    base_tags = [asset.category] + asset.keywords + [asset.source_id]
    
    # 청크 생성
    for chunk_text in chunk_texts:
        if chunk_text and chunk_text.strip():  # 빈 텍스트 제외
            chunk = DerivedChunk.create(
                asset_id=asset.asset_id,
                text=chunk_text,
                tags=base_tags
            )
            chunks.append(chunk)
    
    # ★ 핵심 수정: fallback 보장 - derive 결과가 0건이면 fallback 1건 생성
    if not chunks:
        # fallback text 선택 (우선순위: summary → text → fallback message)
        fallback_text = (
            payload.get("summary")
            or payload.get("text")
            or f"[fallback-derived] {asset.category} :: {', '.join(asset.keywords)}"
        )
        
        # fallback DerivedChunk 생성
        fallback_chunk = DerivedChunk.create(
            asset_id=asset.asset_id,
            text=fallback_text,
            tags=base_tags
        )
        chunks.append(fallback_chunk)
    
    # 저장 (approved store에 저장)
    chunks_path = get_chunks_path("approved")
    ensure_dirs("approved")
    for chunk in chunks:
        append_jsonl(chunks_path, chunk.to_dict())
        log_event("DERIVE", {
            "chunk_id": chunk.chunk_id,
            "asset_id": asset.asset_id
        }, store="approved")
    
    # 인덱스 업데이트
    index_path = get_store_root("approved") / "index" / "index.json"
    index = {}
    if index_path.exists():
        with open(index_path, "r", encoding="utf-8") as f:
            index = json.load(f)
    
    # keyword -> chunk_id 매핑
    for keyword in asset.keywords:
        if keyword not in index:
            index[keyword] = []
        for chunk in chunks:
            if chunk.chunk_id not in index[keyword]:
                index[keyword].append(chunk.chunk_id)
    
    # category -> chunk_id 매핑
    if asset.category not in index:
        index[asset.category] = []
    for chunk in chunks:
        if chunk.chunk_id not in index[asset.category]:
            index[asset.category].append(chunk.chunk_id)
    
    atomic_write_json(index_path, index)
    
    # lifecycle_state 업데이트
    asset.lifecycle_state = "DERIVED"
    
    return chunks

