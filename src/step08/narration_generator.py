import logging
from pathlib import Path
from gtts import gTTS
from src.core.config import GTTS_LANG

logger = logging.getLogger(__name__)

def generate_narration(script: dict, output_path: Path) -> bool:
    parts = [script.get("hook",{}).get("text",""), script.get("promise","")]
    for s in script.get("sections",[]): parts.append(s.get("narration_text",""))
    cta = script.get("cta",{}).get("text","")
    if cta: parts.append(cta)
    full_text = "\n\n".join(p for p in parts if p)
    try:
        tts = gTTS(text=full_text, lang=GTTS_LANG, slow=False)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        tts.save(str(output_path))
        logger.info(f"[STEP08] narration 완료: {output_path.name}")
        return True
    except Exception as e:
        logger.error(f"[STEP08] NARRATION_FAIL: {e}")
        return False
