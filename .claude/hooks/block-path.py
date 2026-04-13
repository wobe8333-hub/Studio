#!/usr/bin/env python3
"""
PreToolUse 경로 차단 hook.

Usage: python .claude/hooks/block-path.py /path1/ /path2/ ...
stdin:  Claude Code PreToolUse 이벤트 JSON
exit 2: 차단 (도구 실행 중단)
exit 0: 허용 (도구 실행 계속)

예시:
  backend-engineer:   python .claude/hooks/block-path.py /web/
  frontend-engineer:  python .claude/hooks/block-path.py /src/ globals.css
  db-architect:       python .claude/hooks/block-path.py /src/step /web/app/ /web/components/
"""
from __future__ import annotations
import sys
import json

blocked_paths: list[str] = sys.argv[1:]

if not blocked_paths:
    # 인자 없으면 모두 허용
    sys.exit(0)

try:
    data: dict = json.loads(sys.stdin.read())
    file_path: str = data.get("input", {}).get("file_path", "").replace("\\", "/")
except (json.JSONDecodeError, AttributeError):
    sys.exit(0)

for blocked in blocked_paths:
    if blocked in file_path:
        print(
            f"[block-path] BLOCKED: {file_path!r} contains {blocked!r}",
            file=sys.stderr,
        )
        sys.exit(2)

sys.exit(0)
