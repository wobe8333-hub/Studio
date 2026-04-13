# Loomix Agent Teams v10.0 운영 가이드

> **브랜드**: Loomix (AI 콘텐츠 에이전시) · **내부 코드명**: KAS
> **버전**: v10.0 | **에이전트 수**: 37개 (+ Meta 3) | **기준일**: 2026-04-13
> **공식 Claude Code 문서 준수**: 100% (v10.0 재감사 기반)

---

## 조직도 — 9 부서 × 34명 + Meta 3명

```
                    ceo (Sonnet) — Executive 부서장
                        |
    +------+--------+-------+-----+-------+--------+--------+------+------+
    v      v        v       v     v       v        v        v      v
  Exec    Eng     Ops    QA   Creat  Sales  Growth   Fin   Data   Meta
  (5명)  (6명)   (6명)  (4명)  (2명)  (3명)  (4명)   (1명)  (3명)  (3명)

  ceo    db-arch  devops  qa-aud  content  sales   marketing  finance  data-anal  eval
  cto    backend  sre     perf-a  revenue  project customer            data-eng   router
  legal  frontend code-r  ux-aud           partner community           prompt-e  debate
  res-l  ui-des   pipel   security          moderator
 complian mlops   release
         media   doc-wri
```

**모델 분포**: Opus 2 (cto, db-architect) · Sonnet 22 · Haiku 13
**부서장 9명**: ceo · db-architect · devops-engineer · qa-auditor · content-director · sales-manager · marketing-manager · finance-manager · data-analyst

---

## 부서별 정의

### Executive Office — 5명
| 에이전트 | 모델 | 역할 |
|---|:-:|---|
| **ceo** | Sonnet | **부서장** · HITL 판단 · Debate 최종 결정 · 월간 경영보고 |
| **cto** | Opus | 기술 조율 · 에이전트 라이프사이클 관리 · ultrathink |
| **legal-counsel** | Haiku | 계약서·NDA·저작권 검토 (read-only) |
| **research-lead** | Sonnet | AI 신기술 탐색·POC (read-only, plan) |
| **compliance-officer** | Sonnet | YouTube 정책·GDPR·Content ID (read-only, ultrathink) |

### Engineering Division — 6명
| 에이전트 | 모델 | 역할 |
|---|:-:|---|
| **db-architect** | Opus | **부서장** · DB 스키마 · RLS · types.ts (ultrathink) |
| **backend-engineer** | Sonnet | src/ · 파이프라인 · 테스트 (worktree) |
| **frontend-engineer** | Sonnet | web/ · Next.js · E2E |
| **ui-designer** | Sonnet | globals.css · 디자인 시스템 · 썸네일 |
| **mlops-engineer** | Sonnet | SD XL/LoRA/ElevenLabs/Whisper (worktree, DRIFT_THRESHOLD) |
| **media-engineer** | Sonnet | FFmpeg CRF/preset · EBU R128 오디오 · HLS |

### Platform Operations — 6명
| 에이전트 | 모델 | 역할 |
|---|:-:|---|
| **devops-engineer** | Sonnet | **부서장** · 인프라 · hooks · CLAUDE.md |
| **sre-engineer** | Sonnet | Sentry 알람 · SLO · 런타임 대응 (read-only) |
| **code-refactorer** | Sonnet | God Module 분해 (worktree) |
| **pipeline-debugger** | Sonnet | Step 실패 원인 분석 (read-only) |
| **release-manager** | Haiku | CHANGELOG · git tag · PR |
| **documentation-writer** | Haiku | docs/ ADR·API·온보딩 (docs/ 단독) |

### Quality Assurance — 4명
| 에이전트 | 모델 | 역할 |
|---|:-:|---|
| **qa-auditor** | Sonnet | **부서장** · OWASP 감사 · 감사팀 결성 (ultrathink) |
| **performance-analyst** | Haiku | N+1·메모리·번들 분석 (read-only) |
| **ux-auditor** | Haiku | WCAG 2.1 AA · UX 감사 (read-only) |
| **security-engineer** | Sonnet | OAuth·RLS 런타임 (read-only, ultrathink) |

