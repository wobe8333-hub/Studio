"""KAS 파이프라인 preflight 체크 — 파일럿 실행 전 환경 점검.

실행:
  python scripts/preflight_check.py

점검 항목:
  1. 필수 환경 변수 설정 여부
  2. 채널 디렉토리 및 정책 파일 존재 여부
  3. Python 패키지 임포트 체인
  4. Gemini API 연결 테스트
  5. OAuth token 파일 존재 여부
  6. FFmpeg 실행 가능 여부
"""

import sys
import os
from pathlib import Path

# 프로젝트 루트
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

PASS = "✅"
FAIL = "❌"
WARN = "⚠️ "

results = []


def check(name: str, ok: bool, detail: str = "") -> bool:
    icon = PASS if ok else FAIL
    msg = f"{icon} {name}"
    if detail:
        msg += f"  ({detail})"
    results.append((ok, msg))
    print(msg)
    return ok


def warn(name: str, detail: str = "") -> None:
    msg = f"{WARN} {name}"
    if detail:
        msg += f"  ({detail})"
    results.append((True, msg))
    print(msg)


# ─── 1. 환경 변수 ────────────────────────────────────────────────────────────
print("\n[1] 필수 환경 변수")
try:
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env", override=True)
except ImportError:
    pass

REQUIRED_VARS = ["GEMINI_API_KEY", "YOUTUBE_API_KEY"]
OPTIONAL_VARS = ["ELEVENLABS_API_KEY", "SENTRY_DSN", "SERPAPI_KEY"]
CH_VARS = [f"CH{i}_CHANNEL_ID" for i in range(1, 8)]

for var in REQUIRED_VARS:
    val = os.environ.get(var, "")
    check(var, bool(val), "설정됨" if val else "미설정")

for var in OPTIONAL_VARS:
    val = os.environ.get(var, "")
    if val:
        print(f"{PASS} {var}  (설정됨)")
    else:
        warn(var, "미설정 — 폴백 동작")

for var in CH_VARS:
    val = os.environ.get(var, "")
    check(var, bool(val), val[:20] + "..." if val else "미설정")

# ─── 2. 채널 디렉토리 및 정책 파일 ──────────────────────────────────────────
print("\n[2] 채널 데이터 파일")
try:
    from src.core.config import CHANNELS_DIR, CHANNEL_CATEGORIES
    for ch in CHANNEL_CATEGORIES.keys():
        ch_dir = CHANNELS_DIR / ch
        has_dir = ch_dir.exists()
        has_algo = (ch_dir / "algorithm_policy.json").exists()
        has_rev  = (ch_dir / "revenue_policy.json").exists()
        has_style = (ch_dir / "style_policy.json").exists()
        ok = has_dir and has_algo and has_rev
        detail = f"dir={has_dir} algo={has_algo} rev={has_rev} style={has_style}"
        check(f"{ch} 정책 파일", ok, detail)
except Exception as e:
    check("채널 설정 로드", False, str(e)[:80])

# ─── 3. 핵심 모듈 임포트 ────────────────────────────────────────────────────
print("\n[3] 핵심 모듈 임포트")
modules_to_check = [
    ("src.core.config", "설정 SSOT"),
    ("src.step05.trend_collector", "트렌드 수집"),
    ("src.step06.style_policy", "스타일 정책"),
    ("src.step07.revenue_policy", "수익 정책"),
    ("src.step11.qa_gate", "QA 게이트"),
    ("src.quota.gemini_quota", "Gemini 쿼터"),
    ("src.quota.youtube_quota", "YouTube 쿼터"),
]
for mod, label in modules_to_check:
    try:
        __import__(mod)
        check(label, True, mod)
    except Exception as e:
        check(label, False, str(e)[:60])

# step08 별도 (google.generativeai 의존)
try:
    import google.generativeai  # noqa: F401
    check("google.generativeai", True, "설치됨")
except ImportError:
    check("google.generativeai", False, "pip install google-generativeai 필요")

# ─── 4. Gemini API 연결 테스트 ───────────────────────────────────────────────
print("\n[4] Gemini API 연결")
try:
    import google.generativeai as genai
    from src.core.config import GEMINI_API_KEY, GEMINI_TEXT_MODEL
    if GEMINI_API_KEY:
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel(GEMINI_TEXT_MODEL)
        resp = model.generate_content("안녕하세요. 한 단어로만 답해주세요: 오늘 날씨는?")
        check("Gemini API 응답", bool(resp.text), resp.text[:30])
    else:
        check("Gemini API", False, "GEMINI_API_KEY 미설정")
except Exception as e:
    check("Gemini API 연결", False, str(e)[:80])

# ─── 5. OAuth token 파일 ─────────────────────────────────────────────────────
print("\n[5] YouTube OAuth 토큰")
try:
    from src.core.config import CREDENTIALS_DIR, CHANNEL_CATEGORIES
    for ch in CHANNEL_CATEGORIES.keys():
        token_path = CREDENTIALS_DIR / f"{ch}_token.json"
        check(f"{ch} token.json", token_path.exists(),
              "있음" if token_path.exists() else f"없음 — {token_path}")
except Exception as e:
    check("OAuth 토큰 디렉토리", False, str(e)[:60])

# ─── 6. FFmpeg ───────────────────────────────────────────────────────────────
print("\n[6] FFmpeg")
import subprocess
try:
    r = subprocess.run(
        ["ffmpeg", "-version"], capture_output=True, text=True, timeout=10
    )
    ver_line = r.stdout.splitlines()[0] if r.stdout else ""
    check("FFmpeg 실행", r.returncode == 0, ver_line[:60])
except FileNotFoundError:
    check("FFmpeg", False, "ffmpeg 명령어 없음 — PATH 확인 또는 ffmpeg 설치 필요")
except Exception as e:
    check("FFmpeg", False, str(e)[:60])

# ─── 요약 ───────────────────────────────────────────────────────────────────
print("\n" + "=" * 60)
failures = [msg for ok, msg in results if not ok and "❌" in msg]
if failures:
    print(f"❌ {len(failures)}개 항목 실패:")
    for msg in failures:
        print(f"   {msg}")
    print("\n위 항목을 해결한 후 파이프라인을 실행하세요.")
    sys.exit(1)
else:
    print(f"✅ 모든 체크 통과! 파일럿 실행 준비 완료")
    print("\n파일럿 실행 명령어 (CH1~CH2):")
    print("  python -m src.pipeline 1")
