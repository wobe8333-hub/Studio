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
