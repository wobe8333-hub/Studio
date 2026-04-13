---
description: 완료 전 검증 — pytest + ruff + build 통과 확인
---

superpowers:verification-before-completion 스킬을 호출하여
현재 변경사항이 완료 기준을 만족하는지 확인하세요.

검증 체크리스트:
1. `pytest tests/ -x -q --ignore=tests/test_step08_integration.py`
2. `ruff check src/ --select=E,F`
3. `cd web && npm run build`
4. `git status` — 커밋되지 않은 파일 목록

모두 통과하면 커밋 준비 완료.
실패 항목은 담당 에이전트에게 자동 에스컬레이션:
- pytest 실패 → backend-engineer
- npm build 실패 → frontend-engineer
- ruff 실패 → backend-engineer

$ARGUMENTS: 검증 범위 (예: "backend-only" 또는 "frontend-only"). 미지정 시 전체.
