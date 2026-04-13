#!/usr/bin/env python3
"""
v8.0 CLAUDE.md + AGENTS.md 재작성 스크립트.
CLAUDE.md: 197 -> ~80줄 (-59%)
AGENTS.md: 352 -> ~200줄 (-43%)
실행: python scripts/write_main_docs_v8.py
"""
from __future__ import annotations

import io
import sys
from pathlib import Path

if hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT = Path(__file__).parent.parent

CLAUDE_MD = """\
# CLAUDE.md

@AGENTS.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

---

## 프로젝트 개요

**Loomix** (AI 콘텐츠 에이전시 · 내부 코드명: KAS) — AI 7채널 YouTube 풀 자동화. 채널당 월 200만원, 총 1,400만원/월 수익 목표.
GitHub: `https://github.com/wobe8333-hub/Studio`
7채널: CH1(경제) / CH2(부동산) / CH3(심리) / CH4(미스터리) / CH5(전쟁사) / CH6(과학) / CH7(역사)

## 주요 명령어

```bash
python -m src.pipeline 1                         # 월간 파이프라인 (1~12)
pytest tests/ -q                                 # 전체 테스트
python scripts/preflight_check.py               # 환경 점검
python scripts/generate_oauth_token.py --channel CH1  # OAuth 최초 발급
python scripts/sync_to_supabase.py              # Supabase 동기화
ruff check src/ --fix --select=E,W,F,I          # Python 린팅 자동 수정
cd web && npm run build                          # 프론트엔드 빌드
ngrok start kas-studio                          # 외부 공개 (cwstudio.ngrok.app)
claude agents                                   # 29개 에이전트 목록
```

## SSOT 원칙

모든 JSON I/O: `src/core/ssot.py`의 `read_json()` / `write_json()` 사용 **필수**.
> 데이터 디렉토리 전체 목록 + SSOT 규칙 → `.claude/rules/ssot-io.md`

## 핵심 규칙

- **로깅**: `import logging` 금지. `from loguru import logger` 사용.
- **JSON I/O**: 직접 `open()` 금지. `ssot.read_json()` / `ssot.write_json()` 사용.
- **채널 설정 SSOT**: 채널 수/카테고리/RPM/목표값은 `src/core/config.py` 단일 출처.
- **KPI 수집 지연**: Step12 업로드 후 48시간 pending 메커니즘.
- **Sub-Agent 비침습**: `src/agents/` 코드는 Step00~17 로직 변경 금지.
- **Sub-Agent BaseAgent**: `if root is not None:` 사용 (Path는 항상 truthy).
- **대용량 파일 쓰기**: 한국어 ≥300줄 파일은 Python 스크립트로 작성. `wc -l`로 검증.
- **settings.local.json**: Write/Edit 전 반드시 Read 먼저 실행 (훅 트리거 주의).
- **Windows 인코딩**: `sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")`.
- **CronCreate**: Windows에서 세션 한정 → 작업 스케줄러 사용.
- **`assets/` 디렉토리**: `characters/`, `lora/`, `thumbnails/` — 런타임 읽기 전용.
> 웹 규칙: `.claude/rules/web.md` | 영상·Step: `.claude/rules/steps.md`

## 환경 변수

**백엔드 `.env`** (`.env.example` 참고):
`GEMINI_API_KEY`, `YOUTUBE_API_KEY`, `CH1~7_CHANNEL_ID`, `KAS_ROOT`(필수),
`ELEVENLABS_API_KEY`, `CH1~7_VOICE_ID`, `GEMINI_TEXT_MODEL`(gemini-2.5-flash),
`GEMINI_IMAGE_MODEL`, `MANIM_QUALITY`(l/h), `SENTRY_DSN`, `TAVILY_API_KEY`, `SERPAPI_KEY`

**웹 `web/.env.local`** (`.env.local.example` 참고):
`NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY`,
`SUPABASE_SERVICE_ROLE_KEY`(서버 전용), `DASHBOARD_PASSWORD`, `PYTHON_EXECUTABLE`

## Loomix Agent Teams v8.0

**9부서 × 29명** (Opus 2 · Sonnet 18 · Haiku 9) | `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` 필요.
상세 조직도·파일 소유권·Anti-Patterns → **`AGENTS.md`** | 팀 구조·SSOT → `.claude/rules/agent-teams.md`

| 부서 | 인원 | 부서장 | 주요 역할 |
|------|:---:|--------|----------|
| Executive | 4 | ceo | HITL·전략·법률·AI리서치 |
| Engineering | 5 | db-architect | src/+web/ 구현·DB·MLOps |
| Platform Ops | 5 | devops-engineer | 인프라·SRE·릴리스 |
| Quality | 4 | qa-auditor | 보안+성능+UX+런타임보안 감사 |
| Creative | 2 | content-director | 영상·SEO·수익 전략 |
| Sales&Delivery | 2 | sales-manager | 리드·계약·프로젝트 |
| Growth&Brand | 3 | marketing-manager | 브랜드·CS·커뮤니티 |
| Finance Ops | 1 | finance-manager | 청구·P&L·API 비용 |
| Data Intelligence | 3 | data-analyst | BI·ETL·프롬프트 최적화 |

핵심 규칙: TeamCreate(ceo·cto·qa-auditor만), Opus 2명 한도, color enum 8종, SSOT 교차쓰기 금지.
품질 게이트: `SubagentStop` → pytest·ruff·npm build 자동 실행.
"""

