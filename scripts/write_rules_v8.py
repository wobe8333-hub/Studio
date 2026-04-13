#!/usr/bin/env python3
"""
v8.0 rules 파일 + playbooks 생성 스크립트.
.claude/rules/agent-teams.md, reflection.md, ssot-io.md
docs/playbooks/ 4개 시나리오 파일
실행: python scripts/write_rules_v8.py
"""
from __future__ import annotations

import io
import sys
from pathlib import Path

if hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT = Path(__file__).parent.parent
RULES_DIR = ROOT / ".claude" / "rules"
PLAYBOOKS_DIR = ROOT / "docs" / "playbooks"


FILES = {
    RULES_DIR / "agent-teams.md": """\
---
paths:
  - .claude/agents/**
  - AGENTS.md
---

# Agent Teams — 파일 소유권 + 팀 구조 (on-demand)

> 상세 조직도·미션 프리셋·Anti-Patterns → AGENTS.md 참고

## 파일 소유권 (v8.0)

| 에이전트 | 소유 경로 | 금지 경로 |
|----------|----------|----------|
| backend-engineer | src/, tests/, scripts/ (migrations 제외) | web/ |
| frontend-engineer | web/app/, web/lib/, web/hooks/, web/components/(로직) | src/, globals.css |
| ui-designer | web/app/globals.css, web/public/, assets/thumbnails/ | src/, tests/ |
| devops-engineer | .claude/, CLAUDE.md, AGENTS.md, docs/, .github/, scripts/ (migrations 제외) | src/step*, web/app/ |
| qa-auditor | Read-only 감사 전용 | Write, Edit 금지 |
| ux-auditor | Read-only 감사 전용 | Write, Edit 금지 |
| content-director | Read-only 영상 콘텐츠 감사 | Write, Edit 금지 |
| performance-analyst | Read-only 분석 전용 | Write, Edit 금지 |
| pipeline-debugger | Read-only 파이프라인 분석 | Write, Edit 금지 |
| revenue-strategist | Read-only 수익 전략 감사 | Write, Edit 금지 |
| legal-counsel | Read-only 법률 검토 · data/legal/ 단독 | Edit 금지 |
| cto | 조율 전용 | Write, Edit 금지 |
| ceo | 조율 전용 | Write, Edit 금지 |
| db-architect | scripts/supabase_schema.sql, scripts/migrations/, web/lib/types.ts | src/, web/app/ |
| code-refactorer | src/ 리팩토링 (worktree) | web/, tests/ 삭제, src/step08/__init__.py |
| release-manager | CHANGELOG.md (단독), git tag | src/step*, web/app/ |
| sales-manager | data/sales/ | src/, web/ |
| project-manager | data/pm/ | src/, web/ |
| marketing-manager | data/marketing/ | src/, web/ |
| customer-support | data/cs/ | src/, web/ |
| finance-manager | data/finance/ | src/, web/ |
| data-analyst | data/bi/ (단독) | src/, web/, data/global/ |
| prompt-engineer | src/step*/prompts.py, data/prompts/ | src/ 로직 코드, web/ |
| sre-engineer | data/sre/ (Read-only) | Write, Edit 금지 |
| mlops-engineer | data/mlops/, assets/lora/ (worktree) | data/global/, web/ |
| security-engineer | data/security/audit/ (Read-only) | Write, Edit 금지 |
| data-engineer | data/etl/, scripts/sync_to_supabase.py (worktree) | src/ 로직, web/ |
| community-manager | data/community/ (Read-only) | Write, Edit 금지 |
| research-lead | data/research/ (Read-only, plan mode) | Write, Edit 금지 |

## TeamCreate 권한

**TeamCreate 허가 3명만**: ceo · cto · qa-auditor

팀 유형:
- `kas-weekly-ops` — 상설팀 (월요일 생성, 일요일 종료)
- `client-{id}` / `incident-{날짜}` / `feature-{ticket}` — 동적 미션팀
- `weekly-audit-{날짜}` — 감사팀

최대 동시 활성: 5팀 (상설1 + 미션3 + 감사1)

## v8.0 신규 에이전트 배치

| 부서 | 신규 | 역할 |
|------|------|------|
| Executive | research-lead | AI 신기술 탐색·POC (read-only, plan) |
| Engineering | mlops-engineer | SD XL/LoRA/ElevenLabs 모델 운영 (worktree) |
| Platform Ops | sre-engineer | Sentry 알람·런타임 대응 (read-only) |
| Quality | security-engineer | OAuth 회전·RLS 런타임 보안 (read-only) |
| Growth&Brand | community-manager | 7채널 시청자 커뮤니티 (read-only) |
| Data Intelligence | data-engineer | Step05 ETL·Supabase idempotency (worktree) |
""",

    RULES_DIR / "reflection.md": """\
---
paths:
  - .claude/agents/**
---

# Reflection 패턴 — 세션 간 교훈 누적 (공통)

> 모든 에이전트의 Reflection 지침. 개별 에이전트 파일에서 중복 선언하지 않는다.

## 기본 원칙

Reflection은 **선택이 아닌 의무**다. 미션 종료 후 반드시 기록한다.

## 저장 위치

```
~/.claude/agent-memory/{agent-name}/MEMORY.md
```

## 기록 항목

1. **성공 패턴**: 무엇이 효과적이었는가? (재사용 가능한 접근법)
2. **실패 패턴**: 무엇이 시간 낭비였는가? (반복 금지 실수)
3. **의존성 교훈**: 다른 에이전트와 협업 시 발견한 인터페이스 주의사항
4. **다음 세션 컨텍스트**: 다음에 같은 미션을 받으면 먼저 확인해야 할 것

## 포맷

```markdown
# MEMORY.md — {에이전트명}

## {날짜} 세션 교훈
- **성공**: ...
- **실패**: ...
- **다음 확인**: ...
```

## PreCompact 훅 자동 저장

컨텍스트 압축 직전 `PreCompact` 훅이 `data/global/learning_feedback.json`에
세션 ID와 타임스탬프를 자동 기록한다. 핵심 교훈은 에이전트가 직접 MEMORY.md에 작성해야 한다.

## cto/ceo 특별 지침

`initialPrompt`에서 `data/global/notifications/hitl_signals.json`과
`data/exec/team_lifecycle.json`을 먼저 확인한 후 Reflection 기록.
""",

    RULES_DIR / "ssot-io.md": """\
---
paths:
  - src/**/*.py
  - data/**
---

# SSOT I/O 규칙 + 데이터 디렉토리 (on-demand)

## SSOT I/O 원칙

모든 JSON 읽기/쓰기는 **반드시** `src/core/ssot.py` 사용:

```python
from src.core.ssot import read_json, write_json

data = read_json(path)        # encoding="utf-8-sig" (BOM 처리)
write_json(path, data)        # filelock + atomic write + ensure_ascii=True
```

- `write_json()`: `filelock` + **atomic write** (tempfile → `os.replace`) + `ensure_ascii=True`
- `read_json()`: `encoding="utf-8-sig"` (BOM 처리)
- 직접 `open()` 금지 — PowerShell 5.1 cp949 환경에서 깨짐

## 데이터 디렉토리 전체 목록

```
data/global/                        — 채널 레지스트리, 쿼터 정책
data/global/notifications/          — hitl_signals.json, notifications.json
data/global/step_progress.json      — 파이프라인 실시간 상태 (웹 3초 폴링)
data/global/audits/                 — qa-auditor 주간 감사 리포트
data/global/learning_feedback.json  — PreCompact 훅 세션 교훈 누적
data/global/session_history.json    — SessionEnd 훅 비용 집계
data/channels/CH*/                  — 채널별 algorithm/revenue/style 정책
data/knowledge_store/               — KnowledgePackage JSON
data/exec/                          — ceo 의사결정 로그, 팀 생명주기
data/sales/                         — 리드·제안서 (sales-manager)
data/pm/                            — 수주 프로젝트 (project-manager)
data/creative/                      — content-director 콘텐츠 리뷰
data/marketing/                     — 마케팅 캠페인 (marketing-manager)
data/cs/                            — 고객 문의 (customer-support)
data/finance/                       — 청구서·P&L (finance-manager)
data/legal/                         — 계약서·NDA (legal-counsel)
data/bi/                            — BI 대시보드 (data-analyst)
data/prompts/                       — 프롬프트 버전 (prompt-engineer)
data/sre/                           — SLO·런북 (sre-engineer) [v8.0]
data/mlops/                         — 모델 이력 (mlops-engineer) [v8.0]
data/security/audit/                — 보안 감사 (security-engineer) [v8.0]
data/etl/                           — ETL 스케줄 (data-engineer) [v8.0]
data/community/                     — 시청자 피드백 (community-manager) [v8.0]
data/research/                      — AI 기술 레이더 (research-lead) [v8.0]
runs/CH*/run_*/                     — 실행 결과물 (manifest.json, step08/ 등)
runs/CH*/test_run_*/                — DRY RUN 결과물 (dry_run: true)
logs/                               — pipeline.log (loguru, 50MB rotation)
```

## SSOT 교차 쓰기 금지

| SSOT 경로 | 단독 소유 에이전트 |
|-----------|---------------|
| data/exec/ | ceo |
| data/sales/ | sales-manager |
| data/pm/ | project-manager |
| data/creative/ | content-director |
| data/marketing/ | marketing-manager |
| data/cs/ | customer-support |
| data/finance/ | finance-manager |
| data/legal/ | legal-counsel |
| data/bi/ | data-analyst |
| data/prompts/ | prompt-engineer |
| data/sre/ | sre-engineer (read-only 에이전트, Bash로만) |
| data/mlops/ | mlops-engineer |
| data/security/audit/ | security-engineer (read-only) |
| data/etl/ | data-engineer |
| data/community/ | community-manager (read-only) |
| data/research/ | research-lead (read-only) |
""",
}

