"""
Knowledge v1 Layers - Layer 모델 정의
"""

from enum import Enum


class Layer(Enum):
    """지식 레이어"""
    APPROVED = "APPROVED"  # 승인된 레이어 (기존 knowledge_v1)
    DISCOVERY = "DISCOVERY"  # 발견 레이어 (신규 knowledge_v1_discovery)

