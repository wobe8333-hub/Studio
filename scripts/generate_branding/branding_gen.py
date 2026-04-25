"""채널 브랜딩 에셋 생성 — Gemini nano_banana 방식

로고 / 마스코트 / 인트로 / 아웃트로를 Gemini 이미지 생성으로 제작합니다.
PROMPTS 딕셔너리를 직접 수정해 원하는 스타일로 재생성할 수 있습니다.

사용법:
    python scripts/generate_branding/branding_gen.py --channel CH1 --type mascot
    python scripts/generate_branding/branding_gen.py --channel CH1 --type logo
    python scripts/generate_branding/branding_gen.py --channel CH1 --type intro
    python scripts/generate_branding/branding_gen.py --channel CH1 --type outro
    python scripts/generate_branding/branding_gen.py --channel CH1 --type all
    python scripts/generate_branding/branding_gen.py --channel CH1 --type mascot --prompt "커스텀 프롬프트"

출력 경로:
    로고    → assets/channels/{ch}/logo/logo.png
    마스코트 → assets/channels/{ch}/characters/character_default.png
             + assets/channels/{ch}/characters/narrator_ref.png  (QC layer1용 동일 이미지)
    인트로  → assets/channels/{ch}/intro/intro_card.png
             + assets/channels/{ch}/intro/intro.mp4  (FFmpeg 변환)
    아웃트로 → assets/channels/{ch}/outro/outro_card.png
             + assets/channels/{ch}/outro/outro.mp4  (FFmpeg 변환)
"""
from __future__ import annotations

import argparse
import io
import os
import shutil
import subprocess
import sys
from pathlib import Path

from dotenv import load_dotenv
from loguru import logger

load_dotenv()

sys.path.insert(0, str(Path(__file__).parent))

from gemini_image_gen import generate_image, generate_with_reference

# ─── 경로 ─────────────────────────────────────────────────────────────────────
_HERE = Path(__file__).parent
KAS_ROOT = _HERE.parent.parent
CHANNELS_DIR = KAS_ROOT / "assets" / "channels"
BASE_PLAIN = KAS_ROOT / "assets" / "shared" / "base_plain.png"

# 인트로 3초 / 아웃트로 10초
INTRO_DURATION = 3
OUTRO_DURATION = 10

# ─── 채널별 프롬프트 ──────────────────────────────────────────────────────────
# 아래 프롬프트를 수정하면 다음 실행 시 반영됩니다.

