# scripts/generate_branding/outro_gen.py
"""영상 아웃트로 HTML — 10초, 구독·좋아요 CTA + 다음영상 카드"""
import io
import sys
from pathlib import Path

from loguru import logger

sys.path.insert(0, str(Path(__file__).parent))
from config import CHANNELS, CHANNELS_DIR


def _build_ch1_outro() -> str:
    """CH1 전용: 레퍼런스 crop PNG 분해 요소 기반 지폐 낙하 CSS keyframes 아웃트로 (10초)."""
    # 지폐 20장 — 각기 다른 left·delay·duration으로 무한 낙하
    BILL_PARAMS = [
        (5,  0.0, 4.0), (12, 0.5, 5.0), (20, 1.2, 4.5), (28, 0.3, 5.0),
        (35, 2.0, 4.2), (43, 0.8, 4.8), (50, 1.5, 5.2), (58, 2.3, 4.5),
        (65, 0.2, 5.0), (72, 1.0, 4.3), (80, 1.8, 5.5), (88, 0.5, 4.6),
        (10, 2.5, 4.8), (25, 0.7, 5.3), (40, 1.3, 4.4), (55, 2.1, 5.1),
        (68, 0.4, 4.7), (78, 1.7, 5.4), (92, 2.2, 4.5), (15, 1.1, 5.2),
    ]
    bills = "\n".join(
        f'  <img class="bill" style="left:{left}%;animation:fly {dur}s {delay}s linear infinite;" src="outro_bill.png" alt=""/>'
        for left, delay, dur in BILL_PARAMS
    )
    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="utf-8">
<style>
:root {{ --dur: 10s; }}
html, body {{ margin: 0; height: 100%; background: #FFFFFF; overflow: hidden; }}
.stage {{
  position: relative; width: 100vw; height: 100vh;
  animation: fade-out 0.4s calc(var(--dur) - 0.4s) ease-in forwards;
}}
.bg {{
  position: absolute; inset: 0; width: 100%; height: 100%;
  object-fit: cover; opacity: 0.35;
}}
.bill {{
  position: absolute; width: 14vmin; top: -20vmin; will-change: transform, opacity;
}}
.character {{
  position: absolute; left: 50%; top: 55%;
  transform: translate(-50%, -50%); width: 38vmin;
  animation: bounce 1.2s 0.3s ease-out backwards, breathe 2s 1.5s ease-in-out infinite;
}}
.cta {{
  position: absolute; left: 50%; bottom: 10vmin;
  transform: translateX(-50%); width: 60vmin;
  animation: slide-up 0.6s 1.2s ease-out backwards, pulse 1.5s 2s ease-in-out infinite;
}}
@keyframes fly {{
  0%   {{ transform: translateY(0) rotate(0deg); opacity: 0; }}
  10%  {{ opacity: 1; }}
  100% {{ transform: translateY(130vh) rotate(720deg); opacity: 0; }}
}}
@keyframes bounce {{
  from {{ opacity: 0; transform: translate(-50%, -30%) scale(0.6); }}
  to   {{ opacity: 1; transform: translate(-50%, -50%) scale(1); }}
}}
@keyframes breathe {{
  0%, 100% {{ transform: translate(-50%, -50%) scale(1); }}
  50%       {{ transform: translate(-50%, -50%) scale(1.03); }}
}}
@keyframes slide-up {{
  from {{ opacity: 0; transform: translate(-50%, 30%); }}
  to   {{ opacity: 1; transform: translateX(-50%) translateY(0); }}
}}
@keyframes pulse {{
  0%, 100% {{ filter: brightness(1); }}
  50%       {{ filter: brightness(1.15); }}
}}
@keyframes fade-out {{
  to {{ opacity: 0; }}
}}
</style>
</head>
<body>
<div class="stage">
  <img class="bg" src="outro_background.png" alt=""/>
{bills}
  <img class="character" src="outro_character.png" alt=""/>
  <img class="cta"       src="outro_cta.png"       alt="구독 좋아요"/>
</div>
</body>
</html>"""


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
    out = CHANNELS_DIR / ch_id / "outro" / "outro.html"
    # CH1: 레퍼런스 crop PNG 분해 요소 기반 지폐 낙하 CSS keyframes 아웃트로
    if ch_id == "CH1":
        html = _build_ch1_outro()
    else:
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
    out.write_text(html, encoding="utf-8")
    logger.info(f"[OK] {ch_id} 아웃트로 → outro.html")


if __name__ == "__main__":
    if hasattr(sys.stdout, "buffer"):
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    for ch_id in CHANNELS:
        generate_outro(ch_id)
    logger.info("7채널 아웃트로 HTML 생성 완료")
