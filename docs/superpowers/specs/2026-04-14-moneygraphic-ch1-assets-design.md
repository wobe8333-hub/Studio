# Loomix 7채널 에센셜 브랜딩 에셋 제작 설계 문서

**날짜**: 2026-04-14  
**범위**: CH1~CH7 전체 7채널  
**스타일 공통**: 두들(Doodle) 애니메이션 — 손그림 곡선, stroke 기반 SVG  
**저장 위치**: `assets/channels/CH1/` ~ `assets/channels/CH7/`  
**사용 목적**: Manim 파이프라인 SVG 에셋 + 채널 브랜딩 자료  
**레퍼런스**: `essential_branding/CH1.png` ~ `CH7.png`

---

## 1. 7채널 브랜딩 확정표

| CH | 브랜드명 | 도메인 | 메인 컬러 | HEX | 서브 컬러 |
|----|---------|--------|-----------|-----|----------|
| CH1 | 머니그래픽 | 경제 | 머니그린 | `#2ECC71` | `#3498DB` / `#F1C40F` / `#2C3E50` |
| CH2 | 가설낙서 | 과학 | 네온사이언스 | `#00E5FF` | `#1A1A2E` / `#00B8D4` / `#FFFFFF` |
| CH3 | 홈팔레트 | 부동산 | 홈오렌지 | `#E67E22` | `#3498DB` / `#2ECC71` / `#F1C40F` |
| CH4 | 오묘한심리 | 심리 | 마인드퍼플 | `#9B59B6` | `#2C3E50` / `#BDC3C7` / `#FFFFFF` |
| CH5 | 검은물음표 | 미스터리 | 다크미스트 | `#1C2833` | `#2E4057` / `#AAAAAA` / `#FFFFFF` |
| CH6 | 오래된두루마리 | 역사 | 고서브라운 | `#A0522D` | `#C4A35A` / `#6B4C11` / `#F5F0E0` |
| CH7 | 워메이징 | 전쟁사 | 배틀레드 | `#C0392B` | `#2C3E50` / `#7F8C8D` / `#F1C40F` |

---

## 2. 채널별 캐릭터 포즈 목록

### CH1 — 머니그래픽 (경제)
왕관 쓴 동그란 얼굴 캐릭터
- `character_explain.png` — 설명하는 (Explaining)
- `character_rich.png` — 부자 (Rich)
- `character_money.png` — 부자 + 돈 (Rich More Money)
- `character_lucky.png` — 복권 당첨 (Lottery Winner)

### CH2 — 가설낙서 (과학) · 메인 컬러 #00E5FF / 배경 #1A1A2E
연구실 박사 캐릭터 (손글씨 과학 실험 초보) · 네온 사이언스 스타일
- `character_curious.png` — 호기심 많은
- `character_explain.png` — 설명하는
- `character_research.png` — 연구하는
- `character_serious.png` — 심각한
- `character_data.png` — 데이터 분석하는

### CH3 — 홈팔레트 (부동산)
집 모양 팔레트 캐릭터
- `character_explain.png` — 설명하는 (Explaining)
- `character_buy.png` — 매매 (Buying/Selling)
- `character_invest.png` — 투자 (Investment)
- `character_contract.png` — 계약 (Contract)
- `character_profit.png` — 수익 (Profit)
- `character_dream.png` — 꿈의 집 (Dream Home)

### CH4 — 오묘한심리 (심리)
뇌 심볼 두들 캐릭터
- `character_explore.png` — 심리 이론 탐구
- `character_explain.png` — 마음 설명 중
- `character_anxiety.png` — 정서 불안
- `character_stress.png` — 스트레스 관리
- `character_growth.png` — 자아 성취

### CH5 — 검은물음표 (미스터리)
물음표 두들 캐릭터
- `character_curious.png` — 호기심 많은
- `character_explain.png` — 설명하는
- `character_shocked.png` — 당황한
- `character_think.png` — 고뇌하는
- `character_investigate.png` — 비밀을 찾는
- `character_win.png` — 승리한

### CH6 — 오래된두루마리 (역사)
두루마리 책 캐릭터
- `character_explore.png` — 탐험
- `character_explain.png` — 설명
- `character_scholar.png` — 학자
- `character_travel.png` — 역사 여행

### CH7 — 워메이징 (전쟁사)
두들 장군 캐릭터
- `character_victory.png` — 승리한 장군
- `character_strategy.png` — 전략 고민하는
- `character_battle.png` — 전쟁으로
- `character_general.png` — 두들 장군
- `character_soldier.png` — 치군 장군

---

## 3. 제작 자료 7종 × 7채널

각 채널마다 동일한 7종을 제작. 도구는 채널 공통.

| 자료 | 도구 | 결과 파일 | 비고 |
|------|------|----------|------|
| ① 채널 로고 | Figma MCP → Claude SVG 변환 | `logo/logo.svg` | 500×500px, 투명 배경 |
| ② 채널 캐릭터 | Gemini API (imagen) | `characters/character_*.png` | 1024×1024px, 흰 배경 |
| ③ 영상 인트로 | Claude HTML/CSS/JS | `intro/intro.html` | **3초 통일**, 채널 컬러 적용 |
| ④ 영상 아웃트로 | Claude HTML/CSS/JS | `outro/outro.html` | **10초 통일**, 구독 CTA |
| ⑤ 아이콘 세트 | Claude SVG | `icons/*.svg` | 도메인별 15~20종 |
| ⑥ 영상 템플릿 | Figma MCP → Claude SVG 변환 | `templates/*.svg` | 자막바·썸네일·장면전환 |
| ⑦ 채널 아트·배너 | Claude SVG | `extras/*.svg` | YouTube 규격 |

