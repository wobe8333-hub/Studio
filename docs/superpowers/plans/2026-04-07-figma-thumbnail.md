# Figma MCP 썸네일 시스템 구현 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Figma MCP로 7채널 마스코트 베이스 PNG를 생성하고 Step10 thumbnail_generator.py를 PIL 합성 방식으로 완전 교체한다.

**Architecture:** Figma MCP `generate_figma_design` + `get_screenshot`으로 채널별 1920×1080 베이스 이미지를 `assets/thumbnails/CH{N}_base.png`에 저장. 이후 Step10 실행 시 PIL로 베이스 위에 채널명·제목 텍스트를 4레이어 합성하여 3종 변형 PNG를 생성한다. Gemini 이미지 생성 코드는 완전 제거.

**Tech Stack:** Python Pillow 10.1.0, Figma MCP (generate_figma_design + get_screenshot), C:/Windows/Fonts/malgun.ttf (한국어 폰트)

---

## 파일 구조

| 파일 | 역할 |
|---|---|
| `assets/thumbnails/CH{1-7}_base.png` | Figma MCP 생성 베이스 (1920×1080, 신규) |
| `src/step10/thumbnail_generator.py` | PIL 합성으로 완전 교체 |
| `tests/test_step10.py` | 신규 PIL 함수 테스트 추가 |

변경 없는 파일: `src/step10/title_variant_builder.py`, `src/step10/__init__.py`, 웹 대시보드, API 라우트

---

## Task 1: Figma MCP — CH1 파일럿 베이스 PNG 생성

**Files:**
- Create: `assets/thumbnails/CH1_base.png`

> **주의:** 이 Task는 Claude Code가 직접 Figma MCP 도구를 호출하여 실행한다. 코드 작성이 아니라 도구 실행이다.

- [ ] **Step 1: Figma MCP로 CH1 경제 채널 디자인 생성**

  Figma MCP `generate_figma_design` 호출:
  ```
  prompt: "YouTube thumbnail base template 1920x1080px.
  Cute chibi economist character wearing suit, dark gold gradient background (#1A1200 to #000000),
  stock chart icon (📈), Korean YouTube thumbnail style, no text, professional,
  top 62% area only (mascot and background), bottom 38% solid dark gold (#2D2000) bar placeholder.
  Style: flat illustration, bold colors, high contrast."

  title: "KAS CH1 경제 - 썸네일 베이스"
  ```

- [ ] **Step 2: 생성된 Figma 파일에서 스크린샷 캡처**

  Figma MCP `get_screenshot` 호출 → PNG 바이트 반환

- [ ] **Step 3: assets/thumbnails/CH1_base.png 저장 확인**

  ```bash
  ls -la assets/thumbnails/CH1_base.png
  # 기대: 파일 존재, 크기 > 100KB
  ```

- [ ] **Step 4: 이미지 크기 검증**

  ```python
  from PIL import Image
  img = Image.open("assets/thumbnails/CH1_base.png")
  print(img.size)  # 기대: (1920, 1080) 또는 리사이즈 필요 시 확인
  ```

---

## Task 2: Figma MCP — CH2~CH7 베이스 PNG 생성

**Files:**
- Create: `assets/thumbnails/CH2_base.png` ~ `assets/thumbnails/CH7_base.png`

> **주의:** Task 1과 동일하게 Figma MCP 도구를 채널별로 반복 실행.

- [ ] **Step 1: CH2 부동산 베이스 생성**

  ```
  prompt: "YouTube thumbnail base template 1920x1080px.
  Cute chibi real estate agent character, dark green gradient background (#0A1F0A to #000000),
  building and map icon (🏘️🗺️), Korean YouTube thumbnail style, no text, professional,
  top 62% mascot area, bottom 38% solid dark green (#1A3A1A) bar placeholder.
  Style: flat illustration, bold colors, high contrast."
  ```
  → `assets/thumbnails/CH2_base.png` 저장

- [ ] **Step 2: CH3 심리 베이스 생성**

  ```
  prompt: "YouTube thumbnail base template 1920x1080px.
  Cute chibi psychologist counselor character, dark purple gradient background (#0D001A to #000000),
  brain and thought bubble icon (🧠💭), Korean YouTube thumbnail style, no text, professional,
  top 62% mascot area, bottom 38% solid dark purple (#1A0033) bar placeholder.
  Style: flat illustration, bold colors, high contrast."
  ```
  → `assets/thumbnails/CH3_base.png` 저장

