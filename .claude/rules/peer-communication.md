---
paths:
  - .claude/agents/**
---

# Peer Communication — 직접 소통 원칙 (Peer-to-peer First)

> v10.0 자율성 향상: 부서장 경유 -40% 목표. 실행·운영 레벨은 peer-to-peer 우선.

## 핵심 원칙

**같은 부서 내**: 항상 직접 SendMessage. 부서장 경유 불필요.
**부서 간 운영·실행 레벨**: 직접 SendMessage 허용. 결정권 없는 협업.
**부서 간 중요 결정**: 부서장 경유 or RACI A 확인 (COMPANY.md 참조).
**고위험 결정 (HITL 9종)**: debate-facilitator → ceo 경유 필수.

## 직접 소통 허용 패턴

```
backend-engineer ←→ frontend-engineer  (API 계약 변경 사전 알림)
backend-engineer ←→ db-architect       (쿼리 최적화 협의)
backend-engineer ←→ mlops-engineer     (모델 연동 파라미터)
backend-engineer ←→ media-engineer     (FFmpeg 파이프라인 조율)
prompt-engineer  ←→ backend-engineer   (프롬프트 토큰 최적화)
data-engineer    ←→ backend-engineer   (ETL 스키마 협의)
community-manager ←→ content-moderator (댓글 모더레이션 조율)
compliance-officer ←→ legal-counsel    (정책·법률 경계 조율)
sre-engineer     ←→ pipeline-debugger  (런타임 vs 사후 분석 분업)
```

## 부서장 경유 필요 패턴

```
신규 기능 결정  → cto 또는 해당 부서장
예산 영향 변경  → finance-manager → ceo
SSOT 교차 쓰기  → cto 판단
에이전트 역할 변경 → cto
보안 이슈 발견  → security-engineer → ceo HITL
```

## SendMessage 메시지 포맷

**운영 협의 (peer-to-peer)**:
```
To: {agent}
[협의] {주제} | 영향: {Low/Medium/High} | 응답 기대: {same-session/async}
{간략 내용}
```

**이슈 전달 (Guardian → Builder)**:
```
To: {builder-agent}
[이슈 유형] 파일: {경로:줄번호} | 심각도: CRITICAL/HIGH/MEDIUM/LOW
설명: {문제와 영향} | 수정 담당: {본인 이름}
```

## 채널 분류

| 채널 | 형식 | 대상 |
|---|---|---|
| peer 협의 | SendMessage (직접) | 같은 부서·인접 빌더 |
| HITL 에스컬레이션 | hitl_signals.json + Slack | ceo |
| 부서장 보고 | data/{부서}/reports/ | 주간 정기 |
| 일일 digest | Slack | 전체 (18:00 자동) |

## Anti-Patterns
- 단순 실행 협의를 ceo에게 직접 에스컬레이션 금지
- 부서장을 CC에 넣어 모든 메시지 복사 금지 (중앙집중 회귀)
- peer 소통 결과를 SSOT 없이 구두로만 처리 금지 (문서화 필수)
