---
description: cto 소환 — HITL/실패 자동 감지 + 팀 편성
---

cto 에이전트를 소환해서 다음 순서로 진행하세요:

1. HITL 미해결 신호 스캔:
   `data/global/notifications/hitl_signals.json` — `resolved: false` 항목

2. FAILED 런 스캔:
   `runs/*/manifest.json` — `run_state: "FAILED"` 항목

3. 이슈 유형별 팀 편성 (`AGENTS.md` 미션 프리셋 참조):
   - 백엔드 버그 → backend-engineer + qa-auditor
   - 프론트엔드 → frontend-engineer + qa-auditor
   - 파이프라인 실패 → pipeline-debugger + backend-engineer
   - DB 스키마 → db-architect + backend-engineer + frontend-engineer
   - 2명 이상 + 1일 이상 예상 시 → TeamCreate로 팀 결성

4. 소환 메시지 형식 필수:
   ```
   [미션 ID: YYYY-MM-DD-{유형}]
   목표: {한 줄}
   범위: {파일/모듈}
   제약조건: {금지 사항}
   완료 기준: {구체적 조건}
   ```

$ARGUMENTS 가 있으면 특정 미션 설명으로 사용합니다. 없으면 자율 감지.
이슈가 없으면 "이상 없음" 로그만 남기고 종료.
