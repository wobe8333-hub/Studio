# Figma MCP 썸네일 시스템 설계

**날짜**: 2026-04-07  
**상태**: 승인됨  
**작성자**: Claude Code (brainstorming)

---

## 개요

KAS(Knowledge Animation Studio) Step10 썸네일 생성 방식을 Gemini API 이미지 생성에서 **Figma MCP 마스코트 템플릿 + PIL 텍스트 합성**으로 완전 교체한다.

### 목표

- 채널별 일관된 브랜딩 확보 (Gemini 매번 달라지는 문제 해결)
- Gemini 이미지 생성 쿼터 절약
- 전문적인 레이아웃 C (상단 비주얼 + 하단 텍스트 바) 적용
- 7채널 각각의 색상 아이덴티티 유지

---

## 아키텍처

### 데이터 흐름

```
[1회성] Figma MCP 실행
    → generate_figma_design (채널별 마스코트)
    → get_screenshot (PNG 내보내기)
    → assets/thumbnails/CH{N}_base.png (7개 파일)

[매 파이프라인] Step10 실행
    → CH{N}_base.png 로드
    → PIL 4레이어 합성
        Layer 1: CH{N}_base.png (Figma 마스코트 베이스)
        Layer 2: 하단 40% 반투명 오버레이 (채널 색상)
        Layer 3: 채널명 소형 텍스트 (채널 강조색)
        Layer 4: 제목 대형 텍스트 (흰색 + 채널 강조 키워드)
    → thumbnail_variant_01.png (제목 전체)
    → thumbnail_variant_02.png (숫자·데이터 강조)
    → thumbnail_variant_03.png (질문형 텍스트)

[웹 대시보드]
    → /api/artifacts/{channelId}/{runId}/step10/thumbnail_v*.png
    → 썸네일 탭 A/B/C 비교 표시 (기존 UI 유지)
```

### 수정 파일

| 파일 | 변경 내용 |
|---|---|
| `src/step10/thumbnail_generator.py` | Gemini 생성 제거 → PIL 합성으로 완전 교체 |
| `assets/thumbnails/CH{1-7}_base.png` | Figma MCP로 신규 생성 (7개) |

**변경 없는 파일**: `src/step10/__init__.py`, 웹 대시보드 썸네일 탭, API 라우트

---

## 레이아웃 C 스펙

```
┌──────────────────────────────────┐
│                                  │  ← 상단 62%: Figma 마스코트 베이스
│     [채널 마스코트] [아이콘]      │     (CH{N}_base.png 그대로)
│                                  │
├──────────────────────────────────┤  ← 하단 38%: PIL 합성
│ CH{N} · {채널명}                 │     채널 강조색 반투명 오버레이
│ {제목 텍스트 (강조 키워드 색상)} │     + 텍스트 2줄
└──────────────────────────────────┘
해상도: 1920×1080 (YouTube 권장)
```

### mode별 변형 (출력 파일명: `thumbnail_variant_01/02/03.png`)

| mode | 출력 파일 | 텍스트 전략 | 구현 규칙 |
|---|---|---|---|
| `01` | `thumbnail_variant_01.png` | 제목 전체 표시 | 흰색 텍스트, 하이라이트 없음 |
| `02` | `thumbnail_variant_02.png` | 숫자 대형 강조 | 제목 내 아라비아 숫자 감지 → 대형(2×) + 나머지 소형. 숫자 없으면 mode 01과 동일 |
| `03` | `thumbnail_variant_03.png` | 질문형 변환 | 제목 끝에 "?" 추가, 마지막 어절 채널 primary색으로 렌더링 |

---

## 채널별 디자인 스펙

### CH1 — 경제

