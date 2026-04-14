"""CH1.png bbox 측정용 디버그 스크립트 — 실행 후 _debug/CH1_bbox.png 확인"""
from pathlib import Path
from PIL import Image, ImageDraw
import sys
import io

if __name__ == "__main__":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

    img = Image.open("essential_branding/CH1.png").convert("RGBA")
    W, H = img.size
    print(f"이미지 크기: {W}×{H}")

    # 흰 배경 위에 오버레이
    overlay = Image.new("RGBA", (W, H), (255, 255, 255, 255))
    overlay.paste(img, (0, 0), img)
    draw = ImageDraw.Draw(overlay)

    # 정밀 측정 bbox (L, T, R, B) — 1379×752 이미지 기준
    regions = {
        # ── 섹션1: 비주얼 아이덴티티 (x: 0~495) ──
        # 채널 로고: 원형 프레임 + 왕관 캐릭터 + "머니그래픽" 텍스트
        "logo":               (15,  75, 215, 310),
        # 캐릭터 4종: 각 캐릭터 영역
        "character_explain":  (218, 85, 345, 240),
        "character_rich":     (345, 85, 475, 240),
        "character_money":    (218, 240, 345, 390),
        "character_lucky":    (345, 240, 475, 390),
        # ── 섹션2: 영상 제작 에센셜 (x: 495~1379) ──
        # 인트로(3s) 전체 박스
        "intro_frame":        (495, 75, 695, 250),
        # 인트로 내 "머니그래픽" 텍스트 부분
        "intro_text":         (500, 185, 690, 245),
        # 인트로 내 캐릭터만
        "intro_character":    (530, 85, 660, 190),
        # 인트로 내 반짝이(별) 부분
        "intro_sparkle":      (495, 75, 560, 140),
        # 아웃트로(10s) 전체 박스
        "outro_background":   (700, 75, 960, 250),
        # 아웃트로 내 지폐 요소
        "outro_bill":         (710, 80, 870, 165),
        # 아웃트로 내 캐릭터
        "outro_character":    (710, 110, 820, 248),
        # 아웃트로 내 CTA("구독하고 돕기") 텍스트
        "outro_cta":          (820, 155, 955, 248),
        # 썸네일 예시 3종
        "thumbnail_sample_1": (965, 75, 1115, 248),
        "thumbnail_sample_2": (1120, 75, 1260, 165),
        "thumbnail_sample_3": (1120, 168, 1260, 248),
        # 자막 Bar 3종 (영상 스타일 에시)
        "subtitle_bar_key":   (495, 268, 875, 325),
        "subtitle_bar_dialog":(495, 328, 875, 385),
        "subtitle_bar_info":  (495, 388, 875, 445),
        # 장면 전환 3종
        "transition_paper":   (885, 268, 1050, 445),
        "transition_ink":     (1055, 268, 1215, 445),
        "transition_zoom":    (1220, 268, 1375, 445),
    }
    colors = ["red", "blue", "green", "orange", "purple", "cyan", "magenta", "yellow", "lime", "pink",
              "brown", "gray", "teal", "navy", "coral", "olive", "maroon", "silver", "gold", "violet", "indigo", "crimson"]
    for i, (name, (l, t, r, b)) in enumerate(regions.items()):
        c = colors[i % len(colors)]
        draw.rectangle([l, t, r, b], outline=c, width=2)
        draw.text((l + 2, t + 2), name[:12], fill=c)

    out = Path("_debug")
    out.mkdir(exist_ok=True)
    overlay.convert("RGB").save(out / "CH1_bbox.png")
    print("저장 완료: _debug/CH1_bbox.png — 이 파일을 열어 좌표를 확인하세요")
