---
name: security-auditor-memory
description: KAS security-auditor 에이전트 작업 이력 — 발견 취약점 패턴, 수정 이력
type: project
---

# Security Auditor 메모리

## 반복 취약점 패턴

아직 기록 없음 — 첫 감사 후 업데이트 예정.

## 감사 이력

아직 기록 없음.

## 주의사항

- `security-sentinel`(상시 감시)과 역할 중복 주의. `security-auditor`는 PR 전 심층 감사 전담
- `validateRunPath()` / `validateChannelPath()` 미사용 패턴이 가장 빈번한 취약점
- `web/middleware.ts` 생성 금지 — `proxy.ts`가 Next.js 16.2.2 미들웨어 파일
