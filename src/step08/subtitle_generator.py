import logging
from pathlib import Path
from pydub import AudioSegment

logger = logging.getLogger(__name__)

def generate_subtitles(script: dict, narration_path: Path, output_path: Path) -> bool:
    try:
        total_ms = len(AudioSegment.from_file(str(narration_path)))
    except Exception:
        total_ms = script.get("target_duration_sec",720) * 1000
    texts = []
    hook  = script.get("hook",{})
    if hook.get("text"): texts.append(("Hook", hook["text"]))
    for s in script.get("sections",[]):
        if s.get("narration_text"): texts.append((s.get("heading",""), s["narration_text"]))
    if not texts: return False
    per_ms    = total_ms // len(texts)
    srt_lines = []
    def ms2srt(ms):
        h=ms//3600000; m=(ms%3600000)//60000; s=(ms%60000)//1000; r=ms%1000
        return f"{h:02d}:{m:02d}:{s:02d},{r:03d}"
    for i,(heading,text) in enumerate(texts):
        srt_lines += [str(i+1), f"{ms2srt(i*per_ms)} --> {ms2srt(min((i+1)*per_ms,total_ms))}",
                      text[:80]+("..." if len(text)>80 else ""), ""]
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(srt_lines), encoding="utf-8")
    return True
