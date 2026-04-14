# 머니그래픽 CH1 채널 에셋 제작 설계 문서

**날짜**: 2026-04-14  
**채널**: CH1 — 머니그래픽 (경제)  
**스타일**: 두들(Doodle) 애니메이션  
**저장 위치**: `임시/` 폴더  
**사용 목적**: Manim 파이프라인 SVG 에셋 + 영상 편집 보조 자료

---

## 1. 브랜딩 기준

### 컬러 팔레트
| 역할 | 이름 | HEX |
|------|------|-----|
| Primary | 머니그린 | `#2ECC71` |
| Primary | 비즈블루 | `#3498DB` |
| Primary | 골드옐로 | `#F1C40F` |
| Primary | 차콜블랙 | `#2C3E50` |
| Accent | 어텐션레드 | `#E74C3C` |
| Background | 화이트 | `#FFFFFF` |

### 스타일 원칙
- **두들(Doodle)**: 불규칙한 손그림 곡선, 두꺼운 선(stroke-width 3~5), 약간의 비정형감
- **폰트**: 손글씨 계열 (Gmarket Sans Bold 또는 Nanum Pen Script)
- **캐릭터**: 왕관 쓴 동그란 얼굴, 단순화된 몸체, 과장된 표정

---

## 2. 제작 자료 7종 — 도구·결과물 매핑

### ① 채널 로고 — Figma MCP → Claude SVG 변환
- **설명**: "머니그래픽" 텍스트 + 왕관 캐릭터 원형 배지
- **도구**: `mcp__figma__generate_figma_design`으로 디자인 구조 생성 → Claude가 SVG 코드로 변환 후 저장
- **결과물**: `임시/logo/logo.svg`
- **스펙**: 500×500px 기준, 배경 투명, 두들 원형 외곽선
- **주의**: Figma MCP는 Figma 클라우드에 파일을 생성하며 로컬 저장은 Claude SVG 코딩으로 완성

### ② 채널 캐릭터 — Gemini API (imagen-3.0)
- **설명**: 왕관 캐릭터 4가지 포즈
  - `character_explain.png` — 설명하는 포즈 (손가락 가리키기)
  - `character_rich.png` — 부자 포즈 (돈 들고 웃는)
  - `character_money.png` — 돈다발 포즈
  - `character_lucky.png` — 복권 당첨 포즈 (깜짝 놀란)
- **도구**: Gemini `imagegeneration` API (`GEMINI_API_KEY`)
- **프롬프트 전략**: "cute doodle style character, crown, white background, simple lines, economic theme, 두들 애니메이션 스타일"
- **결과물**: `임시/characters/*.png` (1024×1024px)

### ③ 영상 인트로 (3초) — HTML/CSS/JS
- **설명**: 슬라이드 인 애니메이션 → 로고 등장 → 채널명 타이핑
- **도구**: Claude 직접 코딩
- **결과물**: `임시/intro/intro.html`
- **스펙**:
  - 0.0~0.5s: 배경 페이드 인 (차콜블랙)
  - 0.5~1.5s: 로고 슬라이드 인 (왼쪽→중앙)
  - 1.5~2.5s: "머니그래픽" 타이핑 효과
  - 2.5~3.0s: 전체 페이드 아웃

### ④ 영상 아웃트로 (10초) — HTML/CSS/JS
- **설명**: 구독·공유 CTA + 다음 영상 추천 카드
- **도구**: Claude 직접 코딩
- **결과물**: `임시/outro/outro.html`
- **스펙**:
  - 0~2s: "영상이 도움됐나요?" 텍스트 + 캐릭터 등장
  - 2~6s: 구독 버튼(빨간) + 좋아요(파란) 버튼 애니메이션
  - 6~10s: 다음 영상 추천 카드 2개 + 유튜브 엔드카드 레이아웃

### ⑤ 영상 아이콘 세트 (20종+) — Claude SVG
- **설명**: 경제 도메인 두들 스타일 아이콘
- **도구**: Claude 직접 코딩 (Manim SVGMobject 완벽 호환)
- **결과물**: `임시/icons/*.svg`
- **아이콘 목록** (각 100×100px, stroke 기반):

