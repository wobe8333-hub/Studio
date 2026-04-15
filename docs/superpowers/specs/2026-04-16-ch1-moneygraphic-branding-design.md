# CH1 머니그래픽 브랜딩 시스템 설계

**채널**: CH1 — 머니그래픽 (경제)
**날짜**: 2026-04-16
**상태**: 승인됨
**작성**: 브레인스토밍 세션 (사용자 승인)

---

## Context

기존 CH1 브랜딩 자산(Imagen 4.0 + gemini-3.1-flash-image-preview 생성물)이 레퍼런스 두들 스타일 재현 실패, 텍스트 오염(hex code), 3D 느낌 등의 문제로 전면 폐기되었다. 이번 설계는 완전히 새로운 캐릭터·스타일·에셋 시스템을 확립하여 앞으로 생성되는 **모든 영상에 재사용 가능한 브랜드 바이블**을 구축하는 것이 목적이다. CH1 완성 후 동일 파이프라인을 CH2~CH7에 순차 적용한다.

---

## 1. 채널 아이덴티티

| 항목 | 내용 |
|---|---|
| 채널명 | 머니그래픽 |
| 분야 | 경제 (금리·부동산·주식·재테크·거시경제) |
| 캐릭터명 | **원이** |
| 슬로건 | 경제를 쉽고 재미있게 |
| 캐릭터 컨셉 | ₩ 왕관을 쓴 미니멀 둥근 마스코트 — "돈의 왕" |

---

## 2. 캐릭터 스펙 — 원이

### 2-1. 외형 정의

| 요소 | 스펙 |
|---|---|
| 바디 형태 | 완전히 둥근 원형 (Molang/Mochi 계열) |
| 바디 색상 | 순백 #FFFFFF |
| 바디 아웃라인 | 검정 #333333, 2.2px |
| 왕관 | 골드 #F4C420, 아웃라인 #854D0E |
| 왕관 문양 | ₩ 원화 심볼 (문자가 아닌 형태로 암시) |
| 왕관 보석 | 중앙 초록 #16A34A, 양쪽 핑크 #FED7AA |
| 볼터치 | 살구 #F4C420 opacity 50%, 양볼 대칭 |
| 눈 | 검정 작은 원형 2개, 흰 하이라이트 점 |
| 입 | 위로 향하는 곡선 (기본 미소) |
| 팔 | 가늘고 짧은 막대형 |
| 다리 | 가늘고 짧은 막대형 |
| 손/발 | 없음 (막대 끝 처리) |

### 2-2. 캐릭터 포즈 10종

| # | 포즈명 | 설명 | 주 사용처 |
|---|---|---|---|
| 01 | 기본 (정면) | 팔 내리고 직립, 미소 | 채널 아이콘·로고 |
| 02 | 설명 | 오른팔 들어 가리키기, 눈 크게 | 영상 본편 차트 설명 |
| 03 | 놀람 | 양팔 벌림, 입 O자, 눈 크게 | 충격 뉴스·큰 변화 |
| 04 | 기쁨 | 점프, 양팔 위로, 눈 ^^ | 수익·긍정 소식 |
| 05 | 슬픔 | 고개 숙임, 눈물 한 방울 | 손실·하락·위기 |
| 06 | 생각 | 한 손 턱 짚기, 눈 옆 보기 | 분석·고민 장면 |
| 07 | 승리 | 엄지척 (한쪽), 윙크 | 정답·결론·요약 |
| 08 | 경고 | 양손 앞으로, 눈썹 내림 | 주의·리스크 강조 |
| 09 | 앉기 | 책상/의자에 앉아서 | 장시간 설명·인트로 |
| 10 | 달리기 | 옆면, 달리는 포즈 | 긴급 뉴스·속보 |

---

## 3. 스타일 시스템 — C+B 하이브리드

### 3-1. 본편 영상 스타일 (Style C — Doodly 클래식)

