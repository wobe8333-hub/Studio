import re
from datetime import timedelta
from pathlib import Path
from typing import List, Dict, Any


_TIME_RE = re.compile(r"^\d{2}:\d{2}:\d{2},\d{3}$")


def _format_time(seconds: float) -> str:
    td = timedelta(seconds=max(0.0, seconds))
    total_ms = int(td.total_seconds() * 1000)
    hours, rem = divmod(total_ms, 3600_000)
    minutes, rem = divmod(rem, 60_000)
    secs, ms = divmod(rem, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{ms:03d}"


def write_srt_for_sections(
    path: Path,
    sections: List[Dict[str, Any]],
    target_duration_sec: float,
) -> None:
    """
    섹션을 균등 분할하여 SRT 작성.
    """
    n = len(sections)
    if n <= 0:
        raise ValueError("sections must be non-empty")

    per = target_duration_sec / float(n)
    lines: List[str] = []
    for idx, section in enumerate(sections, start=1):
        start = per * (idx - 1)
        end = per * idx
        if idx == n:
            end = target_duration_sec
        start_str = _format_time(start)
        end_str = _format_time(end)
        heading = str(section.get("heading") or section.get("id") or f"Section {idx}")
        narration = str(section.get("narration_text") or "")
        text = narration if narration.strip() else heading

        lines.append(str(idx))
        lines.append(f"{start_str} --> {end_str}")
        lines.append(text)
        lines.append("")  # blank line

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines).strip() + "\n", encoding="utf-8")


def validate_srt_format(path: Path) -> bool:
    """
    간단한 정규식 검증: 타임라인 라인들이 SRT 형식을 만족하는지 확인.
    """
    text = path.read_text(encoding="utf-8", errors="ignore")
    lines = [l.rstrip("\n") for l in text.splitlines()]
    for i in range(1, len(lines), 4):
        if i >= len(lines):
            break
        if " --> " not in lines[i]:
            return False
        start, end = [s.strip() for s in lines[i].split(" --> ", 1)]
        if not (_TIME_RE.match(start) and _TIME_RE.match(end)):
            return False
    return True


def get_srt_last_end_time(path: Path) -> float:
    """
    마지막 자막 블록의 종료 시간을 초 단위로 파싱.
    """
    text = path.read_text(encoding="utf-8", errors="ignore")
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    last_time = None
    for i, line in enumerate(lines):
        if " --> " in line:
            last_time = line
    if not last_time:
        return 0.0
    _, end = [s.strip() for s in last_time.split(" --> ", 1)]
    h, m, rest = end.split(":", 2)
    s, ms = rest.split(",", 1)
    total_ms = (
        int(h) * 3600_000
        + int(m) * 60_000
        + int(s) * 1000
        + int(ms)
    )
    return total_ms / 1000.0

