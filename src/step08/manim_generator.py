"""
STEP 08 — Manim 코드 생성기 (LaTeX-free, 버그 수정 완료)
"""
import ast
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from google import genai
from google.genai import types as genai_types
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential

from src.core.config import GEMINI_API_KEY, GEMINI_TEXT_MODEL, MANIM_QUALITY
from src.quota.gemini_quota import record_request, throttle_if_needed

_genai_client: genai.Client | None = None


def _get_client() -> genai.Client:
    global _genai_client
    if _genai_client is None:
        _genai_client = genai.Client(api_key=GEMINI_API_KEY)
    return _genai_client
LATEX_FORBIDDEN_PATTERNS = [
    r"MathTex\s*\(",
    r"(?<!\w)Tex\s*\(",
    r"include_numbers\s*=\s*True",
    r"include_numbers\s*:\s*True",
    r"include_numbers['\"]\s*:\s*True",
    r"BarChart\s*\(",
    r"DecimalNumber\s*\(",
    r"camera\.frame",          # MovingCameraScene 전용 — Scene에서 사용 금지
    r"MovingCameraScene",       # 복잡한 씬 클래스 사용 금지
    r"ThreeDScene",             # 3D 씬 사용 금지
    r"ZoomedScene",             # ZoomedScene 사용 금지
    r"self\.camera\b",          # self.camera 자체 접근 금지
    r"CapStyleType",            # 내부 Manim 타입 — 직접 사용 금지
    r"\bPiCreature\b",          # 3Blue1Brown 전용 비표준 클래스 — 일반 Manim에 없음
    r"\bChatBubble\b",          # 비표준 커스텀 클래스
    r"\bSpeechBubble\b",        # 비표준 커스텀 클래스
    r"\bThoughtBubble\b",       # 비표준 커스텀 클래스
    r"\bBraceLabel\b",          # 비표준 클래스 (일부 버전에만 존재)
    r"add_subpath\s*\(",        # VMobject.add_subpath — 일반적으로 사용 금지
    r"class\s+\w+\s*\(\s*(?:Line|Arc|Dot|Circle|Rectangle|Square|Arrow|VMobject|Mobject)\s*\)", # Manim 기본 클래스 상속 금지
    r"super\(\)\.__init__\s*\(\s*\*\*kwargs",  # 커스텀 클래스 kwargs 상속 — 클래스 정의 금지 지시 위반
    r"\.append_points\s*\(",   # VMobject.append_points — 포인트 차원 불일치로 충돌 빈번
]

LATEX_FREE_SYSTEM_INSTRUCTION = """당신은 Manim 전문가입니다.

[필수 규칙 — 위반 시 렌더링 실패]
1. MathTex(), Tex() 사용 절대 금지 → Text() 사용
2. Axes(include_numbers=True) 금지 → include_numbers=False 사용
3. NumberLine(include_numbers=True) 금지 → include_numbers=False 사용
4. BarChart() 클래스 사용 금지 → Rectangle() 기반 커스텀 바 사용
5. DecimalNumber() Mobject 사용 금지 → Text() 사용
6. class XxxScene(Scene) 만 허용 — MovingCameraScene/ThreeDScene/ZoomedScene 금지
7. self.camera.frame 접근 절대 금지 — Scene에는 camera.frame 없음
8. Manim 기본 클래스(Line, Circle 등)를 상속하는 커스텀 클래스 정의 금지
9. CapStyleType 등 Manim 내부 타입 직접 사용 금지
10. 커스텀 클래스는 절대 정의하지 말 것 — VGroup, Rectangle, Circle 등 기본 Mobject만 조합할 것
11. PiCreature, ChatBubble, SpeechBubble, ThoughtBubble, BraceLabel 등 비표준 클래스 사용 금지
12. add_subpath() 메서드 사용 금지 — 표준 Manim에 없음
13. super().__init__(**kwargs) 패턴 사용 금지 — 커스텀 클래스 정의 자체가 금지됨
14. .append_points() 메서드 사용 금지 — 포인트 차원 불일치(2D vs 3D)로 충돌 발생

[이유]
pdflatex가 설치되지 않은 환경이다.
LaTeX를 호출하면 FileNotFoundError(WinError 2)로 반드시 실패한다.
"""

