"""
Meaning Failure Taxonomy - "의미 실패" 분류

의미 실패는 '기술적 실패'와 분리되어 기록된다.
"""

from enum import Enum
from typing import Any, Dict, Optional


class MeaningFailureType(str, Enum):
    FACTUAL_UNSUPPORTED = "FACTUAL_UNSUPPORTED"
    SCOPE_DRIFT = "SCOPE_DRIFT"
    LOW_SIGNAL = "LOW_SIGNAL"
    STYLE_BREAK = "STYLE_BREAK"
    CONTINUITY_BREAK = "CONTINUITY_BREAK"


def classify_meaning_failure(
    error: str,
    manifest: Optional[Dict[str, Any]] = None,
    step: Optional[str] = None
) -> MeaningFailureType:
    """
    v6 기준:
    - 의미 실패는 "항상 기록"되어야 하므로, 미분류 상태를 금지한다.
    - 현재 코드베이스에서 정답근거/연속성 스코어가 완비되지 않았으므로
      1차는 보수적인 문자열 기반 분류로 고정한다.
    """
    e = (error or "").lower()

    if any(k in e for k in ["citation", "근거", "unsupported", "hallucination", "factual"]):
        return MeaningFailureType.FACTUAL_UNSUPPORTED

    if any(k in e for k in ["scope", "drift", "irrelevant", "주제", "이탈"]):
        return MeaningFailureType.SCOPE_DRIFT

    if any(k in e for k in ["style", "tone", "정체성", "가드레일"]):
        return MeaningFailureType.STYLE_BREAK

    if any(k in e for k in ["continuity", "consistent", "연속", "미학"]):
        return MeaningFailureType.CONTINUITY_BREAK

    # default: LOW_SIGNAL (가장 보수적)
    return MeaningFailureType.LOW_SIGNAL