PROMPTS: dict[str, dict[str, str]] = {
    # ── CH1 머니그래픽 (경제) ───────────────────────────────────────────────────
    # 컨셉: 베이스 캐릭터 + 골드 왕관(W) + MZ 에너지
    # 색상: 골드 #F5C518 + 크림 #FFF8E1 + 초록 지폐
    "CH1": {
        # generate_with_reference(base_plain, scene_mode=False) — 마스코트 전용
        "mascot": (
            "Same character with a dark brown short back-and-sides haircut — "
            "clean fade on both sides, slightly swept forward and neatly styled on top. "
            "Wearing a slim-fit navy business suit with a white dress shirt visible at collar "
            "and a slightly loosened gold necktie. "
            "Bold golden crown with 5 pointed tips sitting on top of the head. "
            "Spinning a large gold coin on the tip of the right index finger, "
            "chest puffed out with confident pride. "
            "Expression: sharp knowing smirk, one eyebrow raised higher than the other, "
            "money-expert self-assured energy."
        ),
        # generate_with_reference(base_plain, scene_mode=True) — 씬 모드
        # 채널명은 Pillow 후처리로 추가 (_add_text_overlay "logo" 케이스)
        # B안: 에디토리얼 스탬프 — 팔각형 배지 + W 모노그램 + 왕관 (스트리트웨어 패치 감성)
        "logo": (
            "Apply this flat hand-drawn doodle cartoon style to ALL elements. "
            "Pure white background. "
            "LOGO SHAPE: regular octagon outline — thick 4px hand-drawn black stroke, "
            "slightly rough uneven lines like a hand-stamped patch badge, "
            "8 equal sides, centered in frame. "
            "INSIDE octagon background: pure white. "
            "INSIDE octagon: bold geometric W-shaped symbol — "
            "two V-shapes placed side by side sharing a center peak, forming a W silhouette — "
            "thick flat black fill, takes up 55% of interior space, centered vertically and horizontally. "
            "ON TOP OF W-SYMBOL: small 5-pointed gold (#F5C518) crown icon, "
            "sitting centered on the very top edge of the W, like a crown worn on a letter. "
            "COLORS: black octagon border, black W-symbol, gold (#F5C518) crown only. "
            "Bold editorial magazine section badge aesthetic — confident, graphic, stamp-like quality. "
            "NO circles. NO extra decorations. NO text. NO numbers. NO additional symbols. "
            "Clean white interior, strong black geometry, one gold accent."
        ),
        # generate_with_reference(base_plain, scene_mode=True) — ②+⑤ 합성
        # 포스터 풀샷(캐릭터 히어로) × 아카이브 프레임(두꺼운 테두리 진/잡지 미학)
        "intro": (
            "Apply this flat hand-drawn doodle cartoon style to ALL elements. "
            "16:9 wide horizontal scene. "
            "OUTER BORDER: thick 10px bold black rectangular frame on ALL 4 EDGES of the canvas — "
            "hand-drawn slightly uneven confident strokes, "
            "zine print-magazine aesthetic, like a physical print frame. "
            "INTERIOR BACKGROUND: warm cream (#FFF8E1), fills entire interior. "
            "MAIN CHARACTER: same character with dark brown short haircut, "
            "slim-fit navy business suit, golden 5-pointed crown on head, "
            "confident smirk with one eyebrow raised — "
            "FULL BODY, VERY LARGE, character height fills 82% of frame height, "
            "positioned slightly left of center, feet near bottom edge, "
            "poster-movie energy — commanding and large. "
            "LOGO BADGE: small octagonal badge (matching the logo — "
            "octagon outline, W-shape inside, small crown on W) — "
            "positioned upper-right area inside the frame, badge height 14% of frame height, floating. "
            "GOLD COINS: exactly one bold gold circle coin in lower-left corner area, "
            "one bold gold circle coin in lower-right corner area. "
            "CORNER ACCENTS: one tiny 4-pointed gold star in each of the 4 inner corners. "
            "COLORS: warm cream background, navy suit, gold crown and coins, black outlines. Flat colors only. "
            "NO text. NO letters. NO numbers. NO speech bubbles. NO background patterns. NO speed lines. "
            "Bold poster-meets-zine aesthetic. Character is the undisputed hero."
        ),
        # generate_with_reference(base_plain, scene_mode=True) — MZ 아웃트로 (서핑 A안)
        # 말풍선은 Pillow 후처리로 추가 (_add_text_overlay "outro" 케이스)
        "outro": (
            "Apply this flat hand-drawn doodle cartoon style to ALL elements in the scene — "
            "background, wave, bills, coins, sparkles, and character — not just the character. "
            "16:9 wide horizontal scene card. Warm cream (#FFF8E1) background. "
            "LEFT 60% OF SCENE ONLY: "
            "same character with dark brown short haircut, slim navy business suit, "
            "surfing on top of a MASSIVE curved wave made of overlapping green rectangular paper bills. "
            "Surfing pose: right arm stretched straight forward pointing ahead, "
            "body leaning forward dynamically, huge open-mouthed grin. "
            "THE MONEY WAVE: enormous sweeping curved arc of densely overlapping green bills "
            "rising high and curling at the top, multiple bills flying off the wave edges. "
            "SCATTERED IN LEFT AND CENTER AREAS ONLY: "
            "gold coins, 4-pointed yellow-gold sparkle stars, small green bills floating. "
            "RIGHT 40% OF SCENE: COMPLETELY BLANK AND EMPTY. "
            "Pure warm cream background only. ABSOLUTELY NOTHING in the right 40% — "
            "NO characters, NO coins, NO sparkles, NO doodles, NO shapes, NO elements of any kind. "
            "This right area MUST be completely clean and open. "
            "Colors: warm cream background, yellow-gold coins, green bills, black outlines. Flat colors only. "
            "NO text. NO letters. NO speech bubbles. NO rounded rectangles."
        ),
    },

    # ── CH2 가설낙서 (과학) ───────────────────────────────────────────────────
    # 컨셉: 폭발로 솟구친 노란 머리 + 그을린 실험복 + 낙서 노트 + 당혹 표정
    # 색상: 네온 시안 #00E5FF + 차콜 #1C1C1C
    "CH2": {
        "mascot": (
            "Person with spiky yellow hair exploding outward in all directions, blasted by an explosion. "
            "Wearing a white lab coat with visible black scorch marks and burn holes. "
            "Holding an open notebook densely covered in messy arrows and scribble doodles. "
            "Eyebrows raised very high, mouth open in embarrassed bewilderment, oh-no-it-went-wrong expression."
        ),
        "logo": (
            "Flat 2D hand-drawn doodle logo icon, 2px black outline, NO gradients, NO shadows, NO text, NO letters. "
            "Design: dark charcoal circular badge with thin double-ring border. "
            "Center icon: chemistry beaker with bright cyan liquid inside. "
            "Small explosion burst lines radiating from the beaker top. "
            "3 small cyan bubble circles above. Simple doodle icon. "
            "Colors: charcoal #1C1C1C badge, neon cyan #00E5FF liquid and bubbles."
        ),
        "intro": (
            "16:9 wide horizontal doodle card, flat 2D hand-drawn illustration, "
            "2px thin black marker lines, pure white background. NO gradients, NO shadows, NO text. "
            "Scene: scattered neon cyan doodles — chemistry flask shapes, atom orbit circles, "
            "starburst explosion shapes, abstract scribble patterns across the white canvas. "
            "Right side: small chibi character with spiky exploded yellow hair and burned white lab coat. "
            "Colors: neon cyan #00E5FF highlights, charcoal #1C1C1C outlines, white background. Flat colors only."
        ),
        "outro": (
            "16:9 wide horizontal doodle card, flat 2D hand-drawn illustration, "
            "2px thin black marker lines, pure white background. NO gradients, NO shadows, NO text. "
            "Center: large open notebook doodle with messy scribbles and a big question mark shape on it. "
            "Right: small chibi character with spiky exploded yellow hair, holding notebook up toward viewer. "
            "Top: rounded rectangle outline in neon cyan. "
            "Scattered neon cyan starburst doodles in corners. "
            "Colors: neon cyan #00E5FF, charcoal #1C1C1C, white background. Flat colors only."
        ),
    },

    # ── CH3 홈팔레트 (부동산) ───────────────────────────────────────────────────
    # 컨셉: 페인트 묻은 포니테일 + 세이지그린 앞치마 + 팔레트 + 코에 페인트 + 뿌듯 표정
    # 색상: 코랄 #FF6B6B + 세이지그린 #87AE73
    "CH3": {
        "mascot": (
            "Person with a ponytail, small paint splatters visible in the hair. "
            "Wearing a sage green apron over casual clothes. "
            "Holding a painter's palette with coral, mint, and cream paint blobs on it. "
            "Small dot of coral paint on the tip of their nose. "
            "Expression: proud satisfied smile, chin slightly lifted, self-pleased look."
        ),
        "logo": (
            "Flat 2D hand-drawn doodle logo icon, 2px black outline, pure white background, "
            "NO gradients, NO shadows, NO text, NO letters. "
            "Design: white circular badge with coral double-ring border. "
            "Center icon: simple house silhouette outline in coral. "
            "Inside the house: small painter's palette shape with 3 color blobs (coral, sage green, cream). "
            "Simple doodle icon. Colors: coral #FF6B6B border and house, sage green #87AE73 blob."
        ),
        "intro": (
            "16:9 wide horizontal doodle card, flat 2D hand-drawn illustration, "
            "2px thin black marker lines, pure white background. NO gradients, NO shadows, NO text. "
            "Scene: scattered interior design doodles — paint roller shape, simple sofa outline, "
            "window frame shape, paint drip streaks in coral and sage green. "
            "One diagonal paint brush stroke across the scene. "
            "Right corner: small chibi character with ponytail, sage green apron, holding color palette. "
            "Colors: coral #FF6B6B, sage green #87AE73, cream, black outlines, white background. Flat colors only."
        ),
        "outro": (
            "16:9 wide horizontal doodle card, flat 2D hand-drawn illustration, "
            "2px thin black marker lines, pure white background. NO gradients, NO shadows, NO text. "
            "Background: simple room interior — wall line and floor line at bottom. "
            "Center: chibi character with paint-splattered ponytail and sage green apron, "
            "arms crossed, proud smile looking at viewer. "
            "Coral paint splatter doodles in corners. "
            "Top: subscribe button rounded rectangle outline in coral. "
            "Colors: coral #FF6B6B, sage green #87AE73, white background. Flat colors only."
        ),
    },

    # ── CH4 오묘한심리 (심리) ───────────────────────────────────────────────────
    # 컨셉: 한쪽 눈 덮는 앞머리 + 인디고 후디 + 관자놀이 짚기 + 말풍선 + 모호한 표정
    # 색상: 인디고 #3D2C8D + 복숭아 #FFAB91
    "CH4": {
        "mascot": (
            "Person with long side-swept bangs covering one eye completely, only one eye visible. "
            "Wearing a deep indigo oversized hoodie. "
            "One hand raised with fingertips pressing thoughtfully against the temple. "
            "A small empty speech bubble doodle floating near the head. "
            "Expression: one visible eye slightly squinted, head tilted to one side, "
            "ambiguous maybe-I-understand-maybe-I-don't contemplative look."
        ),
        "logo": (
            "Flat 2D hand-drawn doodle logo icon, 2px black outline, NO gradients, NO shadows, NO text, NO letters. "
            "Design: deep indigo solid circular badge. "
            "Center icon: simple brain outline shape in peach. "
            "Around the brain: 3 small empty speech bubble outlines of varying sizes. "
            "Simple minimal doodle icon. Colors: indigo #3D2C8D badge, peach #FFAB91 brain and bubbles."
        ),
        "intro": (
            "16:9 wide horizontal doodle card, flat 2D hand-drawn illustration, "
            "2px thin black marker lines, pure white background. NO gradients, NO shadows, NO text. "
            "Scene: floating peach empty speech bubbles of various sizes drifting across the white canvas. "
            "Some bubbles contain three small dots inside. "
            "Right corner: small chibi character with one-eye-covering bangs, indigo hoodie, head tilted sideways. "
            "Colors: indigo #3D2C8D, peach #FFAB91, black outlines, white background. Flat colors only."
        ),
        "outro": (
            "16:9 wide horizontal doodle card, flat 2D hand-drawn illustration, "
            "2px thin black marker lines, pure white background. NO gradients, NO shadows, NO text. "
            "Center-left: chibi character with side-swept bangs covering one eye, indigo hoodie, "
            "one hand pointing outward toward viewer, thoughtful ambiguous expression. "
            "Right: large peach empty speech bubble outline. "
            "Scattered small speech bubble doodles in indigo and peach. "
            "Top: subscribe button rounded rectangle outline in indigo. "
            "Colors: indigo #3D2C8D, peach #FFAB91, white background. Flat colors only."
        ),
    },

    # ── CH5 검은물음표 (미스터리) ───────────────────────────────────────────────
    # 컨셉: 후드+검은 앞머리로 얼굴 반 가림 + 돋보기 + 뒤돌아봄 + 무표정
    # 색상: 미드나잇 블랙 #0A0A0A + 아이스블루 #B3E5FC
    "CH5": {
        # "그림자 반대 방향" 제거 — AI 이미지 모델이 의도적 조명 위반을 렌더링할 수 없음
        "mascot": (
            "Person with jet black hair hanging down like a curtain covering the lower half of the face, "
            "only the eyes visible above the hair. "
            "Wearing a black hoodie with the hood pulled up. "
            "Holding a magnifying glass raised to eye level, facing slightly to the side, "
            "eyes peering sideways toward the viewer with a watchful suspicious gaze. "
            "Expression: completely blank neutral unreadable deadpan."
        ),
        "logo": (
            "Flat 2D hand-drawn doodle logo icon, 2px black outline, NO gradients, NO shadows, NO text, NO letters. "
            "Design: pure black solid circular badge. "
            "Center icon: large question mark in ice blue. "
            "Inside the curved top of the question mark: two small circular dot eyes. "
            "Minimal eerie icon on black background. Colors: black #0A0A0A badge, ice blue #B3E5FC question mark."
        ),
        "intro": (
            "16:9 wide horizontal doodle card, flat 2D hand-drawn illustration, "
            "2px thin black marker lines, pure white background. NO gradients, NO shadows, NO text. "
            "Scene: ice blue question marks of various sizes scattered across white canvas, "
            "some solid, some half-faded as if disappearing. "
            "Right side: small chibi character in black hoodie with hood up, "
            "only eyes visible above black hair curtain, holding magnifying glass, glancing sideways. "
            "Colors: black #0A0A0A, ice blue #B3E5FC, white background. Flat colors only."
        ),
        "outro": (
            "16:9 wide horizontal doodle card, flat 2D hand-drawn illustration, "
            "2px thin black marker lines, pure white background. NO gradients, NO shadows, NO text. "
            "Background: white with scattered small ice blue question marks. "
            "Center: chibi character in black hoodie, arms slightly open toward viewer, "
            "face half-covered by black hair curtain, completely deadpan expression. "
            "Top: subscribe button rounded rectangle outline in ice blue. "
            "Colors: black #0A0A0A, ice blue #B3E5FC, white background. Flat colors only."
        ),
    },

    # ── CH6 오래된두루마리 (역사) ───────────────────────────────────────────────
    # 컨셉: 텁수룩한 갈색 머리 + 다크그린 체크 니트 + 빈티지 안경 + 두루마리 쏟아짐 + 헐 표정
    # 색상: 다크그린 #1B4332 + 크림 #FDFCF0 + 버건디 #6B2737
    "CH6": {
        "mascot": (
            "Person with slightly messy tousled medium-length brown hair, disheveled academic look. "
            "Wearing a dark forest green plaid check knit sweater. "
            "Round vintage-style circular glasses. "
            "Holding an ancient scroll that appears to unroll on its own, scribble symbols tumbling out of it. "
            "Expression: mouth wide open in shock and awe, eyebrows raised very high, completely floored reaction."
        ),
        "logo": (
            "Flat 2D hand-drawn doodle logo icon, 2px black outline, NO gradients, NO shadows, NO text, NO letters. "
            "Design: cream circular badge with dark green thick double-ring border. "
            "Center icon: ancient scroll in mid-unroll pose outlined in dark green. "
            "Bottom of badge: small wax seal circle in burgundy with simple X mark inside. "
            "Vintage scholarly aesthetic. Colors: cream #FDFCF0 badge, dark green #1B4332 border, burgundy #6B2737 seal."
        ),
        "intro": (
            "16:9 wide horizontal doodle card, flat 2D hand-drawn illustration, "
            "2px thin black marker lines, warm cream background. NO gradients, NO shadows, NO text. "
            "Scene: dark green ink-spreading effect radiating from center of cream canvas. "
            "Scattered ancient document doodles: quill pen shape, ink blot, small scroll silhouettes. "
            "Right side: ancient scroll visually unrolling with scribble symbols tumbling out. "
            "Corner: small chibi character with round glasses and dark green plaid sweater, shocked wide-open expression. "
            "Colors: dark green #1B4332, cream #FDFCF0, burgundy #6B2737. Flat colors only."
        ),
        "outro": (
            "16:9 wide horizontal doodle card, flat 2D hand-drawn illustration, "
            "2px thin black marker lines, warm cream background. NO gradients, NO shadows, NO text. "
            "Center: large scroll rolling itself back up, one end pointing toward a corner. "
            "Left: small chibi character with round glasses and plaid knit sweater, pointing at scroll. "
            "Bottom-right: burgundy wax seal circle doodle with X mark. "
            "Top: subscribe button rounded rectangle outline in dark green. "
            "Colors: dark green #1B4332, cream #FDFCF0, burgundy #6B2737. Flat colors only."
        ),
    },

    # ── CH7 워메이징 (전쟁사) ───────────────────────────────────────────────────
    # 컨셉: 베레모+군인 머리 + 올리브 군복 + 작전 지도 짚는 포즈 + 다 계획대로야 표정
    # 색상: 올리브 #556B2F + 레드 #D32F2F + 오프화이트
    "CH7": {
        "mascot": (
            "Person with very short buzz-cut military hair, wearing a dark olive beret on top. "
            "Wearing an olive green military uniform with small button details. "
            "Both hands pressed flat on an unrolled military operations map, "
            "leaning forward in a commanding authoritative stance. "
            "Expression: determined confident smirk, everything-is-going-according-to-plan self-assured look."
        ),
        "logo": (
            "Flat 2D hand-drawn doodle logo icon, 2px black outline, NO gradients, NO shadows, NO text, NO letters. "
            "Design: circular badge with outer ring in olive green and inner fill in off-white. "
            "Center icon: two crossed swords in red. "
            "Below the swords: horizontal rectangular military stamp outline in olive. "
            "Bold military aesthetic. Colors: olive #556B2F ring, red #D32F2F swords, off-white fill."
        ),
        "intro": (
            "16:9 wide horizontal doodle card, flat 2D hand-drawn illustration, "
            "2px thin black marker lines, off-white background. NO gradients, NO shadows, NO text. "
            "Scene: faint grid lines across off-white canvas, "
            "tactical arrow paths in red spreading in strategic directions. "
            "Right side: small chibi character in olive military uniform and beret, "
            "pressing both hands confidently on a simple map outline. "
            "Colors: olive #556B2F, red #D32F2F arrows, off-white background, black outlines. Flat colors only."
        ),
        "outro": (
            "16:9 wide horizontal doodle card, flat 2D hand-drawn illustration, "
            "2px thin black marker lines, off-white background. NO gradients, NO shadows, NO text. "
            "Background: off-white with subtle faint grid lines. "
            "Left: large bold red checkmark in military rubber stamp style. "
            "Center: chibi character in olive beret and military uniform, arms crossed, smirking at viewer. "
            "Top: subscribe button rounded rectangle outline in olive green. "
            "Corner: small crossed-sword doodles and red accent marks. "
            "Colors: olive #556B2F, red #D32F2F, off-white background. Flat colors only."
        ),
    },
}


