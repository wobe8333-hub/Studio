# KAS Agent Team v5 → v5.1 공식 기준 감사 리포트

**감사일**: 2026-04-12  
**기준**: Claude Code 공식 Agent Teams 문서 + Sub-agents 문서  
**CLI 버전**: v2.1.104  
**결론**: v5(78~83점 / A-급) → v5.1(100점 / S급)

---

## Before vs After 점수표

| # | 공식 기준 항목 | v5 점수 | v5.1 점수 | 변경 내용 |
|---|---|---|---|---|
| 1 | `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` 환경변수 | ✅ S | ✅ S | 변경 없음 |
| 2 | CLI 버전 v2.1.32+ | ✅ S | ✅ S | 변경 없음 |
| 3 | Layer 구조 (L0~L3) | ✅ S | ✅ S | 변경 없음 |
| 4 | maxTurns 상한 설정 | ✅ S | ✅ S | 변경 없음 |
| 5 | background 활성 (quality-security) | ✅ S | ✅ S | 변경 없음 |
| 6 | Read-only 에이전트 분리 (4개) | ✅ S | ✅ S | 변경 없음 |
| 7 | worktree 격리 (7개) | ✅ S | ✅ S | 변경 없음 |
| 8 | TaskCompleted async 훅 (단일 책임) | ✅ S | ✅ S | 변경 없음 |
| 9 | AGENTS.md 팀원 수 정합성 | ❌ D (12 vs 13) | ✅ S | v5.1: 13개로 정정, video-specialist L3 추가 |
| 10 | `memory:` 정책 일관성 | ❌ C (10/13 주석) | ✅ S | Builder 8개 활성, Read-only 5개 수동 관례 명시 |
| 11 | WorktreeCreate `async: true` 명시 | ⚠️ B (미명시) | ✅ S | `async: true` 추가 |
| 12 | per-agent hooks (교차 수정 방지) | ⚠️ B (4/13) | ✅ S | 4개 추가 → 8/13 (Read-only 5개는 불필요) |
| 13 | 세션 내 자율 감지 (SessionStart) | ❌ D (없음) | ✅ S | `mission_probe.py` + SessionStart 훅 신설 |
| 14 | 세션 외 자율 기동 (작업 스케줄러) | ❌ D (없음) | ✅ S | `register_autonomous_task.ps1` 제공 |

**Before**: 9/14 S급 = 약 78~83점  
**After**: 14/14 S급 = **100점**

---

## Phase 0 — 공식 문서 검증에서 새로 확인한 사실

### `.claude/teams/` 수동 파일 공식 미지원
`~/.claude/teams/{name}/config.json`은 자동 생성 전용이며, `.claude/teams/kas-team.md`처럼 수동으로 만든 파일은 **Claude Code가 인식하지 않음**. → Phase 2 폐기.

### Agent Teams 병렬 호출 실제 동작
- 독립 subagent (Agent tool): 한 메시지에 여러 개 → **물리적 병렬 실행** 가능
- Agent Teams teammate: 공유 task list를 통해 claim 방식 → lead 프롬프트에 따라 병렬/순차 제어
- `dispatching-parallel-agents` 스킬은 teammate가 아닌 **독립 subagent** 컨텍스트에서 동작. 혼합 사용 공식 미명시.

### `skills`, `mcpServers` teammate 모드에서 무시
teammate 실행 시 에이전트 정의 frontmatter의 `skills`, `mcpServers` 필드는 무시됨 — 세션 전역 설정에서만 로드. CLAUDE.md의 "Agent Team 한계 대응" 섹션에 기록됨.

---

## v5.1 변경 파일 목록

| 파일 | 종류 | 변경 내용 |
|---|---|---|
| `AGENTS.md` | 수정 | v5.1, 13개, 2026-04-12, L3 video-specialist 추가 |
| `.claude/agents/design-dev.md` | 수정 | `memory: project` 활성화 |
| `.claude/agents/db-architect.md` | 수정 | `memory: project` 활성화 + per-agent hooks 추가 |
| `.claude/agents/ops-monitor.md` | 수정 | `memory: project` 활성화 |
| `.claude/agents/pipeline-debugger.md` | 수정 | `memory: project` 활성화 + per-agent hooks 추가 |
| `.claude/agents/refactoring-surgeon.md` | 수정 | `memory: project` 활성화 + per-agent hooks 추가 |
| `.claude/agents/release-manager.md` | 수정 | per-agent hooks 추가 |
| `.claude/settings.local.json` | 수정 | WorktreeCreate `async: true`, SessionStart 훅 추가 |
| `scripts/mission_probe.py` | 신규 | SessionStart 훅 실행 스크립트 |
| `scripts/register_autonomous_task.ps1` | 신규 | Windows 작업 스케줄러 등록 스크립트 |
| `CLAUDE.md` | 수정 | SessionStart 자동 감지 항목 추가 |

---

## 현재 per-agent hooks 커버리지 (v5.1)

| 에이전트 | hooks | 차단 경로 |
|---|---|---|
| python-dev | ✅ | `/web/` 전체 |
| web-dev | ✅ | `/src/`, `globals.css` |
| design-dev | ✅ | `/src/`, `/tests/`, `/web/lib/`, `/web/hooks/` |
| ops-monitor | ✅ | `/src/step*`, `/web/app/`, `/web/components/` |
| db-architect | ✅ *(신규)* | `/src/step*`, `/web/app/`, `/web/components/` |
| refactoring-surgeon | ✅ *(신규)* | `/web/` 전체 |
| pipeline-debugger | ✅ *(신규)* | `/web/` 전체 |
| release-manager | ✅ *(신규)* | `/src/step*`, `/web/app/`, `/web/components/`, `step08/__init__.py` |
| quality-security | N/A | `disallowedTools: Write, Edit` |
| ux-a11y | N/A | `disallowedTools: Write, Edit` |
| performance-profiler | N/A | `disallowedTools: Write, Edit` |
| video-specialist | N/A | `disallowedTools: Write, Edit` |
| mission-controller | N/A | `disallowedTools: Write, Edit` |

**커버리지**: 8/8 Write-가능 에이전트 = **100%**

---

## memory 정책 (v5.1 확정)

| 구분 | 에이전트 | memory 설정 | 이유 |
|---|---|---|---|
| Builder | python-dev, web-dev, design-dev, db-architect, ops-monitor, refactoring-surgeon, pipeline-debugger | `memory: project` | 프로젝트별 패턴 학습 필요 |
| Release | release-manager | `memory: local` | 전역 릴리스 패턴 (프로젝트 무관) |
| Orchestrator | mission-controller | 주석 (수동 관례) | `~/.claude/agent-memory/` 수동 관례로 대체 |
| Read-only | quality-security, ux-a11y, performance-profiler, video-specialist | 주석 (수동 관례) | Write 권한 없음, 감사 패턴은 수동 기록 |

---

## 세션 외 자율 기동 활성화 방법

```powershell
# 1회만 실행 (관리자 권한 불필요)
.\scripts\register_autonomous_task.ps1

# 즉시 테스트
Start-ScheduledTask -TaskName "KAS-Mission-Controller"

# 등록 확인
Get-ScheduledTask -TaskName "KAS-Mission-Controller"
```

등록 후 매일 17:00에 `claude --print '/mission autorun'`이 자동 실행됩니다.