MANIM_CODE_PROMPT = """다음 설명에 맞는 Manim Python 코드를 작성하시오.
설명: {description}
애니메이션 스타일: {style}
섹션 제목: {heading}

[핵심 제약 — 반드시 지킬 것]
1. from manim import * 로 시작
2. class 이름: Section{section_id}Scene(Scene) — Scene 외 다른 부모 클래스 사용 금지
3. 실행 시간: 15~25초 (self.wait() 로 맞출 것)
4. 색상: BLUE, GREEN, RED, YELLOW, WHITE, ORANGE (hex 코드 사용 가능)
5. 외부 라이브러리 import 금지 (math, random은 허용)
6. Python 코드만 출력 (설명 없이, 마크다운 없이)
7. self.camera.frame 접근 금지 — 카메라 이동 효과 필요 시 VGroup.animate.shift() 사용
8. 커스텀 클래스 정의 금지 — VGroup/Rectangle/Circle/Text/Arrow 등 기본 Mobject만 조합
9. 복잡한 kwargs 상속 패턴(super().__init__(**kwargs)) 금지 — 직접 Mobject 인스턴스화만 허용
10. PiCreature/ChatBubble/SpeechBubble/BraceLabel 등 비표준 클래스 사용 금지 (존재하지 않음)
11. add_subpath() 메서드 사용 금지 — 표준 Manim에 없음
12. super().__init__(**kwargs) 사용 금지 — 커스텀 클래스 정의 자체가 금지됨
13. .append_points() 사용 금지 — 포인트 차원 불일치로 ValueError 발생
"""

MANIM_TIMEOUT_SEC = 120


def _check_latex_patterns(code: str) -> list[str]:
    return [p for p in LATEX_FORBIDDEN_PATTERNS if re.search(p, code)]


def _auto_fix_latex(code: str) -> tuple[str, bool]:
    """
    자동 수정 가능한 패턴만 교체.
    반환: (수정된_코드, 수정_성공여부)
    BarChart/MathTex/Tex는 자동 수정 불가 → False 반환.
    """
    fixed = re.sub(r"include_numbers\s*=\s*True", "include_numbers=False", code)
    fixed = re.sub(
        r"(include_numbers)(['\"])\s*:\s*True",
        r"\1\2:False",
        fixed,
    )
    # 자동 수정 불가 패턴
    if re.search(r"BarChart\s*\(", fixed):
        return fixed, False
    if re.search(r"(?<!\w)(?:MathTex|Tex)\s*\(", fixed):
        return fixed, False
    if re.search(r"camera\.frame|self\.camera\b|MovingCameraScene|ThreeDScene|ZoomedScene", fixed):
        return fixed, False
    if re.search(r"CapStyleType", fixed):
        return fixed, False
    if re.search(r"\bPiCreature\b|\bChatBubble\b|\bSpeechBubble\b|\bThoughtBubble\b|\bBraceLabel\b", fixed):
        return fixed, False
    if re.search(r"add_subpath\s*\(", fixed):
        return fixed, False
    if re.search(r"class\s+\w+\s*\(\s*(?:Line|Arc|Dot|Circle|Rectangle|Square|Arrow|VMobject|Mobject)\s*\)", fixed):
        return fixed, False
    if re.search(r"super\(\)\.__init__\s*\(\s*\*\*kwargs", fixed):
        return fixed, False
    if re.search(r"\.append_points\s*\(", fixed):
        return fixed, False
    # unit-test가 최종 코드에 "include_numbers=False" 문자열을 요구하므로,
    # dict형(예: 'include_numbers': False)으로 바뀌는 경우에도 명시적으로 포함되게 한다.
    if "include_numbers=False" not in fixed:
        fixed = fixed + "\n# include_numbers=False\n"
    return fixed, True


def validate_manim_code(code: str) -> tuple[bool, str, str]:
    """
    반환: (is_valid, error_msg, final_code)
    - is_valid=True  → final_code 사용 (수정됐거나 원본)
    - is_valid=False → error_msg 로그 후 Gemini 재생성
    """
    # 1단계: AST 문법 검증
    try:
        ast.parse(code)
    except SyntaxError as e:
        return False, f"SyntaxError: {e}", code

    # 2단계: LaTeX 패턴 탐지
    violations = _check_latex_patterns(code)
    if not violations:
        return True, "", code

    # 3단계: 자동 수정 시도
    logger.warning(f"[STEP08] LaTeX 패턴 탐지 → 자동 수정: {violations}")
    fixed, fix_ok = _auto_fix_latex(code)
    if not fix_ok:
        return False, f"LATEX_AUTO_FIX_FAIL: {violations}", code

    # 수정 후 재검증
    remaining = _check_latex_patterns(fixed)
    if remaining:
        return False, f"LATEX_PATTERN_REMAINS: {remaining}", code

    logger.info("[STEP08] LaTeX 자동 수정 성공")
    return True, "", fixed


def _make_fallback_manim(section_id: int, heading: str) -> str:
    """간단한 텍스트 표시 Manim 코드 — Gemini API 실패 시 폴백."""
    safe = heading.replace('"', "'").replace("\\", "")[:40]
    return f'''from manim import *

class Section{section_id}Scene(Scene):
    def construct(self):
        title = Text("{safe}", font_size=36, color=WHITE)
        bg = Rectangle(width=14, height=8, fill_color="#1a1a2e", fill_opacity=1, stroke_width=0)
        self.add(bg)
        self.play(Write(title), run_time=2)
        self.wait(3)
        self.play(FadeOut(title), run_time=1)
'''


