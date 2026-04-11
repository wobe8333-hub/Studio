# KAS Agent Teams — 현실적 최고 수준 설계 (v2)

**날짜**: 2026-04-11 (v2 수정: 25개 문제점 반영)
**상태**: 구현 완료
**원칙**: 화려한 구성이 아니라 프로젝트 규모에 맞는 적정 복잡도

---

## 1. Context

KAS(Knowledge Animation Studio)는 7채널 YouTube 자동화 파이프라인. 현재 4개 독립 Sub-Agent가 파일 기반 간접 통신으로 동작한다.

**v1 설계(7명 코어팀 + 12 에이전트)에서 발견된 주요 문제:**
- 파일 소유권 겹침 (`src/step*/` vs `src/step05/`) → 충돌
- React 컴포넌트 "로직/스타일" 분리 비현실 → 동시 수정 충돌
- 7명 팀은 중소 규모 프로젝트에 과도 → 조정 비용 > 생산성
- Opus 3명 동시 실행 시 비용 폭주
- 4→12 에이전트 확장은 over-engineering
- `TeammateIdle` hook의 `type: prompt`에서 exit code 2 지시는 무의미

**v2 핵심 교정:**
1. 코어팀 7명 → **4명** (공식 권장 3~5명)
2. 파일 소유권: `src/` vs `web/` 디렉토리 경계로 완전 분리
3. 모델: 전원 **Sonnet** (Haiku 1명), Opus 제거
4. 런타임 에이전트: 4 → **6개** (점진적 확장)
5. hooks: TaskCompleted만 설정 (pytest 자동 실행)

---

## 2. 개발 시점 Agent Teams (코어 4명)

### 파일 구조
```
.claude/
  agents/
    backend-dev.md      — src/ 전체 (Sonnet, maxTurns=40)
    frontend-dev.md     — web/ 전체 (Sonnet, maxTurns=40, playwright+context7)
    quality-reviewer.md — Read-only + Bash (Sonnet, maxTurns=30, plan mode)
    infra-ops.md        — scripts/, 쿼터, 환경변수 (Haiku, maxTurns=25)
  settings.local.json   — CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1 + hooks
AGENTS.md               — 팀 운영 가이드, 미션 프리셋
```

### 팀원 구성

| 팀원 | 모델 | 소유 영역 | 금지 영역 | 특수 설정 |
|------|------|-----------|-----------|-----------|
| `backend-dev` | Sonnet | `src/` 전체 | `web/` | memory=project |
| `frontend-dev` | Sonnet | `web/` 전체 | `src/` | mcpServers: playwright, context7 |
| `quality-reviewer` | Sonnet | `tests/` (읽기만) | 모든 소스 수정 | disallowedTools: Write/Edit, permissionMode: plan |
| `infra-ops` | Haiku | `scripts/`, 쿼터 | `src/step*/`, `web/components/` | memory=user |

### 왜 이 구성이 최적인가

| 차원 | 선택 | 이유 |
|------|------|------|
| 팀 규모 4명 | src/와 web/이 완전 분리된 구조 → 자연스럽게 2개 도메인 + QA + 인프라 |
| Sonnet 선택 | Opus 대비 비용 5~15배 절약. 구현 작업은 Sonnet으로 충분 |
| quality-reviewer Read-only | 수정 권한 없이 리뷰만 → 파일 충돌 0%, CLAUDE.md 규칙 준수 검증에 집중 |
| infra-ops Haiku | 반복적 스크립트/쿼터 작업은 Haiku로 비용 효율적 처리 |
| maxTurns 설정 | 비용 폭주 방지. 초과 시 현재 상태를 리드에게 보고 |

### Hooks 설정

```json
"hooks": {
  "TaskCompleted": [{
    "matcher": "",
    "hooks": [{
      "type": "command",
      "command": "cd \"...\"> && python -m pytest tests/ -x -q --timeout=60 2>&1 | tail -10"
    }]
  }]
}
```

**TaskCompleted만 설정한 이유:**
- TeammateIdle의 `type: prompt`에서 exit code 2 지시는 동작하지 않음 (공식 문서 불일치)
- PostToolUse pytest는 Edit마다 테스트 실행 → 개발 속도 심각 저하
- TaskCompleted만으로도 충분한 품질 게이트 역할

