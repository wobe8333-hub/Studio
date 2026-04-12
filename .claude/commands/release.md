---
description: release-manager 소환 — CHANGELOG + git tag + PR 생성
---

release-manager 에이전트를 소환하세요.

순서:
1. `git log --oneline -20` 으로 마지막 태그 이후 커밋 확인
2. feat/fix/refactor/docs/perf 로 분류
3. `CHANGELOG.md` 업데이트 (기존 형식 유지)
4. `git tag $ARGUMENTS` — 버전 미지정 시 마지막 태그에서 semver 자동 계산
5. `gh pr create` 로 PR 생성

$ARGUMENTS: 버전 태그 (예: "v1.2.0"). 미지정 시 자동 계산.
