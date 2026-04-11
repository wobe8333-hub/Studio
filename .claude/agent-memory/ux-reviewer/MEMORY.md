---
name: ux-reviewer-memory
description: KAS ux-reviewer 에이전트 작업 이력 — UX 감사 결과, WCAG 준수 현황
type: project
---

# UX Reviewer 메모리

## WCAG 준수 현황

아직 감사 미실시 — 첫 감사 후 업데이트 예정.

## 반복 이슈 패턴

아직 기록 없음.

## 주의사항

- Read-only 에이전트. 발견 이슈는 반드시 SendMessage로 전달 (frontend-dev 또는 ui-designer)
- 모바일 터치 타겟 44px 기준, 색상 대비 4.5:1 (일반 텍스트) 이 주요 체크포인트
- `bottom-nav.tsx` (모바일 탭바) 접근성이 핵심 감사 대상