- **배경**: 순백 #FFFFFF
- **라인**: 검정 #333333, 2.5~3px
- **채색**: 포인트 컬러 2종만 (지폐 초록 #16A34A, 동전/왕관 골드 #F4C420)
- **손그림 흔들림**: 중간 강도 (wobbly hand-drawn lines)
- **그림자/그라디언트**: 완전 금지
- **3D 효과**: 완전 금지

### 3-2. 썸네일 스타일 (Style B — Vox 파스텔 플랫)

- **배경**: 골드 #F4C420 또는 크림 #FFF8E7
- **라인**: 검정 #333333, 3.5~4px (본편보다 두껍게)
- **채색**: 파스텔 플랫 (FED7AA·A7F3D0·FBCFE8·C4B5FD 사용 가능)
- **텍스트 배경**: #333333 다크 박스
- **텍스트 색**: 흰색 #FFFFFF (제목) / #F4C420 (강조)

---

## 4. 컬러 팔레트

| 역할 | 색상명 | Hex | 용도 |
|---|---|---|---|
| Primary | 골든 옐로우 | `#F4C420` | 왕관·배경 포인트·강조 |
| Secondary | 차콜 | `#333333` | 라인·자막바·텍스트 |
| Accent Red | 경고 레드 | `#DC2626` | 상승↑·위험·긴급 강조 |
| Accent Green | 수익 그린 | `#16A34A` | 하락↓·긍정·수익·보석 |
| Base | 순백 | `#FFFFFF` | 캐릭터 바디·배경 |
| Sub | 크림 | `#FFF8E7` | 썸네일 보조 배경 |
| Sub | 볼터치 살구 | `#FED7AA` | 캐릭터 볼·썸네일 살색 |

---

## 5. 에셋 인벤토리 — 52종

### 5-1. 캐릭터 (10종)
`assets/channels/CH1/characters/`

```
wonee_default.png       # 기본 정면
wonee_explain.png       # 설명 (가리키기)
wonee_surprised.png     # 놀람
wonee_happy.png         # 기쁨 (점프)
wonee_sad.png           # 슬픔
wonee_thinking.png      # 생각
wonee_victory.png       # 승리 (엄지척)
wonee_warning.png       # 경고
wonee_sitting.png       # 앉기
wonee_running.png       # 달리기
```

### 5-2. 썸네일 템플릿 (5종)
`assets/channels/CH1/templates/`

```
thumb_standard.png      # 캐릭터 왼쪽 + 텍스트 오른쪽
thumb_impact.png        # 전체 배경 + 텍스트 하단
thumb_compare.png       # 좌우 비교 레이아웃 (A vs B)
thumb_question.png      # 물음표 강조형
thumb_urgent.png        # 빨간 강조 (긴급 뉴스)
```

### 5-3. 자막바 & 로어써드 (4종)
`assets/channels/CH1/templates/`

```
subtitle_default.png    # 하단 가로 전체, #333333 배경
subtitle_accent.png     # #F4C420 왼쪽 포인트 바 포함
lowerthird_l.png        # 좌하단 L자형 (인터뷰/설명)
lowerthird_bubble.png   # 원이 말풍선형
```

### 5-4. 화면 전환 (5종)
`assets/channels/CH1/transitions/`

```
trans_ink.png           # 잉크 번짐
trans_zoom.png          # 줌인
trans_slide.png         # 좌→우 슬라이드
trans_page.png          # 종이 넘기기
trans_fade.png          # 페이드 (단색)
```

### 5-5. 인트로 & 아웃트로 (2종)
`assets/channels/CH1/`

```
intro.html              # 3초 CSS 애니메이션
outro.html              # 10초 구독 CTA
```

### 5-6. 경제 아이콘 세트 (20종)
`assets/channels/CH1/icons/`

```
icon_banknote.png       # 지폐/원화
icon_coin.png           # 동전
icon_piggybank.png      # 돼지저금통
icon_chart_up.png       # 상승 차트 (Red)
icon_chart_down.png     # 하락 차트 (Green)
icon_house.png          # 부동산/집
icon_bank.png           # 은행 건물
icon_card.png           # 신용카드
icon_stock.png          # 주식 화면
icon_interest.png       # 금리/퍼센트
icon_inflation.png      # 인플레이션 (가격표↑)
icon_exchange.png       # 환율 (달러↔원)
icon_fund.png           # 펀드/포트폴리오
icon_calculator.png     # 계산기
icon_savings.png        # 통장/저축
icon_tax.png            # 세금 (영수증)
icon_loan.png           # 대출 (서류)
icon_gdp.png            # GDP/경제성장 (그래프+국기)
icon_centralbank.png    # 중앙은행 (건물+원)
icon_wallet.png         # 지갑
```

### 5-7. 섹션 구분자 (3종)
`assets/channels/CH1/templates/`

```
divider_basic.png       # 가로선 + 번호
divider_title.png       # 섹션 제목 배너
divider_highlight.png   # 강조 박스 (Primary 배경)
```

### 5-8. 채널 아트 (3종)
`assets/channels/CH1/`

```
profile_icon.png        # 800×800 원이 얼굴 (유튜브 프로필)
channel_banner.png      # 2560×1440 채널 배너
channel_logo.png        # 가로형 로고 (채널명 + 원이)
```

---

## 6. 기술 파이프라인

### 6-1. 모델 업그레이드

```python
# scripts/generate_branding/nano_banana_helper.py
# 기존 (Flash)
MODEL_MULTIMODAL = "gemini-3.1-flash-image-preview"

# 변경 (Pro)
MODEL_MULTIMODAL = "gemini-3-pro-image-preview"
```

### 6-2. 3단계 생성 전략

```
Stage 1 — 캐릭터 시트 생성
  원이 정면·측면·뒷면·4표정을 한 장에 생성
  → essential_branding/CH1_wonee_sheet.png 저장
  → 이후 모든 호출의 reference 이미지로 사용

Stage 2 — 스타일 바이블 생성
  팔레트 적용 환경(배경·자막바·썸네일) 통합 참고 이미지
  → essential_branding/CH1_style_bible.png 저장

Stage 3 — 개별 에셋 생성
  캐릭터 시트 + 스타일 바이블 동시 reference 투입
  Best-of-3 방식으로 각 에셋 생성
```

### 6-3. 텍스트 오염 방지 프롬프트 규칙

모든 프롬프트 공통 suffix:

```
STRICT RULES:
- NO text, NO labels, NO captions, NO hex codes anywhere
- NO letters or numbers inside the crown
- NO 3D effects, NO shading, NO gradients
- Pure flat 2D hand-drawn doodle only
- Pure white background #FFFFFF (character assets)
- Exactly 2 arms, exactly 2 legs — NO extra limbs
```

### 6-4. 파일 구조 변경

```
assets/channels/CH1/           ← 기존 파일 전체 교체
├── characters/                ← 원이 10종
├── templates/                 ← 썸네일·자막바·구분자 12종
├── transitions/               ← 화면전환 5종
├── icons/                     ← 경제 아이콘 20종
├── intro.html
├── outro.html
├── profile_icon.png
├── channel_banner.png
└── channel_logo.png

essential_branding/
├── CH1_wonee_sheet.png        ← 신규 (캐릭터 시트 레퍼런스)
└── CH1_style_bible.png        ← 신규 (스타일 바이블 레퍼런스)
```

---

## 7. 생성 스크립트 수정 범위

| 파일 | 변경 내용 |
|---|---|
| `nano_banana_helper.py` | MODEL_MULTIMODAL → Pro, BUDGET_LIMIT 조정 |
| `character_gen.py` | 원이 10포즈 프롬프트 정의, 3단계 파이프라인 연결 |
| `run_all.py` | Stage 1→2→3 순서 보장, 에셋 52종 배선 |
| `config.py` | CH1 팔레트 hex 상수 등록 |
| `template_gen.py` | 썸네일 5종·자막바 4종·구분자 3종 |
| `icon_gen.py` | 경제 아이콘 20종 프롬프트 |
| `intro_gen.py` | 원이 + 팔레트 적용 인트로 재제작 |
| `outro_gen.py` | 원이 + 팔레트 적용 아웃트로 재제작 |
| `setup_folders.py` | 새 디렉토리 구조 (icons/ 추가) |
| `tests/test_branding_assets.py` | 52종 assertion 갱신 |

---

## 8. 검증 기준

### 8-1. 자동 검증 (pytest)
- 52종 파일 존재 확인
- 각 이미지 크기 기준 통과 (캐릭터: 1024×1024 이상, 썸네일: 1920×1080)
- 투명 배경 필요 에셋 (캐릭터) — alpha 채널 확인

### 8-2. 시각 품질 기준 (수동)
- 원이 왕관이 모든 포즈에서 일관된 형태
- ₩ 기호가 텍스트가 아닌 왕관 형태로 표현
- hex 코드 텍스트 오염 없음
- 팔다리 수 정확 (팔 2개, 다리 2개)
- 배경 순백 (캐릭터 에셋)

### 8-3. 완료 기준
- `python scripts/generate_branding/run_all.py --channel CH1` 성공
- `pytest tests/test_branding_assets.py -q` 전체 통과
- 수동 시각 검수 통과

---

## 9. CH2~CH7 확장 계획

CH1 파이프라인 완성 후 동일 구조를 각 채널 테마에 맞게 적용:

| 채널 | 분야 | 캐릭터 컨셉 (미정) |
|---|---|---|
| CH2 | 부동산 | 집 모양 왕관 캐릭터 |
| CH3 | 심리 | 뇌/전구 왕관 캐릭터 |
| CH4 | 미스터리 | 돋보기/눈 왕관 캐릭터 |
| CH5 | 전쟁사 | 투구 왕관 캐릭터 |
| CH6 | 과학 | 원자/플라스크 왕관 캐릭터 |
| CH7 | 역사 | 두루마리 왕관 캐릭터 |

> CH2~CH7 캐릭터 컨셉은 CH1 완성 후 동일 브레인스토밍 프로세스로 확정.

---

*스펙 작성: 브레인스토밍 세션 2026-04-16*
*승인: 사용자 확인 완료*
