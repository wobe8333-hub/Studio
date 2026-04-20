# CH1 브랜딩 파일럿 구현 계획 — 시나리오 D (하이브리드)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** CH1 캐릭터 생성 방식을 Gemini 멀티모달(reference image 입력) 로 전환하고, 나머지 11종 자산을 프로그래매틱 SVG/Manim 파이프라인으로 완성한다.

**Architecture:** 3개 독립 서브플랜으로 분리. 이 문서는 **서브플랜 A** — 캐릭터 POC + 캐릭터 생성기 교체. 서브플랜 B(프로그래매틱 자산), C(모션+파이프라인 통합)는 A 완료 후 진행.

**Tech Stack:** `google-genai` SDK, `gemini-2.0-flash-exp` (멀티모달 이미지 생성), PIL, pytest

> ⚠️ **범위 선행 체크** — 기존 `scripts/generate_branding/` 코드 현황:
> - 이미 존재: `character_gen.py`, `icon_gen.py`, `logo_gen.py`, `intro_gen.py`, `outro_gen.py`, `svg_helpers.py`
> - 이미 존재: `assets/channels/CH1/` 구조 + 테스트 `tests/test_branding_assets.py`
> - 문제: `character_gen.py`가 `imagen-4.0-generate-001` (텍스트 전용) 사용 → 두들 스타일 재현 실패
> - 해결 목표: `gemini-2.0-flash-exp` 멀티모달로 교체 (reference 이미지 입력 지원)

---

## 파일 구조 (변경 대상만)

```
scripts/generate_branding/
├── nano_banana_helper.py       ← 신규: Gemini 멀티모달 이미지 생성 래퍼
├── style_guide_loader.py       ← 신규: essential_branding/CH1.png 분석 + style guide JSON
├── character_gen.py            ← 수정: Imagen → Gemini 멀티모달 분기 추가
└── run_all.py                  ← 수정: --channel CH1 --mode poc 옵션 추가

assets/channels/CH1/
└── manifest.json               ← 신규: 채널 style guide + 자산 인덱스
```

---

## Task 1: POC — Gemini 멀티모달 캐릭터 1장 테스트

**목표:** `essential_branding/CH1.png`를 reference로 전달하면 두들 스타일 캐릭터가 생성되는지 확인한다.

**Files:**
- Create: `scripts/generate_branding/nano_banana_helper.py`
- Test: `scripts/test_nano_banana_poc.py` (임시 테스트 스크립트, 완료 후 삭제)

- [ ] **Step 1: nano_banana_helper.py 작성**

```python
# scripts/generate_branding/nano_banana_helper.py
"""Gemini 2.0 Flash 멀티모달 이미지 생성 헬퍼.

Imagen 4.0 (텍스트 전용) 대신 reference 이미지를 함께 전달해
두들 스타일 전이를 시도한다.
"""
import os
from pathlib import Path
from typing import Optional

from google import genai
from google.genai import types
from loguru import logger

# 멀티모달 이미지 생성 지원 모델
# imagen-4.0-generate-001은 텍스트 전용 → 두들 스타일 재현 실패
# gemini-2.0-flash-exp는 image+text 입력 → image 출력 지원
MODEL_MULTIMODAL = "gemini-2.0-flash-exp"

# 예산 하드스톱
_call_count = 0
BUDGET_LIMIT = 30


class BudgetExceededError(Exception):
    pass


def _make_client() -> genai.Client:
    api_key = os.environ.get("GEMINI_API_KEY", "")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY 환경 변수 미설정")
    return genai.Client(api_key=api_key)


def generate_with_reference(
    reference_image_path: Path,
    prompt: str,
    output_path: Path,
    *,
    client: Optional[genai.Client] = None,
) -> bool:
    """reference 이미지 스타일을 참고해 새 이미지를 생성한다.

    Args:
        reference_image_path: 스타일 참고용 레퍼런스 PNG (essential_branding/CH1.png 등)
        prompt: 생성할 캐릭터/자산 설명
        output_path: 저장 경로
        client: 재사용 클라이언트 (None이면 신규 생성)

    Returns:
        True if 성공, False if 실패
    """
    global _call_count
    if _call_count >= BUDGET_LIMIT:
        raise BudgetExceededError(f"API 호출 {BUDGET_LIMIT}회 초과 — 하드스톱")

    if client is None:
        client = _make_client()

    # reference 이미지 읽기
    ref_bytes = reference_image_path.read_bytes()
    ref_part = types.Part.from_bytes(data=ref_bytes, mime_type="image/png")

    full_prompt = (
        f"Replicate EXACTLY the flat 2D hand-drawn doodle illustration style shown "
        f"in the reference image. Same line weight (2-3px thin black marker), "
        f"same cream paper background (#FFFDF5), same wobbly hand-drawn lines, "
        f"same flat coloring with NO gradients or shadows. "
        f"Now generate: {prompt}. "
        f"Output ONLY the character on transparent/cream background, NO text, NO labels."
    )

    try:
        response = client.models.generate_content(
            model=MODEL_MULTIMODAL,
            contents=[ref_part, full_prompt],
            config=types.GenerateContentConfig(
                response_modalities=["IMAGE"],
            ),
        )
        _call_count += 1

        # 이미지 bytes 추출
        for part in response.candidates[0].content.parts:
            if part.inline_data and part.inline_data.mime_type.startswith("image/"):
                output_path.parent.mkdir(parents=True, exist_ok=True)
                output_path.write_bytes(part.inline_data.data)
                logger.info(f"[OK] {output_path.name} ({len(part.inline_data.data):,} bytes)")
                return True

        logger.error(f"[WARN] 이미지 응답 없음: {response.candidates[0].content}")
        return False

    except Exception as e:
        logger.error(f"[ERR] generate_with_reference: {e}")
        return False
```

