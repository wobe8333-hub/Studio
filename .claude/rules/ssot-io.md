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
