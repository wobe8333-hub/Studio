---
name: ui-designer-memory
description: KAS ui-designer 에이전트 작업 이력 — 디자인 시스템 변경사항, CSS 변수 이력, Figma 연동 패턴
type: project
---

# UI Designer 메모리

## 디자인 시스템 현황

**현재 팔레트**: Red Light Glassmorphism
- `--p1: #FFB0B0` (살구레드 강조), `--p4: #B42828` (딥레드 탑바/버튼)
- `--card`: 라이트 `rgba(255,255,255,0.60)` / 다크 `rgba(42,16,16,0.80)`
- 다크모드: Crimson Night (`--background: #1a0808`)

## 성공 패턴

- `CARD_BASE` 상수 패턴: `background: 'var(--card)'` + `border: '1px solid var(--border)'`
- 하드코딩 `rgba(255,255,255,...)` 금지 — 다크모드 흰색 박스 발생
- 탭 컨테이너: `var(--tab-bg)` / `var(--tab-border)`

## 주의사항

- `globals.css`와 `web/public/` 소유. `frontend-dev` 직접 수정 금지
- `web/components/` 동시 수정 시 `frontend-dev`에게 SendMessage 조율 필수
- Figma 연동: `get_design_context()` → CSS 변수 매핑 → CARD_BASE 패턴 적용