AGENTS_MD = """\
# Loomix Agent Teams v8.0 운영 가이드

> **브랜드**: Loomix (AI 콘텐츠 에이전시) · **내부 코드명**: KAS
> **버전**: v8.0 | **에이전트 수**: 29개 | **기준일**: 2026-04-13
> **공식 Claude Code 문서 준수**: 98%+ (v8.0 재감사 기반)

---

## 조직도 — 9 부서 × 29명

```
                             ceo (Sonnet) — Executive 부서장
                                 |
   +------+--------+---------+--+----+--------+--------+--------+--------+
   v      v        v         v       v        v        v        v        v
Exec   Eng      Ops      QA   Creat   Sales  Growth   Fin     Data
(4명)  (5명)    (5명)    (4명) (2명)   (2명)  (3명)    (1명)   (3명)

ceo    db-arch  devops   qa-aud  content  sales   marketing  finance  data-anal
cto    backend  sre      perf-a  revenue  project customer            data-eng
legal  frontend code-ref ux-aud          community          prompt-e
res-l  ui-des   pipeline security
       mlops    release
```

**모델 분포**: Opus 2 (cto, db-architect) · Sonnet 18 · Haiku 9
**부서장 9명**: ceo · db-architect · devops-engineer · qa-auditor · content-director · sales-manager · marketing-manager · finance-manager · data-analyst

---

## 부서별 정의

### Executive Office — 4명
| 에이전트 | 모델 | 역할 |
|---|:-:|---|
| **ceo** | Sonnet | **부서장** · HITL 판단 · 비즈니스 미션팀 결성 · 월간 경영 보고 |
| **cto** | Opus | 기술 조율 · 기술 미션팀 결성 · ultrathink 적용 |
| **legal-counsel** | Haiku | 계약서·NDA·저작권·YouTube 정책 검토 (read-only) |
| **research-lead** | Sonnet | AI 신기술 탐색·POC·cto 보고 (read-only, plan) |

### Engineering Division — 5명
| 에이전트 | 모델 | 역할 |
|---|:-:|---|
| **db-architect** | Opus | **부서장** · DB 스키마 · RLS · types.ts (ultrathink) |
| **backend-engineer** | Sonnet | src/ 전체 · 파이프라인 · 테스트 |
| **frontend-engineer** | Sonnet | web/ 전체 · Next.js · E2E |
| **ui-designer** | Sonnet | globals.css · 디자인 시스템 · 썸네일 |
| **mlops-engineer** | Sonnet | SD XL/LoRA/ElevenLabs/Whisper 모델 운영 (worktree) |

### Platform Operations — 5명
| 에이전트 | 모델 | 역할 |
|---|:-:|---|
| **devops-engineer** | Sonnet | **부서장** · 인프라 · 문서 · hooks |
| **sre-engineer** | Sonnet | Sentry 알람·SLO·런타임 대응 (read-only) |
| **code-refactorer** | Sonnet | God Module 분해 (worktree) |
| **pipeline-debugger** | Sonnet | Step 실패 원인 분석 (read-only) |
| **release-manager** | Haiku | CHANGELOG · git tag · PR |

### Quality Assurance — 4명
| 에이전트 | 모델 | 역할 |
|---|:-:|---|
| **qa-auditor** | Sonnet | **부서장** · OWASP 감사 · 감사팀 결성 (ultrathink) |
| **performance-analyst** | Haiku | N+1·메모리·번들 분석 (read-only) |
| **ux-auditor** | Haiku | WCAG 2.1 AA · UX 감사 (read-only) |
| **security-engineer** | Sonnet | OAuth 회전·RLS 런타임 보안 (read-only) |

### Creative Studio — 2명
| 에이전트 | 모델 | 역할 |
|---|:-:|---|
| **content-director** | Sonnet | **부서장** · 스크립트·썸네일·SEO 감사 (read-only) |
| **revenue-strategist** | Sonnet | 수익 주제 선별 · scorer · 포트폴리오 (read-only) |

### Sales & Delivery — 2명
| 에이전트 | 모델 | 역할 |
|---|:-:|---|
| **sales-manager** | Sonnet | **부서장** · 리드·제안서·계약 |
| **project-manager** | Haiku | 수주 프로젝트 딜리버리 |

### Growth & Brand — 3명
| 에이전트 | 모델 | 역할 |
|---|:-:|---|
| **marketing-manager** | Sonnet | **부서장** · 브랜드 성장 · 인바운드 마케팅 |
| **customer-support** | Haiku | 외주 클라이언트 B2B CS |
| **community-manager** | Haiku | 7채널 시청자 커뮤니티 (read-only) |

### Finance Operations — 1명
| 에이전트 | 모델 | 역할 |
|---|:-:|---|
| **finance-manager** | Haiku | **부서장** · 청구서 · P&L · API 비용 (BUDGET_LIMIT_USD=$50) |

### Data Intelligence — 3명
| 에이전트 | 모델 | 역할 |
|---|:-:|---|
| **data-analyst** | Haiku | **부서장** · Supabase BI · 주간 대시보드 |
| **data-engineer** | Sonnet | Step05 ETL·Supabase idempotency (worktree) |
| **prompt-engineer** | Sonnet | Gemini/ElevenLabs 프롬프트 A/B · 토큰 절감 |

> 파일 소유권 상세 → `.claude/rules/agent-teams.md`

---

## 부서간 협업 — TeamCreate

**권한 3명만**: ceo · cto · qa-auditor

```
TeamCreate(team_name="{유형}-{id}") → Agent() × N명
→ TaskCreate 공유 태스크 → pull 방식 claim
→ SendMessage 실시간 조율 → TeamDelete
→ data/exec/team_lifecycle.json 기록
```

실전 시나리오 → `docs/playbooks/` 참고

---

## 미션 프리셋

| 미션 유형 | 소환 조합 |
|-----------|-----------|
| 백엔드 기능/버그 | backend-engineer + qa-auditor |
| 프론트엔드 기능 | frontend-engineer + qa-auditor |
| UI/디자인 변경 | ui-designer + ux-auditor |
| 보안 취약점 수정 | qa-auditor + security-engineer → backend-engineer |
| 성능 최적화 | performance-analyst + backend-engineer |
| DB 스키마 변경 | db-architect + backend-engineer + frontend-engineer |
| 파이프라인 장애 | sre-engineer + pipeline-debugger + backend-engineer |
| MLOps 드리프트 | mlops-engineer (content-director 신호 수신 후) |
| 대규모 리팩토링 | code-refactorer + backend-engineer |
| 릴리스 배포 | release-manager + backend-engineer |
| UX/접근성 감사 | ux-auditor → frontend-engineer/ui-designer |
| 영상 콘텐츠 감사 | content-director → backend-engineer/ui-designer |
| 수익 전략 감사 | revenue-strategist + pipeline-debugger → backend-engineer |
| 수주 프로젝트 | ceo: TeamCreate + sales-manager + project-manager + 제작팀 |
| 법률 검토 | sales-manager → legal-counsel → (고위험) ceo HITL |
| BI 대시보드 | data-analyst + data-engineer (주간 자동) |
| 프롬프트 최적화 | prompt-engineer + backend-engineer |
| 시청자 피드백 | community-manager → content-director 루프백 |
| AI 신기술 탐색 | research-lead → mlops-engineer (POC 후 위임) |

---

## 통신 프로토콜

**ceo/cto → 팀 결성**:
```
TeamCreate(team_name="{유형}-{id}")
Agent(team_name=..., name="{역할}", subagent_type="{에이전트명}")
TaskCreate(subject="{작업}")
```

**Guardian → Builder (이슈 전달)**:
```
[이슈 유형: 보안/품질/UX/수익/법률]
파일: {경로:줄번호} | 심각도: CRITICAL/HIGH/MEDIUM/LOW
설명: {문제와 영향} | 수정 담당: {에이전트명}
```

---

## Anti-Patterns

### 기본 (v5.2)
- **backend-engineer가 web/ 수정** — PreToolUse hook 차단
- **qa-auditor 코드 직접 수정** — disallowedTools 차단
- **Opus 동시 2명 초과** — cto+db-architect 동시 시 cto 먼저 종료
- **CHANGELOG.md를 release-manager 외 편집** — 이력 충돌
- **db-architect 없이 스키마 변경** — RLS/types.ts 누락

### TeamCreate (v6.0)
- **TeamCreate 권한 3명 제한** (ceo·cto·qa-auditor)
- **고아 팀 금지** — 미션 종료 시 TeamDelete 필수
- **동시 팀 5개 초과 금지**
- **부서 SSOT 교차 쓰기 금지**

### v8.0 신규
- **비표준 hook 이벤트 재도입 금지** — TaskCompleted 등 공식 미지원 이벤트
- **frontmatter memory/permissionMode 누락 금지** — Reflection 손실
- **read-only 에이전트 Write 권한** — disallowedTools에 Write, Edit 반드시 함께
- **Extended thinking 오남용 금지** — 고위험 결정에만 (ultrathink)
- **sre-engineer↔pipeline-debugger 동시 소환 금지** — cto가 1개 선택
- **mlops↔prompt-engineer 혼용 금지** — mlops=가중치, prompt=텍스트
- **security-engineer↔qa-auditor 중첩 금지** — qa=정적, security=런타임
- **community-manager↔customer-support 경로 혼용 금지** — data/community/ vs data/cs/
- **research-lead 직접 채택 금지** — 보고만, 채택은 cto/ceo

---

## 진단 에이전트 경계 (4축)

- **pipeline-debugger**: Step 실패 "원인" (로그·manifest·quota)
- **performance-analyst**: 성공 런 "최적화" (N+1·메모리·번들)
- **revenue-strategist**: 주제 선별 "수익성" (scorer·portfolio)
- **data-analyst**: BI "현황" (채널 코호트·펀널·A/B)
동일 이슈 둘 이상 소환 금지 — cto가 1개 선택.

---

> 커맨드·슬래시 커맨드 → `CLAUDE.md` 참고
"""


def main() -> None:
    print("[v8.0 CLAUDE.md + AGENTS.md 재작성 시작]")

    claude_path = ROOT / "CLAUDE.md"
    claude_path.write_text(CLAUDE_MD, encoding="utf-8")
    lines = len(CLAUDE_MD.splitlines())
    print(f"  [OK] CLAUDE.md ({lines}줄, 197줄 -> {lines}줄)")

    agents_path = ROOT / "AGENTS.md"
    agents_path.write_text(AGENTS_MD, encoding="utf-8")
    lines2 = len(AGENTS_MD.splitlines())
    print(f"  [OK] AGENTS.md ({lines2}줄, 352줄 -> {lines2}줄)")

    total = lines + lines2
    print(f"\n[OK] 합산 {total}줄 (기존 549줄 -> {total}줄, -{round((549-total)/549*100)}% 절감)")


if __name__ == "__main__":
    main()
