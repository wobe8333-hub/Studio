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