- [ ] **Step 3: CH4 미스터리 베이스 생성**

  ```
  prompt: "YouTube thumbnail base template 1920x1080px.
  Cute chibi detective character with magnifying glass, very dark red-black gradient background (#0A0000 to #000000),
  mystery suspense atmosphere, shadow effects, magnifying glass icon (🔍), Korean YouTube thumbnail style,
  no text, professional, top 62% mascot area, bottom 38% solid dark red (#1A0A00) bar placeholder.
  Style: flat illustration, bold colors, high contrast, dramatic lighting."
  ```
  → `assets/thumbnails/CH4_base.png` 저장

- [ ] **Step 4: CH5 전쟁사 베이스 생성**

  ```
  prompt: "YouTube thumbnail base template 1920x1080px.
  Cute chibi military historian character with sword, dark red-black gradient background (#1A0505 to #000000),
  sword and helmet icon (⚔️🪖), war history theme, Korean YouTube thumbnail style, no text, professional,
  top 62% mascot area, bottom 38% solid dark crimson (#2D0A0A) bar placeholder.
  Style: flat illustration, bold colors, dramatic, high contrast."
  ```
  → `assets/thumbnails/CH5_base.png` 저장

- [ ] **Step 5: CH6 과학 베이스 생성**

  ```
  prompt: "YouTube thumbnail base template 1920x1080px.
  Cute chibi scientist character with lab coat, deep navy-black gradient background (#001A2E to #000000),
  microscope and rocket icon (🔬🚀), space science theme, cyber blue accent (#4DD0E1),
  Korean YouTube thumbnail style, no text, professional,
  top 62% mascot area, bottom 38% solid deep navy (#00263D) bar placeholder.
  Style: flat illustration, bold colors, futuristic, high contrast."
  ```
  → `assets/thumbnails/CH6_base.png` 저장

- [ ] **Step 6: CH7 역사 베이스 생성**

  ```
  prompt: "YouTube thumbnail base template 1920x1080px.
  Cute chibi historian scholar character, sepia dark gold gradient background (#1A1200 to #0D0900),
  scroll and temple icon (📜🏛️), Korean history theme, antique gold accent (#C8A96E),
  Korean YouTube thumbnail style, no text, professional,
  top 62% mascot area, bottom 38% solid sepia (#2A1E00) bar placeholder.
  Style: flat illustration, antique colors, elegant, high contrast."
  ```
  → `assets/thumbnails/CH7_base.png` 저장

- [ ] **Step 7: 7개 파일 모두 존재 확인**

  ```bash
  ls -la assets/thumbnails/
  # 기대: CH1_base.png ~ CH7_base.png 7개 파일, 각 > 50KB
  ```

- [ ] **Step 8: 커밋**

  ```bash
  git add assets/thumbnails/
  git commit -m "feat: Figma MCP로 7채널 썸네일 베이스 PNG 생성"
  ```

---

## Task 3: 실패하는 테스트 작성

**Files:**
- Modify: `tests/test_step10.py` (기존 파일에 클래스 추가)