PLAYBOOKS = {
    PLAYBOOKS_DIR / "pipeline-incident.md": """\
# 플레이북: 파이프라인 장애 대응 (Step08 FFmpeg 실패)

## 트리거
Step08 FFmpeg 오류, manifest.json status: "failed", 연속 3회 실패

## 대응 절차

```
/mission "Step08 FFmpeg 에러 조사"
-> cto: TeamCreate("incident-{날짜}-step08")
  1) pipeline-debugger: 로그·manifest·쿼터 분석 (read-only)
  2) backend-engineer: 수정 구현 (src/step08/ffmpeg_composer.py)
-> pipeline-debugger -> SendMessage -> backend-engineer에 근본 원인 전달
-> 수정 -> pytest -> TeamDelete
```

## SRE 에스컬레이션 (v8.0)

연속 3회 실패 시 `sre-engineer`가 `hitl_signals.json`에 `sre_escalation` 신호 삽입.
cto가 HITL 신호 확인 후 TeamCreate 실행.

## 완료 기준
- `pytest tests/ -q` PASS
- manifest.json status: "completed"
- HITL 신호 resolved: true
""",

    PLAYBOOKS_DIR / "client-project.md": """\
# 플레이북: 외주 클라이언트 프로젝트 (법률 포함)

## 트리거
리드 → 수주 확정, 계약서 수신

## 대응 절차

```
sales-manager -> 리드 기록 -> 제안서 작성
-> legal-counsel: 계약서 검토 -> (고위험 없음) -> ceo 보고
-> ceo HITL 게이트 (>=100만원) -> 사용자 승인
-> ceo: TeamCreate("client-{id}")
  + project-manager, content-director, backend-engineer,
    ui-designer, qa-auditor, customer-support, finance-manager
-> 공유 TaskList (스펙->렌더->QA->전달->청구)
-> 팀원 자율 claim -> 완료 -> TeamDelete
```

## 법률 검토 HITL 트리거
- 고위험 조항(위약금 >500만원, 독점 조항, 준거법 해외) 발견 시 legal-counsel이 ceo에게 HITL 신호

## 완료 기준
- data/pm/projects/{id}.json status: "delivered"
- data/finance/invoices.json에 청구서 발행 확인
""",

    PLAYBOOKS_DIR / "schema-change.md": """\
# 플레이북: Supabase 스키마 변경

## 트리거
새 컬럼/테이블 추가, 타입 변경, RLS 정책 수정

## 대응 절차

```
/mission "trend_topics에 is_approved_by 컬럼 추가"
-> cto spawn:
  1) db-architect: SQL 마이그레이션 + RLS (Opus, worktree)
  2) backend-engineer: src/agents/ui_ux/ 동기화 로직 (worktree)
  3) frontend-engineer: web/lib/types.ts 재생성 (worktree)
-> db-architect가 나머지 2명에 API 변경 알림 -> 병렬 구현 -> 통합
```

## 안전 규칙
- 파괴적 변경(DROP, 타입 축소) 시 백필 스크립트 필수
- security-engineer가 RLS 런타임 검증 (완료 후)
- db-architect 없이 스키마 변경 금지

## 완료 기준
- scripts/migrations/ 파일 존재
- web/lib/types.ts 동기화 완료
- pytest PASS, npm build PASS
""",

    PLAYBOOKS_DIR / "bi-report.md": """\
# 플레이북: 월간 BI 보고 (data-analyst 주간 자동)

## 트리거
주간 자동 실행 또는 `/bi-report` 슬래시 커맨드

## 대응 절차

```
data-analyst (주간 or /bi-report 커맨드)
-> scripts/generate_bi_dashboard.py 실행
-> data/bi/weekly_dashboard.json 생성
-> SendMessage(revenue-strategist) — winning pattern 대조
-> SendMessage(ceo) — 월간 경영 보고 입력
```

## 확인 지표
- channel_kpi: 7채널 업로드 수·조회수·평균 조회
- cost_summary: gemini_api_usd, total_usd
- sales_funnel: 리드→수주 전환율
- key_insights: HITL 임계값 초과 여부

## 완료 기준
- data/bi/weekly_dashboard.json 갱신
- ceo SendMessage 완료
- API 비용 >$50 시 HITL 신호 자동 생성
""",
}


def main() -> None:
    print("[v8.0 rules + playbooks 생성 시작]")

    # rules 파일 생성
    RULES_DIR.mkdir(parents=True, exist_ok=True)
    for path, content in FILES.items():
        path.write_text(content, encoding="utf-8")
        print(f"  [OK] {path.relative_to(ROOT)} ({len(content.splitlines())}줄)")

    # playbooks 생성
    PLAYBOOKS_DIR.mkdir(parents=True, exist_ok=True)
    for path, content in PLAYBOOKS.items():
        path.write_text(content, encoding="utf-8")
        print(f"  [OK] {path.relative_to(ROOT)} ({len(content.splitlines())}줄)")

    print(f"\n[OK] 총 {len(FILES)}개 rules + {len(PLAYBOOKS)}개 playbook 생성 완료")


if __name__ == "__main__":
    main()