# ─── PNG → MP4 변환 ──────────────────────────────────────────────────────────

def _png_to_mp4(png_path: Path, out_mp4: Path, duration: int) -> bool:
    """Pillow PNG → FFmpeg MP4 (yuv420p, 30fps, Ken Burns zoom + fade in/out).

    인트로(≤3s): 1.0→1.2 zoom-in (20% 확대, 눈에 확실히 보임)
    아웃트로(>3s): 1.0→1.15 zoom-in (10s 동안 부드럽게 확대)
    """
    W, H = 1280, 720
    fps = 30
    d = duration * fps
    fade = 0.2
    if duration <= 3:
        step = round(0.20 / d, 6)   # 3초에 걸쳐 20% 확대
        z_max = 1.20
    else:
        step = round(0.15 / d, 6)   # 10초에 걸쳐 15% 확대
        z_max = 1.15
    # scale=2560x1440: max_zoom=1.2 기준 최소 필요 입력 1536px의 1.67배 → 충분한 여백
    zoom_filter = (
        f"scale=2560:1440,"
        f"zoompan=z='min(zoom+{step},{z_max})'"
        f":x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
        f":d={d}:s={W}x{H}:fps={fps}"
    )
    cmd = [
        "ffmpeg", "-y",
        "-loop", "1", "-i", str(png_path),
        "-vf", (
            f"{zoom_filter},"
            f"fade=t=in:st=0:d={fade},"
            f"fade=t=out:st={duration - fade}:d={fade}"
        ),
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        "-t", str(duration),
        "-pix_fmt", "yuv420p",
        "-movflags", "+faststart",
        str(out_mp4),
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, timeout=60)
        if result.returncode != 0:
            logger.error(f"[FFmpeg] 오류: {result.stderr.decode(errors='replace')[:300]}")
            return False
        logger.info(f"[MP4] {out_mp4.name} ({duration}s) 생성 완료")
        return True
    except Exception as e:
        logger.error(f"[FFmpeg] 예외: {e}")
        return False


