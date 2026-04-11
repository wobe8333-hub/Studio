# KAS 다크모드 — Crimson Night 설계

## 개요

기본 테마를 라이트 모드로 고정하고, Crimson Night 팔레트의 다크모드를 추가한다.
사용자가 헤더 토글 버튼으로 언제든 전환 가능하다.

## 변경 파일

### 1. `web/app/globals.css`

**`.dark` 섹션 전면 교체** — Crimson Night 팔레트:

| 변수 | 값 | 역할 |
|------|-----|------|
| `--background` | `#1a0808` | 페이지 배경 |
| `--foreground` | `#ffdede` | 기본 텍스트 |
| `--card` | `rgba(42,16,16,0.80)` | 카드 배경 (글래스) |
| `--primary` | `#e85555` | 버튼, 강조 |
| `--muted-foreground` | `#c08080` | 보조 텍스트 |
| `--border` | `rgba(255,100,100,0.20)` | 구분선 |
| `--sidebar` | `rgba(61,15,15,0.95)` | 사이드바 배경 |
| `--glass-bg` | `rgba(42,16,16,0.80)` | 글래스카드 배경 |
| `--glass-border` | `rgba(255,100,100,0.20)` | 글래스카드 테두리 |

**`@layer base` body 배경 다크모드 추가:**
```css
.dark body {
  background: linear-gradient(135deg, #1a0808 0%, #250d0d 40%, #1e0a0a 100%);
}
```

### 2. `web/app/layout.tsx`

- 헤더에 `<ThemeToggle />` 컴포넌트 추가 (LIVE 배지 오른쪽)
- 헤더 배경을 CSS 변수 `var(--sidebar)` 기반으로 전환 (다크모드 자동 반응)

## 기본 동작

- `defaultTheme="light"` 유지 (첫 방문 시 라이트모드)
- `enableSystem={false}` 유지 (OS 설정 무시)
- `localStorage`에 사용자 선택 자동 저장 (next-themes 기본 동작)

## 범위 외

- 각 페이지 컴포넌트의 `CARD_BASE` 인라인 스타일은 이미 CSS 변수를 참조하므로 별도 수정 불필요
- 사이드바(`sidebar-nav.tsx`)의 배경은 `--sidebar` 변수를 이미 사용하므로 자동 반영
