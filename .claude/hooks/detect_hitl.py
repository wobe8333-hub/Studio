#!/usr/bin/env python3
"""
UserPromptSubmit 훅 — HITL 키워드 감지 및 hitl_signals.json 자동 삽입 + Slack 알림.
사용자 입력에서 수주/계약/예산초과 등 HITL 트리거 키워드 탐지.
sync 실행 (async: false) — 사용자 입력 전처리 필수.
"""
from __future__ import annotations

import json
import os
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).parent.parent.parent

HITL_KEYWORDS = {
    "수주": "sales_contract",
    "계약": "sales_contract",
    "견적": "sales_proposal",
    "제안서": "sales_proposal",
    "예산 초과": "budget_exceeded",
    "비용 초과": "budget_exceeded",
    "콘텐츠 정책": "content_policy",
    "저작권": "copyright_issue",
    "신규 채널": "new_channel",
    "외국어": "multilingual",
    "법적": "legal_review",
    "계약서": "legal_review",
    "NDA": "legal_review",
}

HITL_PATH = ROOT / "data" / "global" / "notifications" / "hitl_signals.json"


def main() -> None:
    try:
        raw = sys.stdin.read()
        data = json.loads(raw)
        prompt = data.get("prompt", "")
    except Exception:
        sys.exit(0)

    triggered = []
    for keyword, signal_type in HITL_KEYWORDS.items():
        if keyword in prompt:
            triggered.append({"keyword": keyword, "type": signal_type})

    if not triggered:
        sys.exit(0)

    # hitl_signals.json에 신호 삽입
    try:
        HITL_PATH.parent.mkdir(parents=True, exist_ok=True)
        if HITL_PATH.exists():
            with open(HITL_PATH, encoding="utf-8-sig") as f:
                signals = json.load(f)
        else:
            signals = {"signals": []}

        for t in triggered:
            signals.setdefault("signals", []).append({
                "type": t["type"],
                "keyword": t["keyword"],
                "detected_at": datetime.now(timezone.utc).isoformat(),
                "source": "UserPromptSubmit",
                "resolved": False,
            })

        with open(HITL_PATH, "w", encoding="utf-8") as f:
            json.dump(signals, f, ensure_ascii=True, indent=2)

        # Slack 알림 (SLACK_WEBHOOK_URL 설정 시)
        slack_url = os.environ.get("SLACK_WEBHOOK_URL", "")
        if slack_url and triggered:
            _send_slack(slack_url, triggered, prompt[:100])

    except Exception:
        pass

    sys.exit(0)


def _send_slack(webhook_url: str, triggered: list[dict], prompt_preview: str) -> None:
    """Slack webhook으로 HITL 알림 전송"""
    try:
        types = ", ".join(t["type"] for t in triggered)
        payload = {
            "text": f"🚨 *Loomix HITL 감지*\n"
                    f"트리거: `{types}`\n"
                    f"키워드: {', '.join(t['keyword'] for t in triggered)}\n"
                    f"프롬프트 미리보기: _{prompt_preview}_\n"
                    f"→ `data/global/notifications/hitl_signals.json` 확인"
        }
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            webhook_url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=3):
            pass
    except Exception:
        pass  # Slack 실패는 HITL 기록 중단 사유 아님


if __name__ == "__main__":
    main()
