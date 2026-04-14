# scripts/generate_branding/intro_gen.py
"""영상 인트로 HTML 생성 — 3초, 채널 컬러 적용"""
import sys
import io

from pathlib import Path
from loguru import logger

sys.path.insert(0, str(Path(__file__).parent))
from config import CHANNELS, CHANNELS_DIR

# CH1 전용: 레퍼런스 crop PNG 분해 요소 기반 CSS keyframes 인트로
CH1_TEMPLATE = """<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="utf-8">
<style>
:root {{ --dur: 3s; }}
html, body {{ margin:0; height:100%; background:#FFFDF5; overflow:hidden; }}
.stage {{
  position: relative; width: 100vw; height: 100vh;
  display: flex; align-items: center; justify-content: center;
  animation: fade-out 0.3s calc(var(--dur) - 0.3s) ease-in forwards;
}}
.frame, .character, .text, .sparkle {{ position: absolute; }}
.frame {{
  width: 60vmin;
  animation: zoom-in 0.6s ease-out backwards;
}}
.character {{
  width: 42vmin;
  animation: pop 0.7s 0.4s ease-out backwards;
}}
.text {{
  width: 50vmin; bottom: 20vmin;
  animation: slide-up 0.5s 1.0s ease-out backwards;
}}
.sparkle.s1 {{
  width: 8vmin; top: 22vmin; left: 30vmin;
  animation: twinkle 1.2s 1.2s ease-in-out infinite;
}}
.sparkle.s2 {{
  width: 6vmin; top: 35vmin; right: 28vmin;
  animation: twinkle 1.2s 1.5s ease-in-out infinite;
}}
.sparkle.s3 {{
  width: 7vmin; bottom: 40vmin; left: 32vmin;
  animation: twinkle 1.2s 1.8s ease-in-out infinite;
}}
@keyframes zoom-in {{
  from {{ opacity: 0; transform: scale(0.2); }}
  to   {{ opacity: 1; transform: scale(1); }}
}}
@keyframes pop {{
  from {{ opacity: 0; transform: scale(0.4) translateY(10vh); }}
  to   {{ opacity: 1; transform: scale(1) translateY(0); }}
}}
@keyframes slide-up {{
  from {{ opacity: 0; transform: translateY(4vmin); }}
  to   {{ opacity: 1; transform: translateY(0); }}
}}
@keyframes twinkle {{
  0%, 100% {{ opacity: 0; transform: scale(0.3); }}
  50%       {{ opacity: 1; transform: scale(1); }}
}}
@keyframes fade-out {{
  to {{ opacity: 0; }}
}}
</style>
</head>
<body>
<div class="stage">
  <img class="frame"      src="intro_frame.png"     alt=""/>
  <img class="character"  src="intro_character.png" alt=""/>
  <img class="text"       src="intro_text.png"      alt="머니그래픽"/>
  <img class="sparkle s1" src="intro_sparkle.png"   alt=""/>
  <img class="sparkle s2" src="intro_sparkle.png"   alt=""/>
  <img class="sparkle s3" src="intro_sparkle.png"   alt=""/>
</div>
</body>
</html>"""

TEMPLATE = """<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{name} 인트로</title>
<style>
  * {{ margin:0; padding:0; box-sizing:border-box; }}
  body {{ width:1920px; height:1080px; background:{bg_color}; overflow:hidden;
          font-family:'Gmarket Sans', sans-serif; display:flex;
          align-items:center; justify-content:center; }}
  .logo-wrap {{ opacity:0; transform:translateX(-120px);
                animation:slideIn 0.6s cubic-bezier(.22,1,.36,1) 0.3s forwards; }}
  .logo-circle {{ width:220px; height:220px; border-radius:50%;
                  border:6px solid {main_color}; display:flex; align-items:center;
                  justify-content:center; position:relative; }}
  .logo-inner {{ width:196px; height:196px; border-radius:50%;
                 border:2px solid {main_color}; }}
  .channel-name {{ font-size:72px; font-weight:900; color:{main_color};
                   margin-left:32px; opacity:0;
                   animation:fadeUp 0.5s ease 0.9s forwards; }}
  .domain-tag {{ font-size:28px; color:{sub_color}; margin-top:8px; opacity:0;
                 animation:fadeUp 0.5s ease 1.2s forwards; }}
  .deco-line {{ position:absolute; bottom:180px; width:600px; height:3px;
                background:linear-gradient(90deg, transparent, {main_color}, transparent);
                opacity:0; animation:fadeIn 0.8s ease 1.5s forwards; }}
  @keyframes slideIn {{
    to {{ opacity:1; transform:translateX(0); }}
  }}
  @keyframes fadeUp {{
    from {{ opacity:0; transform:translateY(20px); }}
    to {{ opacity:1; transform:translateY(0); }}
  }}
  @keyframes fadeIn {{
    to {{ opacity:1; }}
  }}
</style>
</head>
<body>
  <div style="display:flex; align-items:center;">
    <div class="logo-wrap">
      <div class="logo-circle">
        <div class="logo-inner"></div>
      </div>
    </div>
    <div style="margin-left:40px;">
      <div class="channel-name">{name}</div>
      <div class="domain-tag">{domain}</div>
    </div>
  </div>
  <div class="deco-line"></div>
  <script>
    // 3초 후 자동 페이드아웃
    setTimeout(() => {{
      document.body.style.transition = "opacity 0.4s";
      document.body.style.opacity = "0";
    }}, 2600);
  </script>
</body>
</html>"""


def generate_intro(ch_id: str) -> None:
    cfg = CHANNELS[ch_id]
    out = CHANNELS_DIR / ch_id / "intro" / "intro.html"
    # CH1: 레퍼런스 crop PNG 분해 요소 기반 CSS keyframes 인트로
    if ch_id == "CH1":
        html = CH1_TEMPLATE
    else:
        html = TEMPLATE.format(
            name=cfg["name"],
            domain=cfg["domain"],
            main_color=cfg["main_color"],
            bg_color=cfg["bg_color"],
            sub_color=cfg["sub_colors"][0],
        )
    out.write_text(html, encoding="utf-8")
    logger.info(f"[OK] {ch_id} 인트로 → intro.html")


if __name__ == "__main__":
    for ch_id in CHANNELS:
        generate_intro(ch_id)
    logger.info("7채널 인트로 HTML 생성 완료")
