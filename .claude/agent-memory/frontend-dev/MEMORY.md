# frontend-dev Memory

> 세션 간 학습 이력 저장. 에이전트가 자동 업데이트.

## 반복 패턴
- [docs HTML 수정 패턴](docs_html_edit_pattern.md) — 대형 standalone HTML 파일은 Read+Edit 조합으로 정밀 수정 (Write 전체 재작성 금지)

## 주의사항
_아직 없음_

## 성공 패턴
- Playwright MCP 브라우저 세션이 닫혀 있을 때: curl로 HTTP 서버 응답 확인 후 파일 내 Grep으로 수정 검증
