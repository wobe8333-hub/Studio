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
