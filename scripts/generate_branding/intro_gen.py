# scripts/generate_branding/intro_gen.py
"""영상 인트로 HTML 생성 — 3초, 채널 컬러 적용"""
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
    html = TEMPLATE.format(
        name=cfg["name"],
        domain=cfg["domain"],
        main_color=cfg["main_color"],
        bg_color=cfg["bg_color"],
        sub_color=cfg["sub_colors"][0],
    )
    out = CHANNELS_DIR / ch_id / "intro" / "intro.html"
    out.write_text(html, encoding="utf-8")
    logger.info(f"[OK] {ch_id} 인트로 → intro.html")


if __name__ == "__main__":
    for ch_id in CHANNELS:
        generate_intro(ch_id)
    logger.info("7채널 인트로 HTML 생성 완료")