- [ ] **Step 2: POC 테스트 스크립트 작성**

```python
# scripts/test_nano_banana_poc.py
"""POC: Gemini 멀티모달로 CH1 explain 캐릭터 1장 생성 후 시각 검수"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from dotenv import load_dotenv

load_dotenv()

from generate_branding.nano_banana_helper import generate_with_reference
from generate_branding.config import CHANNELS, KAS_ROOT

REFERENCE = KAS_ROOT / "essential_branding" / "CH1.png"
OUT = KAS_ROOT / "assets" / "channels" / "CH1" / "characters" / "character_explain_poc.png"

ch1 = CHANNELS["CH1"]
prompt = ch1["character_prompts"]["explain"]

ok = generate_with_reference(REFERENCE, prompt, OUT)
if ok:
    print(f"POC 성공: {OUT}")
    print("→ 사용자 시각 검수 필요: 두들 스타일 일치 여부 확인")
else:
    print("POC 실패 → SVG 폴백 고려")
```

- [ ] **Step 3: POC 실행**

```bash
cd C:\Users\조찬우\Desktop\ai_stuidio_claude
python scripts/test_nano_banana_poc.py
```

예상 결과:
- 성공: `assets/channels/CH1/characters/character_explain_poc.png` 생성
- 실패: 모델이 이미지 출력 미지원 → Task 2로 이동 (SVG 폴백)

- [ ] **Step 4: 생성된 이미지 시각 검수**

