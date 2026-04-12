# KAS Agent Teams v5 운영 가이드

> **버전**: v5.0 | **에이전트 수**: 12개 | **기준일**: 2026-04-11

---

## 4-Layer 구조

```
L0: mission-controller (Opus, 조율 전용)
L1: python-dev | web-dev | design-dev (Builder, worktree)
L2: quality-security | ops-monitor (Guardian, 상시)
L3: db-architect | refactoring-surgeon | pipeline-debugger |
    performance-profiler | ux-a11y | release-manager (온디맨드)
```

---

## 파일 소유권

| 에이전트 | 소유 경로 | 금지 경로 |
|----------|----------|---------|
| python-dev | src/, tests/, scripts/ | web/ |
| web-dev | web/app/, web/lib/, web/hooks/, web/components/(로직) | src/, globals.css |
| design-dev | web/app/globals.css, web/public/, assets/thumbnails/, web/components/(스타일) | src/, tests/ |
| ops-monitor | .claude/, CLAUDE.md, AGENTS.md, docs/, .github/ | src/step*, web/app/, web/components/ |
| quality-security | Read-only 감사 전용 | Write, Edit 금지 |
| ux-a11y | Read-only 감사 전용 | Write, Edit 금지 |
| video-specialist | Read-only 영상 콘텐츠 감사 | Write, Edit 금지 |
| performance-profiler | Read-only 분석 전용 | Write, Edit 금지 |

---

## 미션 프리셋

| 미션 유형 | 소환 조합 |
|-----------|-----------|
| 백엔드 기능/버그 | python-dev + quality-security |
| 프론트엔드 기능 | web-dev + quality-security |
| UI/디자인 변경 | design-dev + ux-a11y |
| 보안 취약점 수정 | quality-security → python-dev/web-dev |
| 성능 최적화 | performance-profiler + python-dev/web-dev |
| DB 스키마 변경 | db-architect + python-dev + web-dev |
| 파이프라인 장애 | pipeline-debugger + python-dev |
| 대규모 리팩토링 | refactoring-surgeon + python-dev |
| 릴리스 배포 | release-manager + python-dev |
| UX/접근성 감사 | ux-a11y → web-dev/design-dev |
| 영상 콘텐츠 감사 | video-specialist → python-dev/design-dev |

---

## 통신 프로토콜

**mission-controller → 팀원 소환**:
```
[미션 ID: YYYY-MM-DD-{유형}]
목표: {한 줄}
범위: {파일/모듈}
제약조건: {금지 사항}
완료 기준: {구체적 조건}
```

**Guardian → Builder (이슈 전달)**:
```
[이슈 유형: 보안/품질/UX]
파일: {경로:줄번호}
심각도: CRITICAL/HIGH/MEDIUM/LOW
설명: {문제와 영향}
수정 담당: {python-dev/web-dev/design-dev}
```

**Builder 간 API 변경 알림**:
```
[API 변경 알림]
엔드포인트: {경로}
변경 전/후: {포맷}
영향 범위: {프론트엔드 컴포넌트}
```

---

## Anti-Patterns

- `python-dev`가 `web/` 수정 시도 — per-agent hook이 차단
- `quality-security`가 코드 직접 수정 — disallowedTools로 차단
- Opus 에이전트 동시 2명 초과 소환 — 비용 폭주
- L3 동시 5명 초과 소환 — 조율 오버헤드

---

## 자주 쓰는 커맨드

```bash
claude agents                                    # 13개 에이전트 목록 확인
pytest tests/ -x -q --ignore=tests/test_step08_integration.py  # 테스트
ruff check src/ --fix --select=E,W,F,I          # 린팅
cd web && npm run build                          # 빌드 검증
```

## Slash Commands (`.claude/commands/`)

| 커맨드 | 설명 |
|---|---|
| `/mission [설명]` | mission-controller 소환 — HITL/실패 자동 감지 + 팀 편성 |
| `/audit [범위]` | quality-security + performance-profiler 병렬 감사 |
| `/release [버전]` | release-manager 소환 — CHANGELOG + tag + PR |
| `/kpi [채널]` | AnalyticsLearningAgent KPI 수집 및 Phase 분석 |
| `/debug-pipeline [step]` | pipeline-debugger 소환 — Step 실패 분석 |
| `/verify [범위]` | 완료 전 검증 — pytest + ruff + build 통과 확인 |
