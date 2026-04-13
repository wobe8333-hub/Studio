#!/usr/bin/env python3
"""
PreCompact 훅 — 컨텍스트 압축 직전 Reflection 저장.
3가지 패턴 자동 감지: retry(재시도) · bottleneck(병목) · hitl(HITL 트리거).
async: true — 비차단 실행.
"""
from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).parent.parent.parent
FEEDBACK_PATH = ROOT / "data" / "global" / "learning_feedback.json"
HITL_PATH = ROOT / "data" / "global" / "notifications" / "hitl_signals.json"


def detect_retry_pattern(transcript: str) -> dict | None:
    """재시도 패턴 감지: 동일 도구·동일 경로 3회 이상 반복."""
    pattern = re.compile(r'"tool_name":\s*"(\w+)".*?"file_path":\s*"([^"]+)"', re.DOTALL)
    calls: dict[str, int] = {}
    for m in pattern.finditer(transcript):
        key = f"{m.group(1)}:{m.group(2)}"
        calls[key] = calls.get(key, 0) + 1

    hotspots = {k: v for k, v in calls.items() if v >= 3}
    if hotspots:
        top = max(hotspots, key=lambda k: hotspots[k])
        return {
            "pattern": "retry",
            "description": f"동일 도구/경로 {hotspots[top]}회 반복: {top}",
            "recommendation": "캐시·사전 검증으로 재시도 줄일 것",
        }
    return None


def detect_bottleneck_pattern(transcript: str) -> dict | None:
    """병목 패턴 감지: SendMessage가 동일 주제로 5회 이상 교환."""
    send_msgs = re.findall(r'"tool_name":\s*"SendMessage"', transcript)
    if len(send_msgs) >= 5:
        return {
            "pattern": "bottleneck",
            "description": f"SendMessage {len(send_msgs)}회 교환 — 의사결정 지연 의심",
            "recommendation": "다음 유사 미션에서 사전 합의 체크리스트 활용",
        }
    return None


def detect_hitl_pattern(transcript: str) -> dict | None:
    """HITL 패턴 감지: hitl_signals.json에 신규 신호 기록 여부."""
    try:
        if HITL_PATH.exists():
            signals = json.loads(HITL_PATH.read_text(encoding="utf-8"))
            pending = [s for s in signals.get("signals", []) if s.get("status") == "pending"]
            if pending:
                types = list({s.get("type", "unknown") for s in pending})
                return {
                    "pattern": "hitl",
                    "description": f"HITL 미결 {len(pending)}건: {types}",
                    "recommendation": "ceo 처리 전까지 관련 에이전트 대기 필요",
                }
    except Exception:
        pass
    return None


def main() -> None:
    try:
        raw = sys.stdin.read()
        data = json.loads(raw) if raw.strip() else {}
    except Exception:
        data = {}

    session_id = data.get("session_id", "unknown")
    transcript = data.get("transcript", "")
    timestamp = datetime.now(timezone.utc).isoformat()

    # 3가지 패턴 자동 감지
    detected_patterns = []
    for detector in (detect_retry_pattern, detect_bottleneck_pattern, detect_hitl_pattern):
        result = detector(transcript)
        if result:
            detected_patterns.append(result)

    try:
        FEEDBACK_PATH.parent.mkdir(parents=True, exist_ok=True)
        if FEEDBACK_PATH.exists():
            with open(FEEDBACK_PATH, encoding="utf-8-sig") as f:
                feedback = json.load(f)
        else:
            feedback = {
                "schema_version": "2.0",
                "description": "PreCompact 훅 — 세션 간 교훈 누적 (패턴 자동 감지 v10.0)",
                "sessions": [],
            }

        entry: dict = {
            "session_id": session_id,
            "compacted_at": timestamp,
            "note": "PreCompact hook fired — context compressed",
        }

        if detected_patterns:
            entry["auto_detected_patterns"] = detected_patterns

        feedback.setdefault("sessions", []).append(entry)

        # 최근 50개 세션만 유지
        feedback["sessions"] = feedback["sessions"][-50:]

        with open(FEEDBACK_PATH, "w", encoding="utf-8") as f:
            json.dump(feedback, f, ensure_ascii=False, indent=2)

    except Exception:
        pass


if __name__ == "__main__":
    main()
