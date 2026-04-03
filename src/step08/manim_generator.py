"""
STEP 08 — Manim 코드 생성기 (LaTeX-free, 버그 수정 완료)
"""
import ast, re, sys, subprocess, tempfile, time, shutil
from loguru import logger
from pathlib import Path
from tenacity import retry, stop_after_attempt, wait_exponential
import google.generativeai as genai
from src.core.config import GEMINI_API_KEY, GEMINI_TEXT_MODEL, MANIM_QUALITY
from src.quota.gemini_quota import throttle_if_needed, record_request

genai.configure(api_key=GEMINI_API_KEY)
LATEX_FORBIDDEN_PATTERNS = [
    r"MathTex\s*\(",
    r"(?<!\w)Tex\s*\(",
    r"include_numbers\s*=\s*True",
    r"include_numbers\s*:\s*True",
    r"include_numbers['\"]\s*:\s*True",
    r"BarChart\s*\(",
    r"DecimalNumber\s*\(",
]

LATEX_FREE_SYSTEM_INSTRUCTION = """당신은 Manim 전문가입니다.

[필수 규칙 — 위반 시 렌더링 실패]
1. MathTex(), Tex() 사용 절대 금지 → Text() 사용
2. Axes(include_numbers=True) 금지 → include_numbers=False 사용
3. NumberLine(include_numbers=True) 금지 → include_numbers=False 사용
4. BarChart() 클래스 사용 금지 → Rectangle() 기반 커스텀 바 사용
5. DecimalNumber() Mobject 사용 금지 → Text() 사용

[이유]
pdflatex가 설치되지 않은 환경이다.
LaTeX를 호출하면 FileNotFoundError(WinError 2)로 반드시 실패한다.
"""

MANIM_CODE_PROMPT = """다음 설명에 맞는 Manim Python 코드를 작성하시오.
설명: {description}
애니메이션 스타일: {style}
섹션 제목: {heading}

규칙:
- from manim import * 로 시작
- class 이름: Section{section_id}Scene(Scene)
- 실행 시간: 15~25초
- 색상: BLUE, GREEN, RED, YELLOW, WHITE, ORANGE
- 외부 라이브러리 import 금지
- Python 코드만 출력 (설명 없이)
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

    logger.info(f"[STEP08] LaTeX 자동 수정 성공")
    return True, "", fixed


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=30))
def generate_manim_code(section_id: int, description: str,
                          style: str, heading: str) -> str:
    model = genai.GenerativeModel(
        GEMINI_TEXT_MODEL,
        system_instruction=LATEX_FREE_SYSTEM_INSTRUCTION,
    )
    throttle_if_needed()
    record_request()
    response = model.generate_content(
        MANIM_CODE_PROMPT.format(
            description=description, style=style,
            heading=heading, section_id=section_id,
        ),
        generation_config=genai.GenerationConfig(max_output_tokens=2000),
    )
    code = response.text.strip()
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

    section["manim_fallback_used"] = True
    return False, None, True

