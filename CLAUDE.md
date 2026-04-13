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
claude agents                                   # 37개 에이전트 목록 (v10.0)
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

## Loomix Agent Teams v10.0

**9부서 × 37명 + Meta 3명** (Opus 2 · Sonnet 22 · Haiku 13) | `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` 필요.
상세 조직도·파일 소유권·Anti-Patterns → **`AGENTS.md`** | 팀 구조·SSOT → `.claude/rules/agent-teams.md`

| 부서 | 인원 | 부서장 | 주요 역할 |
|------|:---:|--------|----------|
| Executive | 5 | ceo | HITL·전략·법률·AI리서치·정책준수 |
| Engineering | 6 | db-architect | src/+web/ 구현·DB·MLOps·미디어 |
| Platform Ops | 6 | devops-engineer | 인프라·SRE·릴리스·문서 |
| Quality | 4 | qa-auditor | 보안+성능+UX+런타임보안 감사 |
| Creative | 2 | content-director | 영상·SEO·수익 전략 |
| Sales&Delivery | 3 | sales-manager | 리드·계약·파트너십 |
| Growth&Brand | 4 | marketing-manager | 브랜드·CS·커뮤니티·모더레이션 |
| Finance Ops | 1 | finance-manager | 청구·P&L·API 비용 |
| Data Intelligence | 3 | data-analyst | BI·ETL·프롬프트 최적화 |
| Meta (virtual) | 3 | ceo/cto 공동 | eval·cost-router·debate |

핵심 규칙: TeamCreate(ceo·cto·qa-auditor만), Opus 2명 한도, color enum 8종, SSOT 교차쓰기 금지.
품질 게이트: `SubagentStop` → pytest·ruff·npm build 자동 실행.
v10.0 신규: Eval 프레임워크·Circuit Breaker·Cron 자율성·Peer-to-peer·COMPANY.md·Debate.