---

## 4. 채널별 도메인 아이콘 목록

### CH1 — 경제
`money` `coin` `stock_up` `stock_down` `bank` `interest` `exchange` `piggy` `card` `wallet` `calculator` `graph_up` `graph_down` `dollar` `won` `tax` `inflation` `recession` `growth` `bond`

### CH2 — 과학
`flask` `microscope` `atom` `dna` `telescope` `rocket` `lightbulb` `magnet` `circuit` `graph` `beaker` `planet` `formula` `lab_coat` `notebook` `fire` `water` `wind` `electricity` `virus`

### CH3 — 부동산
`house` `apartment` `building` `key` `contract` `loan` `interest` `calculator` `chart_up` `chart_down` `location_pin` `map` `wallet` `handshake` `crown` `door` `window` `garden` `elevator` `bus`

### CH4 — 심리
`brain` `heart` `mirror` `eye` `thought_bubble` `stress_cloud` `growth_arrow` `book` `couch` `clock` `spiral` `question` `star` `shield` `hand_holding` `meditation` `journal` `door_open` `balance` `mask`

### CH5 — 미스터리
`question_mark` `eye_dark` `magnifier` `key_old` `lock` `shadow` `ghost` `skull` `map_torn` `compass` `candle` `raven` `clue` `fingerprint` `door_mystery` `fog` `ancient_book` `crystal_ball` `spider` `moon`

### CH6 — 역사
`scroll` `map_old` `sword` `crown` `castle` `ship` `compass_old` `book_aged` `hourglass` `coin_old` `portrait` `flag` `temple` `arch` `quill` `shield_crest` `lantern` `cart` `gate` `column`

### CH7 — 전쟁사
`sword_crossed` `shield` `tank` `plane` `ship_war` `flag_military` `medal` `map_battle` `cannon` `helmet` `rifle` `bomb` `general_star` `binoculars` `radio` `trench` `grenade` `compass` `dog_tag` `victory`

---

## 5. 정식 폴더 구조

```
assets/channels/
├── CH1/                        # 머니그래픽 (경제)
│   ├── logo/
│   │   └── logo.svg
│   ├── characters/
│   │   ├── character_explain.png
│   │   ├── character_rich.png
│   │   ├── character_money.png
│   │   └── character_lucky.png
│   ├── intro/
│   │   └── intro.html
│   ├── outro/
│   │   └── outro.html
│   ├── icons/                  # 20종 SVG
│   │   ├── money.svg
│   │   └── ...
│   ├── templates/
│   │   ├── subtitle_bar.svg
│   │   ├── thumbnail_template.svg
│   │   ├── transition_wipe.svg
│   │   └── lower_third.svg
│   └── extras/
│       ├── channel_art.svg     # 2560×1440
│       └── profile_banner.svg  # 800×800
├── CH2/                        # 가설낙서 (과학)
│   └── ... (동일 구조)
├── CH3/                        # 홈팔레트 (부동산)
├── CH4/                        # 오묘한심리 (심리)
├── CH5/                        # 검은물음표 (미스터리)
├── CH6/                        # 오래된두루마리 (역사)
└── CH7/                        # 워메이징 (전쟁사)
```

---

## 6. 제작 순서 (채널 순차 처리)

```
CH1 → CH2 → CH3 → CH4 → CH5 → CH6 → CH7
각 채널마다:
  1. 폴더 생성
  2. 로고 SVG
  3. 캐릭터 PNG (Gemini API)
  4. 인트로 HTML
  5. 아웃트로 HTML
  6. 아이콘 SVG 세트
  7. 템플릿 SVG
  8. 채널 아트·배너 SVG
```

---

## 7. 기술 제약 및 공통 SVG 스타일

```svg
<!-- 두들 스타일 공통 속성 -->
fill: none (또는 채널 메인 컬러)
stroke: [채널 메인 컬러]
stroke-width: 3~5
stroke-linecap: round
stroke-linejoin: round
<!-- 손그림 곡선: cubic bezier 불규칙 오프셋 ±2~4px -->
```

- **Manim 호환**: `<path>` `<circle>` `<rect>` `<line>` `<ellipse>` 요소만 사용
- **Gemini API**: `.env`의 `GEMINI_API_KEY` 사용
- **Figma MCP**: 디자인 구조 생성 후 Claude가 SVG 코드로 변환 저장
- **총 산출물**: 7채널 × 약 30~35 파일 = **약 220+ 파일**

---

## 8. 레퍼런스 파일

| 채널 | 에센셜 브랜딩 레퍼런스 |
|------|----------------------|
| CH1 | `essential_branding/CH1.png` |
| CH2 | `essential_branding/CH2.png` |
| CH3 | `essential_branding/CH3.png` |
| CH4 | `essential_branding/CH4.png` |
| CH5 | `essential_branding/CH5.png` |
| CH6 | `essential_branding/CH6.png` |
| CH7 | `essential_branding/CH7.png` |