### Persistent Memory

```
.claude/agent-memory/        ← project scope (git 추적)
  backend-dev/MEMORY.md      — 파이프라인 패턴, 에러 이력
  frontend-dev/MEMORY.md     — 컴포넌트 패턴, API 계약 이력
  quality-reviewer/MEMORY.md — 반복 이슈, 보안 패턴

~/.claude/agent-memory/      ← user scope
  infra-ops/MEMORY.md        — 인프라 설정 이력 (프로젝트 간 공유)
```

---

## 3. 미션별 소환 프리셋 (AGENTS.md에 정의)

| 미션 | 소환 팀원 | 총 인원 |
|------|-----------|---------|
| 풀스택 Feature 개발 | backend-dev + frontend-dev + quality-reviewer | 3명 |
| 3각 코드 리뷰 | quality-reviewer × 3 (보안/성능/테스트) | 3명 |
| 경쟁 가설 디버깅 | backend-dev 타입 × 3~5 | 3~5명 |
| 파이프라인 안정화 | backend-dev + quality-reviewer + infra-ops | 3명 |
| 대시보드 리디자인 | frontend-dev + quality-reviewer | 2명 |

**최대 인원: 7명 이내** (토큰 비용 × 팀 효율 균형)

---

## 4. 런타임 Sub-Agent 시스템 (4→6)

### 구현 완료 목록

| # | 에이전트 | 파일 | 상태 |
|---|---------|------|------|
| 1 | `DevMaintenanceAgent` | `src/agents/dev_maintenance/` | 기존 유지 |
| 2 | `AnalyticsLearningAgent` | `src/agents/analytics_learning/` | 기존 유지 |
| 3 | `UiUxAgent` | `src/agents/ui_ux/` | 기존 유지 |
| 4 | `VideoStyleAgent` | `src/agents/video_style/` | 기존 유지 |
| 5 | `ScriptQualityAgent` | `src/agents/script_quality/` | **신규 구현** |
| 6 | `CostOptimizerAgent` | `src/agents/cost_optimizer/` | **신규 구현** |

### ScriptQualityAgent (신규)
- **역할**: Step08 스크립트의 Hook/CTA/씬 구조/채널 톤 일관성 자동 평가
- **트리거**: 수동 실행 또는 Step08 완료 후
- **출력**: `data/global/agent_logs/script_quality_latest.json` (채널별 평균 점수)
- **웹 API**: `POST /api/agents/run { agent_id: "script_quality" }`

### CostOptimizerAgent (신규)
- **역할**: Gemini/YouTube 쿼터 사용 패턴 분석, 낭비 감지, HITL 에스컬레이션
- **트리거**: 수동 실행 또는 파이프라인 완료 후
- **출력**: `data/global/agent_logs/cost_optimizer_latest.json`
- **HITL**: 95% 쿼터 초과 시 `data/global/notifications/hitl_signals.json`에 자동 기록

### 왜 4→6만 확장했는가 (4→12 아닌 이유)
- 기존 4개 에이전트가 아직 초기 단계 (820줄 전체)
- ScriptQuality와 CostOptimizer는 현재 가장 명확한 필요성이 입증된 항목
- 나머지(TrendIntelligence, ChannelStrategy 등)는 실제 운영 데이터 확보 후 점진적 추가

---

## 5. 활성화 확인

```bash
# 1. Agent Teams 활성화 확인
claude agents
# 기대 출력: backend-dev, frontend-dev, quality-reviewer, infra-ops

# 2. 신규 에이전트 테스트
python -c "from src.agents.script_quality import ScriptQualityAgent; print(ScriptQualityAgent().run())"
python -c "from src.agents.cost_optimizer import CostOptimizerAgent; print(CostOptimizerAgent().run())"

# 3. 전체 테스트
python -m pytest tests/ -q
```

---

## 6. 참고 자료

- [Claude Code Agent Teams 공식 문서](https://code.claude.com/docs/en/agent-teams)
- [Claude Code Subagents 공식 문서](https://code.claude.com/docs/en/sub-agents)
- [30 Tips for Claude Code Agent Teams](https://getpushtoprod.substack.com/p/30-tips-for-claude-code-agent-teams)
