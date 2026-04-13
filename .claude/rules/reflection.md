# Reflection 패턴 — 세션 간 교훈 누적 (공통)

> 모든 에이전트의 Reflection 지침. 개별 에이전트 파일에서 중복 선언하지 않는다.

## 기본 원칙

Reflection은 **선택이 아닌 의무**다. 미션 종료 후 반드시 기록한다.

## 저장 위치

```
~/.claude/agent-memory/{agent-name}/MEMORY.md
```

## 기록 항목

1. **성공 패턴**: 무엇이 효과적이었는가? (재사용 가능한 접근법)
2. **실패 패턴**: 무엇이 시간 낭비였는가? (반복 금지 실수)
3. **의존성 교훈**: 다른 에이전트와 협업 시 발견한 인터페이스 주의사항
4. **다음 세션 컨텍스트**: 다음에 같은 미션을 받으면 먼저 확인해야 할 것

## 포맷

```markdown
# MEMORY.md — {에이전트명}

## {날짜} 세션 교훈
- **성공**: ...
- **실패**: ...
- **다음 확인**: ...
```

## PreCompact 훅 자동 저장

컨텍스트 압축 직전 `PreCompact` 훅이 `data/global/learning_feedback.json`에
세션 ID와 타임스탬프를 자동 기록한다. 핵심 교훈은 에이전트가 직접 MEMORY.md에 작성해야 한다.

## cto/ceo 특별 지침

`initialPrompt`에서 `data/global/notifications/hitl_signals.json`과
`data/exec/team_lifecycle.json`을 먼저 확인한 후 Reflection 기록.
