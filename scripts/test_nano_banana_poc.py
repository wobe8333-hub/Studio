# scripts/test_nano_banana_poc.py
"""POC: Gemini 멀티모달로 CH1 explain 캐릭터 1장 생성 후 시각 검수

사용법:
    cd C:\\Users\\조찬우\\Desktop\\ai_stuidio_claude
    python scripts/test_nano_banana_poc.py
"""
import io
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.path.insert(0, str(Path(__file__).parent / "generate_branding"))

from dotenv import load_dotenv
load_dotenv()

from nano_banana_helper import generate_with_reference
from config import CHANNELS, KAS_ROOT

REFERENCE = KAS_ROOT / "essential_branding" / "CH1.png"
OUT = KAS_ROOT / "assets" / "channels" / "CH1" / "characters" / "character_explain_poc.png"

if not REFERENCE.exists():
    print(f"[ERR] 레퍼런스 이미지 없음: {REFERENCE}")
    sys.exit(1)

print(f"레퍼런스: {REFERENCE}")
print(f"출력 경로: {OUT}")
print("생성 중...\n")

ch1 = CHANNELS["CH1"]
prompt = ch1["character_prompts"]["explain"]

ok = generate_with_reference(REFERENCE, prompt, OUT)

if ok:
    print(f"\n[성공] POC 이미지 생성 완료: {OUT}")
    print("\n─── 시각 검수 체크리스트 ───────────────────────────────")
    print("  이미지를 열어서 다음 항목을 확인하세요:")
    print("  ✅ 크림 배경 (#FFFDF5)")
    print("  ✅ 얇은 검정 마커 선 (2-3px)")
    print("  ✅ 평면 2D (그림자·그라디언트 없음)")
    print("  ✅ 삐뚤빼뚤한 손그림 선")
    print("  ❌ 텍스트/헥스코드 오염 없음")
    print("  ❌ 3D 렌더링 느낌 없음")
    print("─────────────────────────────────────────────────────────")
    print(f"\n이미지 열기: start {OUT}")
else:
    print("\n[실패] Gemini 멀티모달 이미지 생성 실패.")
    print("→ SVG stick figure 폴백 방식으로 전환이 필요합니다.")
    print("→ 다음 단계: Task 2 (SVG 폴백 분기) 실행")