# ─── 에셋별 생성 함수 ─────────────────────────────────────────────────────────

def _add_text_overlay(png_path: Path, channel_id: str, asset_type: str) -> None:
    """인트로/아웃트로 PNG에 한국어 텍스트 Pillow 오버레이."""
    from PIL import Image, ImageDraw, ImageFont

    # CH별 채널명 + 아웃트로 CTA 텍스트
    CHANNEL_NAMES = {
        "CH1": "머니그래픽", "CH2": "가설낙서", "CH3": "홈팔레트",
        "CH4": "오묘한심리", "CH5": "검은물음표", "CH6": "오래된두루마리", "CH7": "워메이징",
    }
    CHANNEL_COLORS = {
        "CH1": "#F5C518", "CH2": "#00E5FF", "CH3": "#FF6B6B",
        "CH4": "#FFAB91", "CH5": "#B3E5FC", "CH6": "#1B4332", "CH7": "#D32F2F",
    }

    img = Image.open(png_path).convert("RGBA")
    draw = ImageDraw.Draw(img)
    W, H = img.size

    # 시스템 굵은 한글 폰트 (없으면 기본 폰트 fallback)
    FONT_CANDIDATES = [
        "C:/Windows/Fonts/malgunbd.ttf",   # 맑은 고딕 Bold (Windows)
        "C:/Windows/Fonts/NanumGothicBold.ttf",
        "/usr/share/fonts/truetype/noto/NotoSansKR-Bold.ttf",
    ]

    def _load_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
        for fp in FONT_CANDIDATES:
            try:
                return ImageFont.truetype(fp, size)
            except Exception:
                continue
        return ImageFont.load_default()

    def _draw_outlined_text(draw, xy, text, font, fill, outline, width=4):
        x, y = xy
        for dx in range(-width, width + 1):
            for dy in range(-width, width + 1):
                if dx != 0 or dy != 0:
                    draw.text((x + dx, y + dy), text, font=font, fill=outline)
        draw.text((x, y), text, font=font, fill=fill)

    if asset_type == "intro":
        text = CHANNEL_NAMES.get(channel_id, channel_id)
        color = CHANNEL_COLORS.get(channel_id, "#F5C518")
        font_size = max(56, H // 7)
        font = _load_font(font_size)
        # 좌측 1/3 영역 중앙
        x, y = W // 16, H * 38 // 100
        _draw_outlined_text(draw, (x, y), text, font, fill=color, outline="#111111", width=5)

    elif asset_type == "logo":
        # 검은 배너(로고 하단 내부) 위에 흰색 채널명
        text = CHANNEL_NAMES.get(channel_id, channel_id)
        font_size = max(38, H // 15)
        font = _load_font(font_size)
        bbox = draw.textbbox((0, 0), text, font=font)
        tw = bbox[2] - bbox[0]
        x = (W - tw) // 2      # 수평 중앙
        y = H * 71 // 100      # 검은 배너 수직 중앙 추정 (이미지 하단 29% 지점)
        draw.text((x, y), text, font=font, fill="#FFFFFF")

    elif asset_type == "outro":
        # Pillow로 직접 말풍선 + 꼬리 + "구독 & 좋아요!" 드로잉
        # 우측 40% 영역에 배치 (Gemini가 해당 공간을 비워두도록 프롬프트에서 지시)
        bx1 = W * 56 // 100
        by1 = H * 11 // 100
        bx2 = W * 96 // 100
        by2 = H * 63 // 100
        corner_r = 28

        # 말풍선 배경 (흰색 채움 + 검은 테두리)
        try:
            draw.rounded_rectangle(
                [bx1, by1, bx2, by2],
                radius=corner_r,
                fill="#FFFFFF",
                outline="#111111",
                width=4,
            )
        except AttributeError:
            # Pillow < 8.2 fallback
            draw.rectangle([bx1, by1, bx2, by2], fill="#FFFFFF", outline="#111111", width=4)

        # 아래 화살표 꼬리
        cx = (bx1 + bx2) // 2
        tail_w = W * 3 // 100
        tail_top = by2
        tail_bot = by2 + H * 10 // 100
        # 꼬리 내부 채우기
        draw.polygon(
            [(cx - tail_w, tail_top), (cx + tail_w, tail_top), (cx, tail_bot)],
            fill="#FFFFFF",
        )
        # 꼬리 외곽선 (좌/우변만 — 윗변은 버블 하단선과 겹침)
        draw.line([(cx - tail_w, tail_top), (cx, tail_bot)], fill="#111111", width=4)
        draw.line([(cx + tail_w, tail_top), (cx, tail_bot)], fill="#111111", width=4)

        # "구독 & 좋아요!" 텍스트 말풍선 내부 중앙
        text = "구독 & 좋아요!"
        font_size = max(40, (by2 - by1) // 3)
        font = _load_font(font_size)
        bbox = draw.textbbox((0, 0), text, font=font)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        tx = bx1 + ((bx2 - bx1) - tw) // 2
        ty = by1 + ((by2 - by1) - th) // 2
        draw.text((tx, ty), text, font=font, fill="#111111")

    elif asset_type == "mascot_crown":
        # W 왕관 오버레이 — 왕관 중앙 상단에 "W" 추가
        text = "W"
        color = CHANNEL_COLORS.get(channel_id, "#F5C518")
        font_size = max(32, H // 9)
        font = _load_font(font_size)
        # 캐릭터 머리 상단 추정 위치 (흰 배경, 캐릭터가 중앙이므로 중앙 상단)
        x, y = W // 2 - font_size // 2, H // 8
        _draw_outlined_text(draw, (x, y), text, font, fill="#111111", outline=color, width=3)

    img = img.convert("RGB")
    img.save(png_path, "PNG")
    logger.info(f"[{channel_id}] {asset_type} 텍스트 오버레이 완료")


def generate_logo(channel_id: str, prompt: str | None = None) -> Path:
    out = CHANNELS_DIR / channel_id / "logo" / "logo.png"
    out.parent.mkdir(parents=True, exist_ok=True)

    if not BASE_PLAIN.exists():
        raise RuntimeError(f"base_plain.png 없음: {BASE_PLAIN}")

    p = prompt or PROMPTS[channel_id]["logo"]
    logger.info(f"[{channel_id}] 로고 생성 중 (base_plain 레퍼런스, scene_mode)...")
    ok = generate_with_reference(BASE_PLAIN, p, out, scene_mode=True)
    if ok:
        _add_text_overlay(out, channel_id, "logo")
        try:
            from PIL import Image
            img = Image.open(out)
            sm = out.parent / "logo_sm.png"
            img.resize((256, 256), Image.LANCZOS).save(sm, "PNG")
            logger.info(f"[{channel_id}] logo_sm.png 생성 완료")
        except Exception as e:
            logger.warning(f"logo_sm.png 생성 실패: {e}")
    return out


def generate_logo_variants(channel_id: str, n: int = 3, prompt: str | None = None) -> list[Path]:
    """로고 Best-of-N: n개 variant를 _candidates/logo/ 에 저장 후 경로 반환."""
    from gemini_image_gen import generate_best_of_n_with_reference
    canonical = CHANNELS_DIR / channel_id / "logo" / "logo.png"
    canonical.parent.mkdir(parents=True, exist_ok=True)
    if not BASE_PLAIN.exists():
        raise RuntimeError(f"base_plain.png 없음: {BASE_PLAIN}")
    p = prompt or PROMPTS[channel_id]["logo"]
    logger.info(f"[{channel_id}] 로고 Best-of-{n} 생성 중...")
    variants = generate_best_of_n_with_reference(BASE_PLAIN, p, canonical, n=n, scene_mode=True)
    for v in variants:
        _add_text_overlay(v, channel_id, "logo")
    _log_variants("logo", variants)
    return variants


def generate_mascot(channel_id: str, prompt: str | None = None) -> tuple[Path, Path]:
    char_default = CHANNELS_DIR / channel_id / "characters" / "character_default.png"
    narrator_ref = CHANNELS_DIR / channel_id / "characters" / "narrator_ref.png"
    char_default.parent.mkdir(parents=True, exist_ok=True)
    narrator_ref.parent.mkdir(parents=True, exist_ok=True)

    if not BASE_PLAIN.exists():
        raise RuntimeError(f"base_plain.png 없음: {BASE_PLAIN}")

    p = prompt or PROMPTS[channel_id]["mascot"]
    logger.info(f"[{channel_id}] 마스코트 생성 중 (base_plain 레퍼런스)...")
    ok = generate_with_reference(BASE_PLAIN, p, char_default)
    if not ok:
        raise RuntimeError(f"[{channel_id}] 마스코트 생성 실패")
    shutil.copy2(char_default, narrator_ref)
    logger.info(f"[{channel_id}] 마스코트 저장 완료\n  → {char_default}\n  → {narrator_ref}")
    return char_default, narrator_ref


def generate_mascot_variants(channel_id: str, n: int = 3, prompt: str | None = None) -> list[Path]:
    """마스코트 Best-of-N: n개 variant를 _candidates/character_default/ 에 저장."""
    from gemini_image_gen import generate_best_of_n_with_reference
    canonical = CHANNELS_DIR / channel_id / "characters" / "character_default.png"
    canonical.parent.mkdir(parents=True, exist_ok=True)
    if not BASE_PLAIN.exists():
        raise RuntimeError(f"base_plain.png 없음: {BASE_PLAIN}")
    p = prompt or PROMPTS[channel_id]["mascot"]
    logger.info(f"[{channel_id}] 마스코트 Best-of-{n} 생성 중...")
    variants = generate_best_of_n_with_reference(BASE_PLAIN, p, canonical, n=n, scene_mode=False)
    _log_variants("mascot", variants)
    return variants


def generate_intro(channel_id: str, prompt: str | None = None) -> Path:
    card_dir = CHANNELS_DIR / channel_id / "intro"
    card_dir.mkdir(parents=True, exist_ok=True)

    png_out = card_dir / "intro_card.png"
    mp4_out = card_dir / "intro.mp4"

    if not BASE_PLAIN.exists():
        raise RuntimeError(f"base_plain.png 없음: {BASE_PLAIN}")

    p = prompt or PROMPTS[channel_id]["intro"]
    logger.info(f"[{channel_id}] 인트로 카드 생성 중 (base_plain 레퍼런스, scene_mode)...")
    ok = generate_with_reference(BASE_PLAIN, p, png_out, scene_mode=True)
    if not ok:
        raise RuntimeError(f"[{channel_id}] 인트로 이미지 생성 실패")
    _add_text_overlay(png_out, channel_id, "intro")
    _png_to_mp4(png_out, mp4_out, INTRO_DURATION)
    logger.info(f"[{channel_id}] 인트로 완료 → {mp4_out}")
    return mp4_out


def generate_intro_variants(channel_id: str, n: int = 3, prompt: str | None = None) -> list[Path]:
    """인트로 Best-of-N: n개 PNG variant + 각각 MP4를 _candidates/intro_card/ 에 저장."""
    from gemini_image_gen import generate_best_of_n_with_reference
    canonical = CHANNELS_DIR / channel_id / "intro" / "intro_card.png"
    canonical.parent.mkdir(parents=True, exist_ok=True)
    if not BASE_PLAIN.exists():
        raise RuntimeError(f"base_plain.png 없음: {BASE_PLAIN}")
    p = prompt or PROMPTS[channel_id]["intro"]
    logger.info(f"[{channel_id}] 인트로 Best-of-{n} 생성 중...")
    variants = generate_best_of_n_with_reference(BASE_PLAIN, p, canonical, n=n, scene_mode=True)
    for v in variants:
        _add_text_overlay(v, channel_id, "intro")
        mp4 = v.with_suffix(".mp4")
        _png_to_mp4(v, mp4, INTRO_DURATION)
    _log_variants("intro", variants)
    return variants


def generate_outro(channel_id: str, prompt: str | None = None) -> Path:
    card_dir = CHANNELS_DIR / channel_id / "outro"
    card_dir.mkdir(parents=True, exist_ok=True)

    png_out = card_dir / "outro_card.png"
    mp4_out = card_dir / "outro.mp4"

    if not BASE_PLAIN.exists():
        raise RuntimeError(f"base_plain.png 없음: {BASE_PLAIN}")

    p = prompt or PROMPTS[channel_id]["outro"]
    logger.info(f"[{channel_id}] 아웃트로 카드 생성 중 (base_plain 레퍼런스, scene_mode)...")
    ok = generate_with_reference(BASE_PLAIN, p, png_out, scene_mode=True)
    if not ok:
        raise RuntimeError(f"[{channel_id}] 아웃트로 이미지 생성 실패")
    _add_text_overlay(png_out, channel_id, "outro")
    _png_to_mp4(png_out, mp4_out, OUTRO_DURATION)
    logger.info(f"[{channel_id}] 아웃트로 완료 → {mp4_out}")
    return mp4_out


def generate_outro_variants(
    channel_id: str,
    n: int = 3,
    prompt: str | None = None,
    reference_path: Path | None = None,
) -> list[Path]:
    """아웃트로 Best-of-N: n개 PNG variant + 각각 MP4를 _candidates/outro_card/ 에 저장.

    reference_path: None이면 BASE_PLAIN 사용.
                    확정된 마스코트 경로를 넘기면 캐릭터 일관성이 높아진다.
    """
    from gemini_image_gen import generate_best_of_n_with_reference
    canonical = CHANNELS_DIR / channel_id / "outro" / "outro_card.png"
    canonical.parent.mkdir(parents=True, exist_ok=True)
    ref = reference_path or BASE_PLAIN
    if not ref.exists():
        raise RuntimeError(f"레퍼런스 이미지 없음: {ref}")
    p = prompt or PROMPTS[channel_id]["outro"]
    logger.info(f"[{channel_id}] 아웃트로 Best-of-{n} 생성 중 (ref: {ref.name})...")
    variants = generate_best_of_n_with_reference(ref, p, canonical, n=n, scene_mode=True)
    for v in variants:
        _add_text_overlay(v, channel_id, "outro")
        mp4 = v.with_suffix(".mp4")
        _png_to_mp4(v, mp4, OUTRO_DURATION)
    _log_variants("outro", variants)
    return variants


def _log_variants(asset_type: str, variants: list[Path]) -> None:
    """생성된 variant 경로를 사용자가 확인하기 쉽게 출력한다."""
    if not variants:
        logger.warning(f"[{asset_type}] 생성된 variant 없음")
        return
    logger.info(f"\n{'='*55}")
    logger.info(f"[{asset_type}] {len(variants)}개 variant 생성 완료 — 마음에 드는 파일을 확인 후 선택하세요:")
    for i, v in enumerate(variants, 1):
        logger.info(f"  variant {i}: {v}")
    logger.info(
        f"\n  원하는 variant를 최종 경로로 복사하려면:\n"
        f"  copy \"{variants[0]}\" \"{variants[0].parent.parent.parent / asset_type.replace('_card','') / (asset_type.replace('_card','') + '_card.png')}\""
    )
    logger.info(f"{'='*55}\n")


# ─── 메인 ─────────────────────────────────────────────────────────────────────

ASSET_TYPES = ["logo", "mascot", "intro", "outro", "all"]
ALL_CHANNELS = ["CH1", "CH2", "CH3", "CH4", "CH5", "CH6", "CH7"]


def run(channel_id: str, asset_type: str, prompt: str | None = None, best_of: int = 1) -> None:
    if channel_id not in PROMPTS:
        logger.error(f"지원하지 않는 채널: {channel_id} (가능: {list(PROMPTS.keys())})")
        return

    asset_list = ["logo", "mascot", "intro", "outro"] if asset_type == "all" else [asset_type]

    for t in asset_list:
        try:
            if best_of > 1:
                if t == "logo":
                    generate_logo_variants(channel_id, n=best_of, prompt=prompt)
                elif t == "mascot":
                    generate_mascot_variants(channel_id, n=best_of, prompt=prompt)
                elif t == "intro":
                    generate_intro_variants(channel_id, n=best_of, prompt=prompt)
                elif t == "outro":
                    generate_outro_variants(channel_id, n=best_of, prompt=prompt)
            else:
                if t == "logo":
                    generate_logo(channel_id, prompt)
                elif t == "mascot":
                    generate_mascot(channel_id, prompt)
                elif t == "intro":
                    generate_intro(channel_id, prompt)
                elif t == "outro":
                    generate_outro(channel_id, prompt)
        except Exception as e:
            logger.error(f"[{channel_id}/{t}] 오류: {e}")


if __name__ == "__main__":
    if hasattr(sys.stdout, "buffer"):
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(description="채널 브랜딩 에셋 생성 (Gemini nano_banana)")
    parser.add_argument(
        "--channel", required=True,
        choices=ALL_CHANNELS,
        help="대상 채널 ID (예: CH1)",
    )
    parser.add_argument(
        "--type", required=True,
        choices=ASSET_TYPES,
        help="생성할 에셋 타입",
    )
    parser.add_argument(
        "--prompt", default=None,
        help="커스텀 프롬프트 (생략 시 PROMPTS 딕셔너리 사용)",
    )
    parser.add_argument(
        "--best-of", type=int, default=1, metavar="N",
        help="Best-of-N: N개 variant를 _candidates/ 에 생성 후 선택 (기본 1=단일 생성)",
    )
    args = parser.parse_args()
    run(args.channel, args.type, args.prompt, best_of=args.best_of)