- **배경**: 다크 골드 그래디언트 (`#1A1200` → `#2D2000` → `#000000`)
- **강조색 (primary)**: `#FFD700` 골드
- **강조색 (secondary)**: `#EE2400` 레드
- **텍스트 바 배경**: `rgba(180,120,0,0.92)` 골드 오버레이
- **텍스트 바 상단선**: `#FFD700`
- **마스코트**: 귀여운 양복 경제 분석가 + 📈 아이콘
- **Figma 프롬프트 키워드**: `cute chibi economist character, dark gold background, graph chart icon, Korean YouTube thumbnail style`

### CH2 — 부동산

- **배경**: 다크 그린 그래디언트 (`#0A1F0A` → `#1A3A1A` → `#000000`)
- **강조색 (primary)**: `#4CAF50` 그린
- **강조색 (secondary)**: `#F44336` 레드 (손실/이익 대비)
- **텍스트 바 배경**: `rgba(0,80,0,0.92)` 딥그린 오버레이
- **텍스트 바 상단선**: `#4CAF50`
- **마스코트**: 귀여운 부동산 중개사 + 🏘️🗺️ 아이콘
- **Figma 프롬프트 키워드**: `cute chibi real estate agent character, dark green background, building map icon, Korean YouTube thumbnail style`

### CH3 — 심리

- **배경**: 다크 퍼플 그래디언트 (`#0D001A` → `#1A0033` → `#000000`)
- **강조색 (primary)**: `#CE93D8` 라벤더
- **강조색 (secondary)**: `#E040FB` 핫핑크
- **텍스트 바 배경**: `rgba(80,0,120,0.92)` 딥퍼플 오버레이
- **텍스트 바 상단선**: `#CE93D8`
- **마스코트**: 귀여운 심리 상담사 + 🧠💭 아이콘
- **Figma 프롬프트 키워드**: `cute chibi psychologist character, dark purple background, brain thought bubble icon, Korean YouTube thumbnail style`

### CH4 — 미스터리

- **배경**: 극다크 블랙-레드 (`#0A0000` → `#1A0A00` → `#000000`)
- **강조색 (primary)**: `#FF7043` 오렌지레드
- **강조색 (secondary)**: 그림자 효과 (drop-shadow)
- **텍스트 바 배경**: `rgba(100,20,0,0.92)` 다크레드 오버레이
- **텍스트 바 상단선**: `#FF7043`
- **마스코트**: 귀여운 탐정 + 🔍 아이콘
- **Figma 프롬프트 키워드**: `cute chibi detective character, very dark red black background, magnifying glass icon, mystery suspense, Korean YouTube thumbnail style`

### CH5 — 전쟁사

- **배경**: 다크 레드-블랙 (`#1A0505` → `#2D0A0A` → `#000000`)
- **강조색 (primary)**: `#EF9A9A` 크림슨
- **강조색 (secondary)**: `#FF5252` 레드
- **텍스트 바 배경**: `rgba(120,20,20,0.92)` 다크크림슨 오버레이
- **텍스트 바 상단선**: `#EF9A9A`
- **마스코트**: 귀여운 군인 + ⚔️🪖 아이콘
- **Figma 프롬프트 키워드**: `cute chibi military historian character, dark red black background, sword helmet icon, war history, Korean YouTube thumbnail style`

### CH6 — 과학

- **배경**: 딥 네이비-블랙 (`#001A2E` → `#00263D` → `#000000`)
- **강조색 (primary)**: `#4DD0E1` 사이버블루
- **강조색 (secondary)**: `#00E5FF` 민트
- **텍스트 바 배경**: `rgba(0,60,80,0.92)` 딥네이비 오버레이
- **텍스트 바 상단선**: `#4DD0E1`
- **마스코트**: 귀여운 과학자 + 🔬🚀 아이콘
- **Figma 프롬프트 키워드**: `cute chibi scientist character, deep navy black background, microscope rocket icon, space science, Korean YouTube thumbnail style`

### CH7 — 역사