| 파일명 | 아이콘 |
|--------|--------|
| `money.svg` | 돈다발 |
| `coin.svg` | 동전 |
| `stock.svg` | 주식 차트 (상승) |
| `stock_down.svg` | 주식 차트 (하락) |
| `bank.svg` | 은행 건물 |
| `house.svg` | 집/부동산 |
| `interest.svg` | 금리 (%) |
| `exchange.svg` | 환율 (화살표) |
| `piggy.svg` | 돼지저금통 |
| `card.svg` | 신용카드 |
| `wallet.svg` | 지갑 |
| `calculator.svg` | 계산기 |
| `graph_up.svg` | 상승 그래프 |
| `graph_down.svg` | 하락 그래프 |
| `dollar.svg` | 달러 기호 |
| `won.svg` | 원화 기호 |
| `tax.svg` | 세금/서류 |
| `inflation.svg` | 물가상승 (풍선) |
| `recession.svg` | 경기침체 (구름) |
| `growth.svg` | 경제성장 (화살표+식물) |

- **SVG 스타일**: `fill:none`, `stroke:#2C3E50`, `stroke-width:3`, `stroke-linecap:round`, `stroke-linejoin:round`

### ⑥ 영상 템플릿 — Figma MCP → Claude SVG 변환
- **설명**: 자막바, 장면 전환, 썸네일 틀
- **도구**: `mcp__figma__generate_figma_design`으로 레이아웃 구조 설계 → Claude가 SVG로 변환 저장
- **결과물**: `임시/templates/*.svg`
- **세부 항목**:
  - `subtitle_bar.svg` — 하단 자막바 (검정 배경, 흰 텍스트, 두들 테두리)
  - `transition_wipe.svg` — 장면 전환 와이프 마스크
  - `thumbnail_template.svg` — 썸네일 1280×720 틀 (제목영역+캐릭터영역+배경)
  - `lower_third.svg` — 하단 3분의1 자막 (이름/출처 표시용)

### ⑦ 기타 채널 자료 — Claude SVG
- **설명**: YouTube 채널 규격 에셋
- **도구**: Claude 직접 코딩
- **결과물**: `임시/extras/*.svg`
- **세부 항목**:
  - `channel_art.svg` — 채널 아트 2560×1440px
  - `profile_banner.svg` — 프로필 배너 800×800px
  - `end_card_layout.svg` — 엔드카드 레이아웃 가이드

---

## 3. 폴더 구조

```
임시/
├── logo/
│   └── logo.svg
├── characters/
│   ├── character_explain.png
│   ├── character_rich.png
│   ├── character_money.png
│   └── character_lucky.png
├── intro/
│   └── intro.html
├── outro/
│   └── outro.html
├── icons/
│   ├── money.svg
│   ├── coin.svg
│   ├── stock.svg
│   └── ... (20종)
├── templates/
│   ├── subtitle_bar.svg
│   ├── transition_wipe.svg
│   ├── thumbnail_template.svg
│   └── lower_third.svg
└── extras/
    ├── channel_art.svg
    ├── profile_banner.svg
    └── end_card_layout.svg
```

---

## 4. 제작 순서

1. **폴더 구조 생성** — `임시/` 하위 7개 폴더
2. **채널 로고** — Figma MCP `generate_figma_design`
3. **채널 캐릭터** — Gemini API Python 스크립트
4. **영상 인트로** — HTML/CSS/JS
5. **영상 아웃트로** — HTML/CSS/JS
6. **아이콘 세트** — Claude SVG 코딩 (20종)
7. **영상 템플릿** — Figma MCP
8. **기타 채널 자료** — Claude SVG 코딩

---

## 5. 기술 제약 및 주의사항

- **Manim 호환**: SVG 내부는 `<path>`, `<circle>`, `<rect>`, `<line>` 요소만 사용. `<text>` 요소는 Manim에서 별도 처리 필요
- **Gemini API**: `.env`의 `GEMINI_API_KEY` 사용. `imagen-3.0-generate-002` 모델
- **Figma MCP**: `mcp__figma__generate_figma_design` 도구로 디자인 생성
- **Windows 인코딩**: Python 스크립트 사용 시 UTF-8 명시 필요
- **파일 저장**: `src/core/ssot.py`의 `write_json()` 대신 일반 파일 I/O 사용 (JSON이 아닌 SVG/PNG/HTML)