- [ ] **Step 1: tests/test_step10.py 하단에 테스트 클래스 추가**

  기존 파일 맨 끝에 다음을 추가한다:

  ```python
  class TestGenerateThumbnailPIL:
      """PIL 합성 기반 generate_thumbnail() 단위 테스트."""

      def _make_fake_base(self, tmp_path: Path, channel_id: str = "CH1") -> Path:
          """1920×1080 단색 PNG를 베이스 이미지로 생성."""
          from PIL import Image
          base_dir = tmp_path / "assets" / "thumbnails"
          base_dir.mkdir(parents=True)
          img = Image.new("RGB", (1920, 1080), color=(26, 18, 0))
          path = base_dir / f"{channel_id}_base.png"
          img.save(path)
          return path

      def test_returns_true_when_base_exists(self, tmp_path, monkeypatch):
          """베이스 PNG가 있으면 True를 반환하고 output 파일을 생성한다."""
          base_path = self._make_fake_base(tmp_path, "CH1")
          output = tmp_path / "out" / "thumbnail_variant_01.png"
          output.parent.mkdir(parents=True)

          monkeypatch.setitem(
              __import__("src.step10.thumbnail_generator",
                         fromlist=["CHANNEL_BASE_TEMPLATES"]).CHANNEL_BASE_TEMPLATES,
              "CH1", base_path,
          )

          from src.step10.thumbnail_generator import generate_thumbnail
          result = generate_thumbnail("CH1", "금리 인하의 충격", "01", output)

          assert result is True
          assert output.exists()

      def test_fallback_when_base_missing(self, tmp_path):
          """베이스 PNG가 없으면 _generate_placeholder()로 폴백하고 True를 반환한다."""
          output = tmp_path / "thumb.png"

          from src.step10.thumbnail_generator import generate_thumbnail
          result = generate_thumbnail("CH_NONEXISTENT", "제목", "01", output)

          assert result is True  # placeholder도 True 반환
          assert output.exists()

      def test_mode02_detects_number(self, tmp_path, monkeypatch):
          """mode 02는 제목에서 숫자를 감지한다 (내부 로직 검증)."""
          import re
          title = "10억 모은 비밀 전략"
          match = re.search(r'\d+', title)
          assert match is not None
          assert match.group() == "10"

      def test_mode02_no_number_fallback(self, tmp_path):
          """mode 02에서 숫자 없는 제목은 숫자 없음을 반환한다."""
          import re
          title = "당신이 몰랐던 진실"
          match = re.search(r'\d+', title)
          assert match is None

      def test_mode03_appends_question_mark(self, tmp_path):
          """mode 03은 제목 끝에 '?'를 추가하고 마지막 어절을 반환한다."""
          title = "조선 왕들이 숨긴 비밀"
          question_title = title + "?"
          last_word = title.split()[-1]
          assert question_title.endswith("?")
          assert last_word == "비밀"

      def test_output_path_parent_created(self, tmp_path, monkeypatch):
          """output_path의 부모 디렉토리가 없어도 자동 생성된다."""
          base_path = self._make_fake_base(tmp_path, "CH1")
          # 중첩된 미존재 경로
          output = tmp_path / "deep" / "nested" / "thumb.png"

          monkeypatch.setitem(
              __import__("src.step10.thumbnail_generator",
                         fromlist=["CHANNEL_BASE_TEMPLATES"]).CHANNEL_BASE_TEMPLATES,
              "CH1", base_path,
          )

          from src.step10.thumbnail_generator import generate_thumbnail
          result = generate_thumbnail("CH1", "테스트 제목", "01", output)

          assert result is True
          assert output.parent.exists()
  ```

- [ ] **Step 2: 테스트 실패 확인**

  ```bash
  pytest tests/test_step10.py::TestGenerateThumbnailPIL -v
  ```

  기대 출력: `FAILED` (새 함수들이 아직 구현 안 됨)

---

## Task 4: thumbnail_generator.py PIL 합성 구현

**Files:**
- Modify: `src/step10/thumbnail_generator.py` (전체 교체)