`assets/channels/CH1/characters/character_explain_poc.png`를 열어 확인:
- ✅ 크림 배경 (#FFFDF5)
- ✅ 얇은 검정 마커 선 (2-3px)
- ✅ 평면 2D (그림자·그라디언트 없음)
- ✅ 삐뚤빼뚤한 손그림 선
- ❌ 텍스트/헥스코드 오염 없음
- ❌ 3D 렌더링 느낌 없음

모두 ✅이면 → Task 3 (전체 캐릭터 생성)
하나라도 ❌이면 → Task 2 (SVG 폴백 분기)

---

## Task 2: [폴백] SVG 기반 캐릭터 — POC 실패 시만 실행

> POC(Task 1)가 성공하면 이 Task는 건너뜀.
> POC 실패 시: `svg_helpers.py`의 doodle_circle/doodle_rect으로 캐릭터를 프로그래매틱하게 그린다.

**Files:**
- Modify: `scripts/generate_branding/character_gen.py`

- [ ] **Step 1: CH1 stick figure 캐릭터 SVG 드로잉 함수 추가**

`character_gen.py` 하단에 추가:

```python
# ── SVG 폴백 캐릭터 (두들 stick figure) ──────────────────────────────

import sys
sys.path.insert(0, str(Path(__file__).parent))
from svg_helpers import (
    svg_open, svg_close, doodle_circle, doodle_rect, doodle_line
)

def draw_ch1_stick_figure(pose: str, out_path: Path) -> bool:
    """CH1 stick figure: 동그란 검정 머리 + 금관 + 막대몸통 + 흰 눈.
    
    pose: 'explain' | 'rich' | 'money' | 'lucky'
    """
    W, H = 512, 512
    BG = "#FFFDF5"
    INK = "#2C3E50"
    GOLD = "#F1C40F"

    # 기본 몸통 레이아웃
    head_cx, head_cy, head_r = 256, 160, 70    # 머리
    body_y1, body_y2 = 230, 370                 # 몸통 세로선
    arm_y = 280                                  # 팔 높이

    parts = [
        # 배경
        f'<rect width="{W}" height="{H}" fill="{BG}"/>',
        # 머리 (채워진 검정 원)
        f'<circle cx="{head_cx}" cy="{head_cy}" r="{head_r}" fill="{INK}"/>',
        # 눈 (흰 점 2개)
        f'<circle cx="{head_cx-25}" cy="{head_cy-10}" r="8" fill="white"/>',
        f'<circle cx="{head_cx+25}" cy="{head_cy-10}" r="8" fill="white"/>',
        # 금관 (삼각형 3개)
        f'<polygon points="{head_cx-40},{head_cy-65} {head_cx-30},{head_cy-90} {head_cx-20},{head_cy-65}" fill="{GOLD}" stroke="{INK}" stroke-width="3"/>',
        f'<polygon points="{head_cx-10},{head_cy-70} {head_cx},{head_cy-100} {head_cx+10},{head_cy-70}" fill="{GOLD}" stroke="{INK}" stroke-width="3"/>',
        f'<polygon points="{head_cx+20},{head_cy-65} {head_cx+30},{head_cy-90} {head_cx+40},{head_cy-65}" fill="{GOLD}" stroke="{INK}" stroke-width="3"/>',
        # W 글자 (관 중앙)
        f'<text x="{head_cx}" y="{head_cy-70}" font-family="Arial" font-weight="bold" font-size="20" fill="{INK}" text-anchor="middle">W</text>',
        # 미소
        f'<path d="M {head_cx-20},{head_cy+20} Q {head_cx},{head_cy+40} {head_cx+20},{head_cy+20}" fill="none" stroke="white" stroke-width="4" stroke-linecap="round"/>',
        # 몸통 세로선
        doodle_line(head_cx, body_y1, head_cx, body_y2, INK, sw=5),
        # 다리
        doodle_line(head_cx, body_y2, head_cx-50, H-80, INK, sw=5),
        doodle_line(head_cx, body_y2, head_cx+50, H-80, INK, sw=5),
    ]

    # 포즈별 팔 + 소품
    if pose == "explain":
        # 왼팔 내림, 오른팔 위 (설명 제스처)
        parts += [
            doodle_line(head_cx, arm_y, head_cx-70, arm_y+40, INK, sw=5),
            doodle_line(head_cx, arm_y, head_cx+70, arm_y-40, INK, sw=5),
            # 오른손 검지
            doodle_line(head_cx+70, arm_y-40, head_cx+85, arm_y-70, INK, sw=4),
        ]
    elif pose == "rich":
        # 양팔 내려 돈주머니 들기
        parts += [
            doodle_line(head_cx, arm_y, head_cx-80, arm_y+30, INK, sw=5),
            doodle_line(head_cx, arm_y, head_cx+80, arm_y+30, INK, sw=5),
            # 돈주머니 (원 + $ 기호)
            f'<circle cx="{head_cx-100}" cy="{arm_y+55}" r="25" fill="{GOLD}" stroke="{INK}" stroke-width="3"/>',
            f'<text x="{head_cx-100}" y="{arm_y+63}" font-family="Arial" font-weight="bold" font-size="22" fill="{INK}" text-anchor="middle">$</text>',
            f'<circle cx="{head_cx+100}" cy="{arm_y+55}" r="25" fill="{GOLD}" stroke="{INK}" stroke-width="3"/>',
            f'<text x="{head_cx+100}" y="{arm_y+63}" font-family="Arial" font-weight="bold" font-size="22" fill="{INK}" text-anchor="middle">$</text>',
        ]
    elif pose == "money":
        # 양팔 위로 (신남)
        parts += [
            doodle_line(head_cx, arm_y, head_cx-80, arm_y-60, INK, sw=5),
            doodle_line(head_cx, arm_y, head_cx+80, arm_y-60, INK, sw=5),
            # 날아다니는 지폐 3장
            f'<rect x="130" y="200" width="40" height="20" rx="3" fill="{GOLD}" stroke="{INK}" stroke-width="2" transform="rotate(-15,150,210)"/>',
            f'<rect x="320" y="190" width="40" height="20" rx="3" fill="{GOLD}" stroke="{INK}" stroke-width="2" transform="rotate(10,340,200)"/>',
            f'<rect x="160" y="130" width="40" height="20" rx="3" fill="{GOLD}" stroke="{INK}" stroke-width="2" transform="rotate(5,180,140)"/>',
        ]
    else:  # lucky
        # 한손 복권, 깜짝 표정 (눈 크게)
        parts += [
            doodle_line(head_cx, arm_y, head_cx-70, arm_y+20, INK, sw=5),
            doodle_line(head_cx, arm_y, head_cx+80, arm_y-20, INK, sw=5),
            # 복권 카드
            f'<rect x="{head_cx+85}" y="{arm_y-50}" width="50" height="70" rx="5" fill="white" stroke="{INK}" stroke-width="3"/>',
            f'<text x="{head_cx+110}" y="{arm_y}" font-family="Arial" font-size="14" fill="{INK}" text-anchor="middle">당첨</text>',
            # 별 반짝이 2개
            f'<text x="180" y="120" font-size="28">✦</text>',
            f'<text x="330" y="150" font-size="20">✦</text>',
        ]

    svg = svg_open(W, H, bg_color="none") + "".join(parts) + svg_close()

    # PNG 변환 (cairosvg 또는 Pillow fallback)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    svg_path = out_path.with_suffix(".svg")
    svg_path.write_text(svg, encoding="utf-8")

    try:
        import cairosvg
        cairosvg.svg2png(url=str(svg_path), write_to=str(out_path), scale=2.0)
        logger.info(f"[SVG→PNG] {out_path.name} (cairosvg)")
        return True
    except ImportError:
        # cairosvg 없으면 SVG 그대로 저장 (PNG 변환 실패)
        logger.warning(f"[SVG 저장] cairosvg 미설치 — PNG 변환 불가: {svg_path.name}")
        return False
```

- [ ] **Step 2: SVG 폴백 테스트**

```bash
python -c "
from pathlib import Path
from scripts.generate_branding.character_gen import draw_ch1_stick_figure
for pose in ['explain','rich','money','lucky']:
    ok = draw_ch1_stick_figure(pose, Path(f'assets/channels/CH1/characters/character_{pose}_svg.png'))
    print(f'{pose}: {\"OK\" if ok else \"FAIL\"}')
"
```

Expected: 4개 파일 생성 또는 SVG 저장

- [ ] **Step 3: 커밋**

```bash
git add scripts/generate_branding/nano_banana_helper.py scripts/generate_branding/character_gen.py
git commit -m "feat(branding): Gemini 멀티모달 캐릭터 생성 + SVG stick figure 폴백"
```

---

## Task 3: 전체 CH1 캐릭터 라이브러리 생성 (POC 통과 후)

**Files:**
- Modify: `scripts/generate_branding/character_gen.py`

- [ ] **Step 1: character_gen.py에 멀티모달 분기 추가**

`generate_character()` 함수 상단에 분기 삽입:

```python
def generate_character(
    client: genai.Client, ch_id: str, pose_key: str
) -> bool:
    cfg = CHANNELS[ch_id]
    prompt = cfg["character_prompts"][pose_key]
    out_path = CHANNELS_DIR / ch_id / "characters" / f"character_{pose_key}.png"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    # CH1: Gemini 멀티모달 (reference 이미지 입력)
    if ch_id == "CH1":
        from nano_banana_helper import generate_with_reference
        reference = KAS_ROOT / "essential_branding" / "CH1.png"
        return generate_with_reference(reference, prompt, out_path, client=None)

    # CH2~7: 기존 Imagen 4.0 경로 유지
    try:
        result = client.models.generate_images(
            model=MODEL,
            prompt=prompt,
            config=types.GenerateImagesConfig(number_of_images=1, aspect_ratio="1:1"),
        )
        image_bytes = result.generated_images[0].image.image_bytes
        out_path.write_bytes(image_bytes)
        logger.info(f"[OK] {ch_id}/{pose_key} -> {len(image_bytes):,} bytes")
        return True
    except Exception as e:
        logger.error(f"[ERR] {ch_id}/{pose_key}: {e}")
        return False
```

- [ ] **Step 2: 전체 CH1 캐릭터 4종 생성**

```bash
cd C:\Users\조찬우\Desktop\ai_stuidio_claude
python scripts/generate_branding/character_gen.py --channel CH1
```

Expected: `assets/channels/CH1/characters/` 에 character_explain/rich/money/lucky.png 4종 생성

- [ ] **Step 3: 텍스트 오염 자동 검사**

```python
# 텍스트 오염 확인: 이미지 픽셀 분포로 간접 측정
from PIL import Image
import numpy as np
from pathlib import Path

for name in ["explain","rich","money","lucky"]:
    img = Image.open(f"assets/channels/CH1/characters/character_{name}.png").convert("RGB")
    arr = np.array(img)
    # 순수 검정(0,0,0 ±30) 픽셀 비율 — 텍스트 오염 시 증가
    dark = np.sum((arr < 30).all(axis=2)) / (arr.shape[0]*arr.shape[1])
    print(f"{name}: dark_ratio={dark:.4f} {'⚠️ 텍스트 의심' if dark > 0.15 else '✅'}")
```

- [ ] **Step 4: 테스트 실행**

```bash
pytest tests/test_branding_assets.py -v -k "character"
```

Expected: character 관련 테스트 전체 PASS

- [ ] **Step 5: 커밋**

```bash
git add assets/channels/CH1/characters/ scripts/generate_branding/character_gen.py
git commit -m "feat(ch1): Gemini 멀티모달 캐릭터 4종 생성 완료"
```

---

## Task 4: style_guide_loader.py + manifest.json

**목표:** CH1.png 레퍼런스 분석 결과를 JSON으로 저장해 다른 자산 생성 시 참고.

**Files:**
- Create: `scripts/generate_branding/style_guide_loader.py`
- Create: `assets/channels/CH1/manifest.json`

- [ ] **Step 1: style_guide_loader.py 작성**

```python
# scripts/generate_branding/style_guide_loader.py
"""essential_branding/CH*.png에서 스타일 가이드를 추출해 manifest.json에 저장."""
import json
from pathlib import Path

import numpy as np
from PIL import Image


def extract_dominant_colors(image_path: Path, n: int = 5) -> list[str]:
    """이미지에서 상위 n개 색상 추출 (hex 문자열 반환)."""
    img = Image.open(image_path).convert("RGB")
    arr = np.array(img).reshape(-1, 3)
    # 간단 k-means 대신 히스토그램 방식
    from collections import Counter
    # 8-bit 양자화
    quantized = (arr // 32) * 32
    counts = Counter(map(tuple, quantized))
    top = counts.most_common(n + 10)
    # 흰색/거의흰색 제거
    filtered = [(c, cnt) for c, cnt in top if not all(v > 230 for v in c)]
    return [f"#{r:02X}{g:02X}{b:02X}" for (r, g, b), _ in filtered[:n]]


def build_style_guide(ch_id: str, reference_path: Path, config: dict) -> dict:
    """채널 설정 + 레퍼런스 이미지 분석 → style guide dict."""
    dominant = extract_dominant_colors(reference_path)
    return {
        "channel_id": ch_id,
        "channel_name": config["name"],
        "domain": config["domain"],
        "palette": {
            "main": config["main_color"],
            "bg": config["bg_color"],
            "sub": config["sub_colors"],
            "stroke": config["stroke_color"],
            "dominant_from_reference": dominant,
        },
        "stroke": {"width_px": "2-3", "style": "hand-drawn marker"},
        "line_quality": "wobbly, slightly irregular bezier",
        "shading": "flat, no gradients, no drop shadows",
        "reference_image": str(reference_path),
        "assets": {
            "characters": [f"character_{c}.png" for c in config["characters"]],
            "categories": [
                "branding", "characters", "icons", "intro_outro",
                "transitions", "annotations", "data_viz", "maps", "meta"
            ],
        },
    }


def save_manifest(ch_id: str, out_dir: Path, config: dict, reference_path: Path) -> Path:
    guide = build_style_guide(ch_id, reference_path, config)
    out_path = out_dir / ch_id / "manifest.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(guide, ensure_ascii=False, indent=2), encoding="utf-8")
    return out_path
```

- [ ] **Step 2: manifest 생성 실행**

```python
# 터미널에서 직접 실행
python -c "
from pathlib import Path
from scripts.generate_branding.style_guide_loader import save_manifest
from scripts.generate_branding.config import CHANNELS, CHANNELS_DIR, BRANDING_REF_DIR

path = save_manifest(
    'CH1',
    CHANNELS_DIR,
    CHANNELS['CH1'],
    BRANDING_REF_DIR / 'CH1.png'
)
print(f'manifest 저장: {path}')
"
```

- [ ] **Step 3: manifest 내용 확인**

```bash
cat assets/channels/CH1/manifest.json
```

Expected: `palette`, `stroke`, `assets` 키 포함 JSON

- [ ] **Step 4: 커밋**

```bash
git add scripts/generate_branding/style_guide_loader.py assets/channels/CH1/manifest.json
git commit -m "feat(ch1): style_guide_loader + manifest.json — CH1 스타일 가이드 추출"
```

---

## Task 5: 레거시 Imagen 파일 정리

**Files:**
- Delete: `scripts/generate_branding/imagen_2k_helper.py`
- Delete: `scripts/generate_branding/ch1_imagen_surfaces.py`
- Delete: `scripts/generate_branding/ch1_gemini_svg.py`
- Keep: `scripts/generate_branding/ch1_svg_rasterize.py` (SVG 폴백 보존)

- [ ] **Step 1: 폐기 대상 파일이 다른 파일에서 import되는지 확인**

```bash
grep -r "imagen_2k_helper\|ch1_imagen_surfaces\|ch1_gemini_svg" \
  scripts/generate_branding/ --include="*.py" -l
```

Expected: `character_gen.py`만 `imagen_2k_helper` import

- [ ] **Step 2: character_gen.py import 수정**

`character_gen.py` 상단의 import 교체:

```python
# 삭제:
# from imagen_2k_helper import BudgetExceededError, generate_best_of_n

# 유지 (필요 시):
# from nano_banana_helper import generate_with_reference
```

- [ ] **Step 3: 레거시 파일 삭제**

```bash
cd C:\Users\조찬우\Desktop\ai_stuidio_claude
git rm scripts/generate_branding/imagen_2k_helper.py
git rm scripts/generate_branding/ch1_imagen_surfaces.py
git rm scripts/generate_branding/ch1_gemini_svg.py
```

- [ ] **Step 4: 전체 테스트 통과 확인**

```bash
pytest tests/ -q --ignore=tests/test_step08.py
```

Expected: 이전과 동일한 통과 수 (레거시 삭제로 인한 회귀 없음)

- [ ] **Step 5: 커밋**

```bash
git commit -m "refactor(branding): 레거시 Imagen 4.0 파일 폐기 — nano_banana 분기로 대체"
```

---

## 검증 체크리스트

| # | 항목 | 명령 | 기준 |
|---|---|---|---|
| 1 | POC 성공 | `assets/channels/CH1/characters/character_explain_poc.png` 존재 | 두들 스타일 사용자 OK |
| 2 | 캐릭터 4종 | `pytest tests/test_branding_assets.py -k character -v` | ALL PASS |
| 3 | 텍스트 오염 | dark_ratio ≤ 0.15 | 전체 4종 |
| 4 | manifest.json | 파일 존재 + `palette.main = "#2ECC71"` | JSON parse OK |
| 5 | 레거시 정리 | `ls scripts/generate_branding/imagen_2k_helper.py` | NOT FOUND |
| 6 | 전체 테스트 | `pytest tests/ -q --ignore=tests/test_step08.py` | 이전 동일 수 |

---

## 다음 서브플랜 (이 문서 완료 후)

- **서브플랜 B**: 프로그래매틱 자산 (로고·아이콘·말풍선·데이터 비주얼·지도) — Inkscape CLI + drawSvg
- **서브플랜 C**: 모션 자산 + 파이프라인 통합 (인트로·아웃트로·전환·src/step08/)