- **배경**: 세피아 다크골드 그래디언트 (`#1A1200` → `#2A1E00` → `#0D0900`)
- **강조색 (primary)**: `#C8A96E` 앤틱골드
- **강조색 (secondary)**: `#FFD54F` 옐로우
- **텍스트 바 배경**: `rgba(80,55,0,0.92)` 세피아 오버레이
- **텍스트 바 상단선**: `#C8A96E`
- **마스코트**: 귀여운 역사학자 + 📜🏛️ 아이콘
- **Figma 프롬프트 키워드**: `cute chibi historian character, sepia dark gold background, scroll temple icon, Korean history, Korean YouTube thumbnail style`

---

## Step10 구현 스펙

### `thumbnail_generator.py` 교체 내용

```python
# 제거: Gemini API 호출, genai.configure, record_image, throttle_if_needed
# 추가: PIL 합성 함수

CHANNEL_BASE_TEMPLATES: dict[str, Path] = {
    "CH1": ROOT / "assets/thumbnails/CH1_base.png",
    # ... CH2~CH7
}

CHANNEL_COLORS: dict[str, dict] = {
    "CH1": {"primary": "#FFD700", "secondary": "#EE2400", "overlay": (180,120,0,235)},
    # ... CH2~CH7
}

def generate_thumbnail(channel_id: str, title: str, mode: str, output_path: Path) -> bool:
    """베이스 PNG 위에 PIL로 텍스트 합성하여 썸네일 생성."""
    base_path = CHANNEL_BASE_TEMPLATES.get(channel_id)
    if not base_path or not base_path.exists():
        return _generate_placeholder(title, output_path)
    
    # 1. 베이스 로드 (1920×1080)
    # 2. 하단 38% 오버레이 합성
    # 3. 채널명 소형 텍스트
    # 4. 제목 텍스트 (mode별 변환)
    # 5. output_path에 PNG 저장
```

### mode별 텍스트 변환 규칙

| mode | 변환 규칙 |
|---|---|
| `01` | 제목 그대로 흰색 텍스트 표시, 하이라이트 없음 |
| `02` | `re.search(r'\d+', title)`로 숫자 감지 → 숫자 폰트 2× 크기, 나머지 일반 크기. 숫자 없으면 mode 01과 동일 |
| `03` | `title + "?"` 로 질문형 변환, 마지막 어절(`title.split()[-1]`) 채널 primary색 적용 |

---

## 에러 처리

| 상황 | 처리 방법 |
|---|---|
| `CH{N}_base.png` 파일 없음 | `_generate_placeholder()` 폴백 (기존 함수 유지) |
| PIL 합성 실패 | `logger.warning` 후 `_generate_placeholder()` 폴백 |
| 제목 텍스트 너무 긴 경우 | 최대 2줄, 줄당 16자 자동 줄바꿈 |

---

## 파일 구조

```
assets/
  thumbnails/
    CH1_base.png    ← Figma MCP 생성 (1920×1080)
    CH2_base.png
    CH3_base.png
    CH4_base.png
    CH5_base.png
    CH6_base.png
    CH7_base.png

src/step10/
  thumbnail_generator.py   ← PIL 합성으로 교체
  title_variant_builder.py ← 변경 없음
  __init__.py              ← 변경 없음
```

---

## 구현 순서

1. Figma MCP로 CH1~CH7 베이스 PNG 7개 생성 및 저장
2. `thumbnail_generator.py` PIL 합성으로 교체
3. 로컬 테스트 (각 채널 × 3 모드 = 21개 썸네일 확인)
4. 기존 Gemini 생성 코드 제거

---

## 비고

- Figma 파일은 Figma 계정에 저장되므로 언제든 수정 후 재내보내기 가능
- PIL 합성 레이어(색상, 폰트 크기, 위치)는 `CHANNEL_COLORS` dict 수정으로 튜닝 가능
- 나중에 Figma REST API 연동 시 동적 텍스트 교체도 가능 (현재 범위 외)
