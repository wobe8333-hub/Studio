---
description: qa-auditor + performance-analyst 병렬 감사
---

superpowers:dispatching-parallel-agents 스킬을 활용하여
qa-auditor 와 performance-analyst 를 병렬 소환하세요.

**qa-auditor 담당**:
- OWASP Top 10: API 키 하드코딩, 경로 트래버설, SQL injection
- fs-helpers 검증: validateRunPath/validateChannelPath 미사용 API 라우트
- CLAUDE.md 핵심 규칙 준수: ssot.read_json, loguru, if root is not None

**performance-analyst 담당**:
- N+1 쿼리, 메모리 누수, 번들 사이즈
- time.sleep 하드코딩, 3초 폴링 → SSE 전환 후보
- TaskCompleted 훅 실행 시간 (async 전환 효과 측정)

두 에이전트의 결과를 종합하여 심각도 CRITICAL/HIGH 이슈를 먼저 보고하세요.

$ARGUMENTS: 감사 범위 지정 (예: "src/step08" 또는 "web/app/api"). 미지정 시 전체.