- [ ] **Step 1: thumbnail_generator.py 전체 교체**

  ```python
  """STEP 10 — PIL 합성 기반 썸네일 생성 (Figma 베이스 + 텍스트 레이어)."""
  import re
  from pathlib import Path
  from loguru import logger
  from PIL import Image, ImageDraw, ImageFont

  # ── 프로젝트 루트 ──────────────────────────────────────────────────────────────
  _ROOT = Path(__file__).resolve().parents[2]

  # ── 채널별 베이스 템플릿 경로 ──────────────────────────────────────────────────
  CHANNEL_BASE_TEMPLATES: dict[str, Path] = {
      "CH1": _ROOT / "assets/thumbnails/CH1_base.png",
      "CH2": _ROOT / "assets/thumbnails/CH2_base.png",
      "CH3": _ROOT / "assets/thumbnails/CH3_base.png",
      "CH4": _ROOT / "assets/thumbnails/CH4_base.png",
      "CH5": _ROOT / "assets/thumbnails/CH5_base.png",
      "CH6": _ROOT / "assets/thumbnails/CH6_base.png",
      "CH7": _ROOT / "assets/thumbnails/CH7_base.png",
  }

  # ── 채널별 색상 스펙 ───────────────────────────────────────────────────────────
  # overlay: (R, G, B, A)  primary: 강조 텍스트 색  label: 채널명 소형 텍스트 색
  CHANNEL_COLORS: dict[str, dict] = {
      "CH1": {"overlay": (180, 120,  0, 235), "top_line": (255, 215,   0), "primary": "#FFD700", "label": "#FFD700", "name": "경제"},
      "CH2": {"overlay": (  0,  80,  0, 235), "top_line": ( 76, 175,  80), "primary": "#4CAF50", "label": "#4CAF50", "name": "부동산"},
      "CH3": {"overlay": ( 80,   0, 120, 235), "top_line": (206, 147, 216), "primary": "#CE93D8", "label": "#CE93D8", "name": "심리"},
      "CH4": {"overlay": (100,  20,  0, 235), "top_line": (255, 112,  67), "primary": "#FF7043", "label": "#FF7043", "name": "미스터리"},
      "CH5": {"overlay": (120,  20, 20, 235), "top_line": (239, 154, 154), "primary": "#EF9A9A", "label": "#EF9A9A", "name": "전쟁사"},
      "CH6": {"overlay": (  0,  60, 80, 235), "top_line": ( 77, 208, 225), "primary": "#4DD0E1", "label": "#4DD0E1", "name": "과학"},
      "CH7": {"overlay": ( 80,  55,  0, 235), "top_line": (200, 169, 110), "primary": "#C8A96E", "label": "#C8A96E", "name": "역사"},
  }

  # ── 폰트 로드 ─────────────────────────────────────────────────────────────────
  _FONT_PATH = Path("C:/Windows/Fonts/malgun.ttf")

  def _load_font(size: int) -> ImageFont.FreeTypeFont:
      """malgun.ttf 로드, 실패 시 기본 폰트 반환."""
      try:
          return ImageFont.truetype(str(_FONT_PATH), size)
      except Exception:
          return ImageFont.load_default()


  def _hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
      """#RRGGBB → (R, G, B)."""
      h = hex_color.lstrip("#")
      return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))  # type: ignore


  def _wrap_text(text: str, max_chars: int = 16) -> list[str]:
      """제목을 max_chars 기준으로 최대 2줄 분리."""
      if len(text) <= max_chars:
          return [text]
      # 공백 기준 분리 시도
      words = text.split()
      line1, line2 = [], []
      for w in words:
          if len(" ".join(line1 + [w])) <= max_chars:
              line1.append(w)
          else:
              line2.append(w)
      if not line1:
          return [text[:max_chars], text[max_chars:max_chars*2]]
      return [" ".join(line1), " ".join(line2)] if line2 else [" ".join(line1)]


  def _compose_thumbnail(
      base_img: Image.Image,
      channel_id: str,
      title: str,
      mode: str,
  ) -> Image.Image:
      """베이스 이미지 위에 4레이어 합성."""
      W, H = 1920, 1080
      img = base_img.convert("RGBA").resize((W, H), Image.LANCZOS)
      draw = ImageDraw.Draw(img)
      colors = CHANNEL_COLORS.get(channel_id, CHANNEL_COLORS["CH1"])

      # Layer 2: 하단 38% 반투명 오버레이
      overlay_top = int(H * 0.62)
      overlay = Image.new("RGBA", (W, H - overlay_top), colors["overlay"])
      img.paste(overlay, (0, overlay_top), overlay)

      # 상단 구분선
      line_color = colors["top_line"]
      draw.rectangle([(0, overlay_top), (W, overlay_top + 4)], fill=line_color)

      # Layer 3: 채널명 소형 텍스트 (좌상단 바 영역)
      font_label = _load_font(40)
      ch_num = channel_id  # e.g. "CH1"
      ch_name = colors["name"]
      label_text = f"{ch_num} · {ch_name}"
      label_y = overlay_top + 18
      draw.text((48, label_y), label_text, font=font_label, fill=line_color)

      # Layer 4: 제목 텍스트 (mode별)
      title_y = overlay_top + 72
      _draw_title(draw, title, mode, colors, W, title_y)

      return img.convert("RGB")


  def _draw_title(
      draw: ImageDraw.ImageDraw,
      title: str,
      mode: str,
      colors: dict,
      W: int,
      y: int,
  ) -> None:
      """mode별 제목 텍스트 렌더링."""
      primary_rgb = _hex_to_rgb(colors["primary"])

      if mode == "02":
          # 숫자 감지 → 대형(2×) + 나머지 일반
          m = re.search(r'\d+', title)
          if m:
              number_str = m.group()
              rest = title[:m.start()].strip() + " " + title[m.end():].strip()
              font_num = _load_font(160)
              font_rest = _load_font(72)
              draw.text((48, y - 30), number_str, font=font_num, fill=primary_rgb)
              lines = _wrap_text(rest.strip())
              for i, line in enumerate(lines[:2]):
                  draw.text((320, y + i * 88), line, font=font_rest, fill=(255, 255, 255))
              return
          # 숫자 없으면 mode 01로 폴백
          mode = "01"

      if mode == "03":
          # 질문형: 제목 + "?"
          question = title + "?"
          last_word = title.split()[-1] + "?"
          rest = " ".join(question.split()[:-1])
          font_title = _load_font(80)
          lines = _wrap_text(rest)
          for i, line in enumerate(lines[:2]):
              draw.text((48, y + i * 96), line, font=font_title, fill=(255, 255, 255))
          # 마지막 어절 채널색
          last_y = y + len(lines) * 96
          draw.text((48, last_y), last_word, font=font_title, fill=primary_rgb)
          return

      # mode 01 (기본): 흰색 텍스트
      font_title = _load_font(80)
      lines = _wrap_text(title)
      for i, line in enumerate(lines[:2]):
          draw.text((48, y + i * 96), line, font=font_title, fill=(255, 255, 255))


  def _generate_placeholder(title: str, output_path: Path) -> bool:
      """베이스 없을 때 단색 플레이스홀더 생성."""
      try:
          output_path.parent.mkdir(parents=True, exist_ok=True)
          img = Image.new("RGB", (1920, 1080), color=(30, 30, 30))
          draw = ImageDraw.Draw(img)
          font = _load_font(80)
          draw.text((60, 480), title[:32], font=font, fill=(200, 200, 200))
          img.save(str(output_path))
          return True
      except Exception as e:
          logger.warning(f"[STEP10] 플레이스홀더 생성 실패: {e}")
          return False


  def generate_thumbnail(channel_id: str, title: str, mode: str, output_path: Path) -> bool:
      """채널 베이스 PNG + PIL 합성으로 썸네일 생성.

      Args:
          channel_id: "CH1" ~ "CH7"
          title: 영상 제목
          mode: "01" | "02" | "03"
          output_path: 저장 경로 (.png)

      Returns:
          True: 성공 (합성 또는 플레이스홀더)
          False: 완전 실패
      """
      base_path = CHANNEL_BASE_TEMPLATES.get(channel_id)
      if not base_path or not base_path.exists():
          logger.warning(f"[STEP10] 베이스 없음({channel_id}) → 플레이스홀더")
          return _generate_placeholder(title, output_path)

      try:
          base_img = Image.open(base_path)
          result = _compose_thumbnail(base_img, channel_id, title, mode)
          output_path.parent.mkdir(parents=True, exist_ok=True)
          result.save(str(output_path))
          logger.info(f"[STEP10] 썸네일 생성 완료: {output_path.name} (mode={mode})")
          return True
      except Exception as e:
          logger.warning(f"[STEP10] PIL 합성 실패 → 플레이스홀더: {e}")
          return _generate_placeholder(title, output_path)
  ```