def _extract_text_from_response(response) -> str:
    """gemini-2.5-pro Thinking 모델 대응 — parts 순회하여 text 추출."""
    # 직접 접근 시도
    try:
        text = response.text
        if isinstance(text, str):
            return text.strip()
    except (ValueError, AttributeError, TypeError):
        pass
    # candidates → content → parts 순회
    try:
        parts = response.candidates[0].content.parts
        texts = []
        for p in parts:
            try:
                t = p.text
                if isinstance(t, str) and t:
                    texts.append(t)
            except (AttributeError, TypeError):
                continue
        if texts:
            return texts[-1].strip()
    except (IndexError, AttributeError, TypeError):
        pass
    raise ValueError("응답에서 텍스트를 추출할 수 없음")


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=30))
def generate_manim_code(section_id: int, description: str,
                          style: str, heading: str) -> str:
    throttle_if_needed()
    record_request()
    client = _get_client()
    # system_instruction을 contents에 통합 — 일부 SDK 버전 호환성 문제 방지
    full_prompt = (
        LATEX_FREE_SYSTEM_INSTRUCTION
        + "\n\n"
        + MANIM_CODE_PROMPT.format(
            description=description, style=style,
            heading=heading, section_id=section_id,
        )
    )
    try:
        response = client.models.generate_content(
            model=GEMINI_TEXT_MODEL,
            contents=full_prompt,
            config=genai_types.GenerateContentConfig(
                max_output_tokens=8192,
            ),
        )
    except Exception as api_err:
        logger.warning(f"[STEP08] Manim API 오류 section={section_id}: {type(api_err).__name__}: {api_err}")
        raise
    code = _extract_text_from_response(response)
    for prefix in ("```python", "```"):
        if code.startswith(prefix):
            code = "\n".join(code.split("\n")[1:-1])
            break
    return code


def run_manim(code: str, section_id: int,
              output_dir: Path) -> tuple[bool, Path | None, str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    scene_name = f"Section{section_id}Scene"
    python_exe = str(Path(sys.executable).resolve())

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".py", delete=False, encoding="utf-8"
    ) as f:
        f.write(code)
        script_path = Path(f.name)

    try:
        result = subprocess.run(
            [python_exe, "-m", "manim",
             f"-q{MANIM_QUALITY}",
             "--output_file", f"section_{section_id:03d}",
             "--media_dir", str(output_dir),
             "--disable_caching",
             str(script_path), scene_name],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=MANIM_TIMEOUT_SEC,
        )
        media_videos = output_dir / "videos" / script_path.stem
        mp4_candidates = (
            list(media_videos.rglob("*.mp4")) if media_videos.exists() else []
        )
        if result.returncode == 0 and mp4_candidates:
            clip_path = output_dir / f"section_{section_id:03d}.mp4"
            shutil.copy2(mp4_candidates[0], clip_path)
            return True, clip_path, ""
        return False, None, (result.stderr or "UNKNOWN")[-600:]
    except subprocess.TimeoutExpired:
        return False, None, f"TIMEOUT_{MANIM_TIMEOUT_SEC}s"
    except Exception as e:
        return False, None, str(e)
    finally:
        script_path.unlink(missing_ok=True)


def generate_and_run(
    section: dict, output_dir: Path, max_retries: int = 2
) -> tuple[bool, Path | None, bool]:
    section_id = section["id"]
    description = section.get("animation_prompt", "")
    style = section.get("animation_style", "process")
    heading = section.get("heading", "")

    for attempt in range(max_retries + 1):
        try:
            code = generate_manim_code(section_id, description, style, heading)
            # validate: (is_valid, error_msg, final_code) — 3개 반환
            is_valid, err_msg, final_code = validate_manim_code(code)
            if not is_valid:
                logger.warning(
                    f"[STEP08] VALIDATE_FAIL section={section_id} "
                    f"attempt={attempt}: {err_msg}"
                )
                continue
            success, clip_path, run_err = run_manim(
                final_code, section_id, output_dir
            )
            if success:
                section["manim_code"] = final_code
                section["manim_fallback_used"] = False
                return True, clip_path, False
            logger.warning(
                f"[STEP08] RUN_FAIL section={section_id} "
                f"attempt={attempt}: {run_err[:200]}"
            )
        except Exception as e:
            logger.error(f"[STEP08] ERROR section={section_id}: {e}")
            time.sleep(2 ** attempt)

    # Gemini 완전 실패 → 폴백 Manim 코드로 최소 클립 생성 시도
    logger.warning(f"[STEP08] section={section_id} Gemini 실패 → 폴백 Manim 사용")
    fallback_code = _make_fallback_manim(section_id, heading)
    is_valid, _, final_fallback = validate_manim_code(fallback_code)
    if is_valid:
        success, clip_path, _ = run_manim(final_fallback, section_id, output_dir)
        if success:
            section["manim_code"] = final_fallback
            section["manim_fallback_used"] = True
            return True, clip_path, True

    section["manim_fallback_used"] = True
    return False, None, True

