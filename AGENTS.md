# KAS Agent Teams v5.2 운영 가이드

> **버전**: v5.2 | **에이전트 수**: 14개 | **기준일**: 2026-04-12

---

## 4-Layer 구조

```
L0: mission-controller (Opus, 조율 전용)
L1: python-dev | web-dev | design-dev (Builder, worktree)
L2: quality-security | ops-monitor (Guardian, 상시)
L3: db-architect | refactoring-surgeon | pipeline-debugger |
    performance-profiler | ux-a11y | release-manager | video-specialist |
    revenue-strategist (온디맨드)
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
| pipeline-debugger | Read-only 파이프라인 분석 | Write, Edit 금지 |
| revenue-strategist | Read-only 수익 전략 감사 | Write, Edit 전면 금지 |
| mission-controller | 조율 전용 (파일 편집 불가) | Write, Edit 전면 금지 |
| db-architect | scripts/supabase_schema.sql, scripts/migrations/, web/lib/types.ts (스키마 한정) | src/, web/app/, web/components/ |
| refactoring-surgeon | src/ 리팩토링 전용 (worktree) | web/, tests/ 삭제, src/step08/__init__.py |
| release-manager | CHANGELOG.md (단독), git tag | src/step*, web/app/, src/step08/__init__.py |

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
| 수익 전략 감사 | revenue-strategist → python-dev (scorer/portfolio) + video-specialist (SEO) |
| 월간 주제 포트폴리오 | revenue-strategist + pipeline-debugger (트렌드 품질) → python-dev |

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
[이슈 유형: 보안/품질/UX/수익]
파일: {경로:줄번호}
심각도: CRITICAL/HIGH/MEDIUM/LOW
설명: {문제와 영향}
수정 담당: {python-dev/web-dev/design-dev}
```

---

## Anti-Patterns

- `python-dev`가 `web/` 수정 시도 — per-agent hook이 차단
- `quality-security`가 코드 직접 수정 — disallowedTools로 차단
- Opus 에이전트 동시 2명 초과 소환 — 비용 폭주
- L3 동시 5명 초과 소환 — 조율 오버헤드
- `CHANGELOG.md`를 release-manager 외 에이전트가 편집 — 릴리스 이력 충돌
- db-architect 없이 src/에서 스키마 변경 — RLS/types.ts 동기화 누락

---

## Playwright 사용 우선순위

1. web-dev — E2E 테스트 작성·실행 (1차 소유)
2. ux-a11y — WCAG/반응형 감사 (read-only, Haiku)
3. design-dev — 시각 검증 스크린샷 비교
4. video-specialist — /runs 썸네일 검토

충돌 시 web-dev 우선, 감사 에이전트는 read-only 모드 유지.

---

## 진단 에이전트 경계 (3축)

- **pipeline-debugger** (Sonnet): Step 실패 "원인" (로그·manifest·quota·지식 품질·Stage1~3 팩트체크)
- **performance-profiler** (Haiku): 성공 런의 "최적화" (N+1·메모리·번들·time.sleep 하드코딩)
- **revenue-strategist** (Sonnet): 주제 선별 "수익성" (scorer·portfolio·winning pattern 적중률)

동일 이슈에 둘 이상 소환 금지 — mission-controller가 1개 선택.

---

## Supabase RLS 경계

- **db-architect** (Opus): RLS 정책 1차 설계 + 마이그레이션 + types.ts 동기화 (3종 세트 동시)
- **quality-security** (Sonnet): RLS 감사만 (설계 변경 금지)
- 이슈 발견 시 SendMessage로 db-architect에 전달
- 파괴적 변경(DROP, 타입 축소) 시 백필 스크립트 필수

---

## teammate 모드 동작 (공식문서 § Agent Teams)

- 모든 14개 agent는 teammate 모드(`CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`)로 운영.
- `skills`·`mcpServers`는 teammate 모드에서 무시됨 (공식 문서 명시) — agent frontmatter에 선언하지 않음.
- context7·playwright·figma MCP는 `.claude/settings.local.json`에서 전역 로드.

| 에이전트 | 권장 skill (프로젝트 세션 전역) |
|---|---|
| mission-controller | superpowers:brainstorming, superpowers:writing-plans |
| python-dev | superpowers:test-driven-development, superpowers:systematic-debugging |
| web-dev | superpowers:test-driven-development, frontend-design:frontend-design |
| design-dev | frontend-design:frontend-design, ui-ux-pro-max:ui-ux-pro-max |
| quality-security | superpowers:requesting-code-review |
| ops-monitor | claude-md-management:revise-claude-md |

---

## 실전 협업 시나리오 (공식 § Use case examples 패턴)

### 시나리오 1: 파이프라인 장애 (Step08 FFmpeg 실패)
```
/mission "Step08 FFmpeg 에러 조사 — runs/CH1/*/step08/ 최근 3건 FAILED"
→ mission-controller spawn:
  1) pipeline-debugger: 로그·manifest·쿼터 분석 (read-only)
  2) python-dev: 수정 구현 (worktree, src/step08/ffmpeg_composer.py)
→ pipeline-debugger SendMessage로 python-dev에 근본 원인 전달 → 수정 → pytest → 완료
```

### 시나리오 2: UI 리디자인 (접근성 강화)
```
/mission "홈 탭 글래스모피즘 대비 강화 + 접근성 WCAG AA"
→ mission-controller spawn:
  1) design-dev: globals.css + 컴포넌트 스타일 (worktree)
  2) ux-a11y: WCAG 감사 (read-only, Haiku)
→ ux-a11y가 design-dev에 색 대비 이슈 전달 → design-dev 수정 → npm run build 통과
```

### 시나리오 3: Supabase 스키마 + 타입 동기화
```
/mission "trend_topics에 is_approved_by 컬럼 추가"
→ mission-controller spawn:
  1) db-architect: SQL 마이그레이션 + RLS (Opus, worktree)
  2) python-dev: src/agents/ui_ux/ 동기화 로직 (worktree)
  3) web-dev: web/lib/types.ts 재생성 (worktree)
→ db-architect가 나머지 2명에 API 변경 알림 → 병렬 구현 → 통합
```

---

## 자주 쓰는 커맨드

```bash
claude agents                                    # 14개 에이전트 목록 확인
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
| `/revenue-audit` | revenue-strategist 소환 — scorer/portfolio/winning pattern 감사 |
