"""저작권 위험 사전 체크 (Plan C-2 B7).

Gemini(또는 Claude fallback)로 대본을 분석해 Content ID 스트라이크 위험을
0~1 점수로 산출한다. 0.7 이상이면 Step11 QA 게이트에서 경고를 발행한다.

사용법:
    from src.step11.copyright_checker import check_copyright_risk

    result = check_copyright_risk(script_text)
    # {"risk_score": 0.15, "reasons": []}
"""
import json

from loguru import logger

from src.core.llm_client import generate_text

COPYRIGHT_RISK_PROMPT = """아래 유튜브 영상 대본에서 저작권 위험 요소를 분석하세요.

대본:
{script}

다음 JSON 형식으로만 답하세요:
{{
  "risk_score": 0.0~1.0 사이 숫자 (0=안전, 1=매우 위험),
  "reasons": ["위험 요소 설명 목록"]
}}

위험 요소 예시: 저작권 있는 노래 가사 직접 인용, 실존 인물 허위 사실,
상표 캐릭터 무단 사용, 다른 영상 장면 직접 묘사.
교육·정보 목적의 일반 지식은 위험하지 않습니다."""

# 저작권 경고 임계값
HIGH_RISK_THRESHOLD = 0.7


def check_copyright_risk(script: str) -> dict:
    """대본의 저작권 위험을 분석한다.

    Args:
        script: 분석할 영상 대본 텍스트

    Returns:
        {"risk_score": float, "reasons": list[str]}
        risk_score 0.7 이상이면 업로드 전 검토 권장
    """
    try:
        prompt = COPYRIGHT_RISK_PROMPT.format(script=script[:3000])
        response = generate_text(prompt)

        # JSON 추출 (Gemini가 마크다운 코드블록을 붙일 수 있음)
        text = response.strip()
        if text.startswith("```"):
            text = "\n".join(text.split("\n")[1:-1]).strip()

        start = text.find("{")
        end = text.rfind("}") + 1
        if start == -1 or end == 0:
            raise ValueError(f"JSON 없음: {text[:100]}")

        result = json.loads(text[start:end])
        risk_score = float(result.get("risk_score", 0.0))
        reasons = result.get("reasons", [])

        if risk_score >= HIGH_RISK_THRESHOLD:
            logger.warning(
                f"[COPYRIGHT] 고위험 대본 감지: score={risk_score:.2f} / 사유={reasons}"
            )
        else:
            logger.info(f"[COPYRIGHT] 위험 점수: {risk_score:.2f}")

        return {"risk_score": risk_score, "reasons": reasons}

    except Exception as e:
        logger.warning(f"[COPYRIGHT] 분석 실패, 안전으로 처리: {e}")
        return {"risk_score": 0.0, "reasons": []}