### Creative Studio — 2명
| 에이전트 | 모델 | 역할 |
|---|:-:|---|
| **content-director** | Sonnet | **부서장** · 스크립트·썸네일·SEO (read-only) |
| **revenue-strategist** | Sonnet | 수익 주제 선별 · scorer · 포트폴리오 (read-only) |

### Sales & Delivery — 3명
| 에이전트 | 모델 | 역할 |
|---|:-:|---|
| **sales-manager** | Sonnet | **부서장** · 리드·제안서·계약 |
| **project-manager** | Haiku | 수주 프로젝트 딜리버리 |
| **partnerships-manager** | Sonnet | 브랜드 콜라보·스폰서십 |

### Growth & Brand — 4명
| 에이전트 | 모델 | 역할 |
|---|:-:|---|
| **marketing-manager** | Sonnet | **부서장** · 브랜드 성장 · 인바운드 마케팅 |
| **customer-support** | Haiku | 외주 클라이언트 B2B CS |
| **community-manager** | Haiku | 7채널 시청자 소통 (read-only) |
| **content-moderator** | Haiku | 댓글 악플·위기 대응 (read-only) |

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

### Meta (부서 소속 없음 — ceo/cto 공동 관리) — 3명
| 에이전트 | 모델 | 역할 | 트리거 |
|---|:-:|---|---|
| **agent-evaluator** | Sonnet | Golden test 채점 · LLM-as-judge · eval regression | SubagentStop 자동 |
| **cost-router** | Haiku | 과업 복잡도 → 모델 선택 (Haiku/Sonnet/Opus) | 미션 시작 시 |
| **debate-facilitator** | Sonnet | 3명 병렬 의견 → Constitutional synthesis | ceo HITL 이전 |

> 파일 소유권 상세 → `.claude/rules/agent-teams.md` | 미션 프리셋 + 통신 → `.claude/rules/team-protocol.md`

---

## 부서간 협업 — TeamCreate

**권한 3명만**: ceo · cto · qa-auditor | 최대 동시 활성: 5팀

실전 시나리오 → `docs/playbooks/` | 상세 흐름 → `.claude/rules/team-protocol.md`

---

## Anti-Patterns

### 기본
- **backend-engineer가 web/ 수정** — PreToolUse hook 차단
- **qa-auditor 코드 직접 수정** — disallowedTools 차단
- **Opus 동시 2명 초과** — cto+db-architect 동시 시 cto 먼저 종료
- **db-architect 없이 스키마 변경** — RLS/types.ts 누락

### TeamCreate
- TeamCreate 권한 3명 제한 · 고아 팀 금지(TeamDelete 필수) · 동시 5개 초과 금지 · SSOT 교차쓰기 금지

### v8.0
- 비표준 hook 이벤트 재도입 금지 · frontmatter memory/permissionMode 누락 금지
- read-only 에이전트 disallowedTools: Write, Edit 필수 · ultrathink 고위험 결정에만

### v10.0 신규
- **Meta-agent 자체 TeamCreate 금지** — agent-evaluator/cost-router/debate-facilitator는 ceo/cto만 호출
- **Eval 없는 에이전트 .md 변경 금지** — CI gate 차단
- **Shadow 14일 단축 금지** — ceo HITL 예외 승인 시 eval 소급 필수
- **Debate 스킵 금지** — HITL 9종 중 계약서·수주·정책 이슈는 필수
- **Circuit breaker 우회 금지** — 2인 승인(ceo + finance-manager) 필요
- **Cron job ceo/cto 실행 금지** — 자율성은 중간 관리자에게
- **compliance↔legal, moderator↔community, media↔backend 경계 혼용 금지**

---

## 진단 에이전트 경계 (4축)

- **pipeline-debugger**: Step 실패 "원인" | **performance-analyst**: "최적화"
- **revenue-strategist**: "수익성" | **data-analyst**: BI "현황"

동일 이슈 둘 이상 소환 금지 — cto가 1개 선택.

---

> 커맨드 → `CLAUDE.md` | 미션 프리셋·통신 프로토콜 → `.claude/rules/team-protocol.md`
