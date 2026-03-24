"""
Knowledge v1 Schema - Pydantic 모델 정의
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime
import uuid
from backend.knowledge_v1.utils.keyword_contract import normalize_kw, normalize_kw_list


@dataclass
class KnowledgeAsset:
    """지식 자산 (RAW 단계)"""
    asset_id: str
    category: str  # history|geo|mystery|economy|war|animation|science|common_sense|papers
    keywords: List[str]
    source_id: str
    source_ref: str  # URL or API template or "fixture://…" or "internal://…"
    fetched_at: str  # UTC ISO8601 "Z"
    raw_hash: str  # sha256
    license_status: str  # "KNOWN"|"UNKNOWN"
    usage_rights: str  # "ALLOWED"|"RESTRICTED"|"UNKNOWN"
    trust_level: str  # "LOW"|"MEDIUM"|"HIGH"
    impact_scope: str  # "LOW"|"MEDIUM"|"HIGH"
    lifecycle_state: str  # "RAW"|"DERIVED"|"USED"|"BLOCKED"
    payload: Dict
    license_source: Optional[str] = field(default=None)  # "INTERNAL_SYNTHETIC" | 기타 소스 식별자
    layer: Optional[str] = field(default=None)  # "DISCOVERY"|"APPROVED" 등 저장 레이어 식별
    source_score: Optional[int] = field(default=None)  # 소스별 품질 점수 (0~100)
    
    @classmethod
    def create(cls, category: str, keywords: List[str], source_id: str, source_ref: str, payload: Dict,
               license_status: str = "UNKNOWN", usage_rights: str = "UNKNOWN", trust_level: str = "MEDIUM",
               impact_scope: str = "MEDIUM", license_source: Optional[str] = None) -> "KnowledgeAsset":
        """
        새 자산 생성
        
        Args:
            category: 카테고리 (필수, None/빈 문자열 불가)
            keywords: 키워드 리스트
            source_id: 소스 ID
            source_ref: 소스 참조
            payload: 페이로드 (category가 없으면 payload에서 추출 시도)
            license_status: 라이선스 상태
            usage_rights: 사용 권한
            trust_level: 신뢰 수준
            impact_scope: 영향 범위
            license_source: 라이선스 소스
        """
        # category 전파: 인자 우선, 없으면 payload에서 추출
        final_category = category
        if not final_category or final_category.strip() == "":
            # payload에서 category 추출 시도
            if isinstance(payload, dict):
                final_category = payload.get("category", "")
        
        # 최종 검증: category가 여전히 없으면 에러
        if not final_category or final_category.strip() == "":
            raise ValueError(
                f"KnowledgeAsset.category must be provided as argument or in payload. "
                f"source_id={source_id}, payload_keys={list(payload.keys()) if isinstance(payload, dict) else 'N/A'}"
            )
        
        normalized_keywords = normalize_kw_list(keywords)
        if not normalized_keywords:
            raise ValueError("KnowledgeAsset.keywords must contain at least one string keyword")

        if isinstance(payload, dict):
            payload_kw = normalize_kw(payload.get("keyword"))
            if payload_kw:
                payload["keyword"] = payload_kw

        return cls(
            asset_id=str(uuid.uuid4()),
            category=final_category,
            keywords=normalized_keywords,
            source_id=source_id,
            source_ref=source_ref,
            fetched_at=datetime.utcnow().isoformat() + "Z",
            raw_hash="",  # 나중에 계산
            license_status=license_status,
            usage_rights=usage_rights,
            trust_level=trust_level,
            impact_scope=impact_scope,
            lifecycle_state="RAW",
            payload=payload,
            license_source=license_source
        )
    
    def validate(self) -> None:
        """
        KnowledgeAsset 검증 (persistence 전 필수)
        
        Raises:
            ValueError: category가 None이거나 빈 문자열인 경우
        """
        if not self.category or self.category.strip() == "":
            raise ValueError(
                f"KnowledgeAsset.category must be set before persistence. "
                f"asset_id={self.asset_id}, source_id={self.source_id}"
            )
        if not isinstance(self.keywords, list):
            raise ValueError(f"KnowledgeAsset.keywords must be list[str], got: {type(self.keywords).__name__}")
        normalized = normalize_kw_list(self.keywords)
        if not normalized:
            raise ValueError(f"KnowledgeAsset.keywords empty after normalize. asset_id={self.asset_id}")
        if any(not isinstance(k, str) for k in normalized):
            raise ValueError(f"KnowledgeAsset.keywords contains non-str element. asset_id={self.asset_id}")
        self.keywords = normalized
        if isinstance(self.payload, dict):
            payload_kw = normalize_kw(self.payload.get("keyword"))
            if payload_kw:
                self.payload["keyword"] = payload_kw
    
    def to_dict(self) -> Dict:
        """dict로 변환 (모든 필드 포함)"""
        result = {
            "asset_id": self.asset_id,
            "category": self.category,
            "keywords": self.keywords,
            "source_id": self.source_id,
            "source_ref": self.source_ref,
            "fetched_at": self.fetched_at,
            "raw_hash": self.raw_hash,
            "license_status": self.license_status,
            "usage_rights": self.usage_rights,
            "trust_level": self.trust_level,
            "impact_scope": self.impact_scope,
            "lifecycle_state": self.lifecycle_state,
            "payload": self.payload,
            "license_source": self.license_source,  # 항상 포함 (None이어도)
            "layer": self.layer,
            "source_score": self.source_score  # 항상 포함 (None이어도)
        }
        return result
    
    @classmethod
    def from_dict(cls, d: Dict) -> "KnowledgeAsset":
        """dict에서 생성 (스키마 외 키는 무시)"""
        d_copy = dict(d)

        # Optional 필드 기본값 보정
        if "license_source" not in d_copy:
            d_copy["license_source"] = None
        if "layer" not in d_copy:
            d_copy["layer"] = None
        if "source_score" not in d_copy:
            d_copy["source_score"] = None

        # dataclass 필드만 허용 (그 외 추가키는 무시)
        allowed = set(cls.__dataclass_fields__.keys())
        filtered = {k: v for k, v in d_copy.items() if k in allowed}
        if "keywords" in filtered:
            filtered["keywords"] = normalize_kw_list(filtered.get("keywords"))
        if isinstance(filtered.get("payload"), dict):
            payload_kw = normalize_kw(filtered["payload"].get("keyword"))
            if payload_kw:
                filtered["payload"]["keyword"] = payload_kw

        obj = cls(**filtered)
        obj.validate()
        return obj


@dataclass
class DerivedChunk:
    """정규화된 청크 (DERIVED 단계)"""
    chunk_id: str
    asset_id: str
    text: str
    tags: List[str]
    created_at: str
    
    @classmethod
    def create(cls, asset_id: str, text: str, tags: List[str]) -> "DerivedChunk":
        """새 청크 생성"""
        return cls(
            chunk_id=str(uuid.uuid4()),
            asset_id=asset_id,
            text=text,
            tags=tags,
            created_at=datetime.utcnow().isoformat() + "Z"
        )
    
    def to_dict(self) -> Dict:
        """dict로 변환"""
        return {
            "chunk_id": self.chunk_id,
            "asset_id": self.asset_id,
            "text": self.text,
            "tags": self.tags,
            "created_at": self.created_at
        }
    
    @classmethod
    def from_dict(cls, d: Dict) -> "DerivedChunk":
        """dict에서 생성"""
        return cls(**d)


@dataclass
class Eligibility:
    """사용 가능성 분류"""
    asset_id: str
    eligible_for: str  # "BLOCKED"|"REFERENCE_ONLY"|"LIMITED_INJECTION"|"FULLY_USABLE"
    reason: str
    decided_at: str
    
    @classmethod
    def create(cls, asset_id: str, eligible_for: str, reason: str) -> "Eligibility":
        """새 분류 생성"""
        return cls(
            asset_id=asset_id,
            eligible_for=eligible_for,
            reason=reason,
            decided_at=datetime.utcnow().isoformat() + "Z"
        )
    
    def to_dict(self) -> Dict:
        """dict로 변환"""
        return {
            "asset_id": self.asset_id,
            "eligible_for": self.eligible_for,
            "reason": self.reason,
            "decided_at": self.decided_at
        }
    
    @classmethod
    def from_dict(cls, d: Dict) -> "Eligibility":
        """dict에서 생성"""
        return cls(**d)


@dataclass
class AuditEvent:
    """감사 이벤트"""
    event_id: str
    event_type: str  # "INGEST"|"LICENSE_BLOCK"|"DERIVE"|"CLASSIFY"|"QUERY"|"USE_GATE"
    ts: str
    details: Dict
    
    @classmethod
    def create(cls, event_type: str, details: Dict) -> "AuditEvent":
        """새 이벤트 생성"""
        return cls(
            event_id=str(uuid.uuid4()),
            event_type=event_type,
            ts=datetime.utcnow().isoformat() + "Z",
            details=details
        )
    
    def to_dict(self) -> Dict:
        """dict로 변환"""
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "ts": self.ts,
            "details": self.details
        }
    
    @classmethod
    def from_dict(cls, d: Dict) -> "AuditEvent":
        """dict에서 생성"""
        return cls(**d)

