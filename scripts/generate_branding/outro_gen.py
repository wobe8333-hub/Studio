# scripts/generate_branding/outro_gen.py
"""영상 아웃트로 HTML — 10초, 구독·좋아요 CTA + 다음영상 카드"""
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from pathlib import Path
from loguru import logger

sys.path.insert(0, str(Path(__file__).parent))
from config import CHANNELS, CHANNELS_DIR

TEMPLATE = """<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<title>{name} 아웃트로</title>
<style>
  * {{ margin:0; padding:0; box-sizing:border-box; }}
  body {{ width:1920px; height:1080px; background:{bg_color};
          font-family:'Gmarket Sans', sans-serif; overflow:hidden; }}
  .top-msg {{ position:absolute; top:120px; left:50%; transform:translateX(-50%);
              font-size:56px; font-weight:900; color:{main_color}; text-align:center;
              opacity:0; animation:fadeUp 0.6s ease 0.3s forwards; }}
  .cta-wrap {{ position:absolute; top:320px; left:50%; transform:translateX(-50%);
               display:flex; gap:60px; opacity:0;
               animation:fadeUp 0.6s ease 1s forwards; }}
  .btn-sub {{ background:#FF0000; color:#fff; font-size:40px; font-weight:900;
              padding:28px 64px; border-radius:60px; border:4px solid #fff;
              animation:pulse 1.2s ease-in-out 2s infinite; }}
  .btn-like {{ background:{main_color}; color:{bg_text_color}; font-size:40px; font-weight:900;
               padding:28px 64px; border-radius:60px; border:4px solid {main_color}; }}
  .cards-wrap {{ position:absolute; bottom:80px; left:50%; transform:translateX(-50%);
                 display:flex; gap:48px; opacity:0;
                 animation:fadeUp 0.6s ease 3s forwards; }}
  .next-card {{ width:480px; height:270px; border:4px solid {main_color};
                border-radius:16px; background:rgba(0,0,0,0.15);
                display:flex; align-items:center; justify-content:center;
                font-size:28px; color:{main_color}; font-weight:700; text-align:center; }}
  @keyframes fadeUp {{
    from {{ opacity:0; transform:translateY(24px); }}
    to {{ opacity:1; transform:translateY(0); }}
  }}
  @keyframes pulse {{
    0%,100% {{ transform:scale(1); }}
    50% {{ transform:scale(1.06); }}
  }}
</style>
</head>
<body>
  <div class="top-msg">영상이 도움이 됐나요? 🙌</div>
  <div class="cta-wrap">
    <div class="btn-sub">🔔 구독</div>
    <div class="btn-like">👍 좋아요</div>
  </div>
  <div class="cards-wrap">
    <div class="next-card">다음 영상<br>추천 1</div>
    <div class="next-card">다음 영상<br>추천 2</div>
  </div>
  <script>
    // 10초 후 페이드아웃
    setTimeout(() => {{
      document.body.style.transition = "opacity 0.5s";
      document.body.style.opacity = "0";
    }}, 9500);
  </script>
</body>
</html>"""


def generate_outro(ch_id: str) -> None:
    cfg = CHANNELS[ch_id]
    # CH2 다크 배경은 밝은 텍스트 버튼 색
    bg_text_color = (
        "#000000"
        if cfg["bg_color"] in ("#FFFFFF", "#F5F0E0", "#F0F0F0")
        else "#FFFFFF"
    )
    html = TEMPLATE.format(
        name=cfg["name"],
        main_color=cfg["main_color"],
        bg_color=cfg["bg_color"],
        bg_text_color=bg_text_color,
    )
    out = CHANNELS_DIR / ch_id / "outro" / "outro.html"
    out.write_text(html, encoding="utf-8")
    logger.info(f"[OK] {ch_id} 아웃트로 → outro.html")


if __name__ == "__main__":
    for ch_id in CHANNELS:
        generate_outro(ch_id)
    logger.info("7채널 아웃트로 HTML 생성 완료")
