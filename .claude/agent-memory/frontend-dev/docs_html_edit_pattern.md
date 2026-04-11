---
name: docs HTML 수정 패턴
description: docs/ 디렉토리의 대형 standalone HTML 파일 수정 시 검증된 접근 방법
type: feedback
---

대형 standalone HTML 파일(1000줄 이상)은 Write로 전체 재작성하면 너무 크다. Read로 100줄씩 나누어 구조 파악 후 Edit으로 정밀 수정한다.

**Why:** agent-teams-visual.html이 1100줄 규모여서 Write 재작성 시 오류 위험이 높고 사용자가 금지 지시를 내림.

**How to apply:**
1. Read offset+limit으로 파일을 섹션별 분할 독해
2. 수정 대상 고유 문자열을 찾아 Edit으로 점진적 패치
3. 수정 완료 후 Grep으로 핵심 변경사항 전체 검증
4. Playwright MCP 세션이 닫혀 있을 때는 curl + Grep 조합으로 대체 검증
