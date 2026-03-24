"""
Reproducibility - 재현성 관리

처음문서_v1.2 기준:
"repro_key는 결정적으로 생성되어야 한다."
"""

import hashlib
import uuid
from typing import Dict, Any


def generate_repro_seed(run_id: str) -> int:
    """
    run_id로부터 결정적으로 seed 생성
    
    Args:
        run_id: 실행 ID (UUID)
    
    Returns:
        int: seed 값
    """
    # UUID를 정수로 변환 (결정적)
    try:
        uuid_obj = uuid.UUID(run_id)
        # UUID의 int 속성 사용 (결정적)
        seed = abs(uuid_obj.int) % (2**31)  # 32비트 정수 범위
        return seed
    except (ValueError, AttributeError):
        # UUID 파싱 실패 시 해시 기반 생성
        hash_obj = hashlib.md5(run_id.encode('utf-8'))
        seed = int(hash_obj.hexdigest()[:8], 16) % (2**31)
        return seed


def generate_repro_key(schema_version: str, run_id: str, seed: int) -> str:
    """
    repro_key 결정적으로 생성
    
    Args:
        schema_version: 스키마 버전
        run_id: 실행 ID
        seed: seed 값
    
    Returns:
        str: repro_key (sha256 hex)
    """
    combined = f"{schema_version}:{run_id}:{seed}"
    return hashlib.sha256(combined.encode('utf-8')).hexdigest()


def ensure_repro(manifest: Dict[str, Any], run_id: str) -> Dict[str, Any]:
    """
    manifest에 repro 필드 백필
    
    Args:
        manifest: run manifest
        run_id: 실행 ID
    
    Returns:
        Dict: repro 데이터
    """
    schema_version = manifest.get("schema_version", "v2_manifest_1_2")
    
    # 기존 repro가 있으면 유지
    existing_repro = manifest.get("repro", {})
    if existing_repro and existing_repro.get("repro_key"):
        return existing_repro
    
    # seed 결정적 생성
    seed = generate_repro_seed(run_id)
    
    # repro_key 생성
    repro_key = generate_repro_key(schema_version, run_id, seed)
    
    repro = {
        "seed": seed,
        "repro_key": repro_key
    }
    
    return repro