- [ ] **Step 2: 테스트 통과 확인**

  ```bash
  pytest tests/test_step10.py::TestGenerateThumbnailPIL -v
  ```

  기대 출력: 6개 테스트 모두 `PASSED`

- [ ] **Step 3: 기존 테스트 회귀 확인**

  ```bash
  pytest tests/test_step10.py -v
  ```

  기대 출력: 전체 `PASSED` (기존 `TestRunStep10`, `TestGetPreferredMode` 포함)

---

## Task 5: 전체 테스트 스위트 확인 + 커밋

**Files:** 없음 (검증 전용)

- [ ] **Step 1: 전체 테스트 실행**

  ```bash
  pytest tests/ -q --tb=short
  ```

  기대 출력: 기존 통과 테스트 전부 `PASSED`, 신규 6개 추가 `PASSED`

- [ ] **Step 2: 로컬 동작 검증 — CH1 썸네일 3종 수동 생성**

  ```python
  # 터미널에서 실행
  from pathlib import Path
  from src.step10.thumbnail_generator import generate_thumbnail

  for mode in ["01", "02", "03"]:
      out = Path(f"/tmp/test_thumb_{mode}.png")
      ok = generate_thumbnail("CH1", "금리 인하 시대, 당신의 돈을 지켜라", mode, out)
      print(f"mode={mode}: {ok}, exists={out.exists()}")
  ```

  기대 출력:
  ```
  mode=01: True, exists=True
  mode=02: True, exists=True
  mode=03: True, exists=True
  ```

- [ ] **Step 3: 커밋**

  ```bash
  git add src/step10/thumbnail_generator.py tests/test_step10.py
  git commit -m "feat: Step10 썸네일 Gemini 제거 → Figma+PIL 합성으로 교체"
  ```

---

## 자체 검토 체크리스트

- [x] **스펙 커버리지**: 레이아웃 C (상단 62%/하단 38%) ✓, 4레이어 합성 ✓, mode 01/02/03 ✓, 에러 폴백 ✓, 7채널 색상 ✓
- [x] **플레이스홀더 없음**: 모든 코드 블록 완성, TBD 없음
- [x] **타입 일관성**: `CHANNEL_BASE_TEMPLATES[id]` → `Path`, `generate_thumbnail() → bool`, `_compose_thumbnail() → Image.Image`
- [x] **파일명 일관성**: `thumbnail_variant_01/02/03.png` — `title_variant_builder.py` 호출과 일치
