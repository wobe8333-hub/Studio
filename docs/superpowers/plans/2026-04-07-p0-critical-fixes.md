# P0 긴급 수정 구현 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** KAS 프로덕션 론칭 전 반드시 제거해야 할 Critical 버그 8개를 수정한다 — API 인증 없음, 경로 트래버설, PATCH 무검증, FFmpeg 반환값 무시, QA 프레임 추출 오류, chapter_markers 미삽입, dedup 경로 누락, Run 목록 페이지 부재.

**Architecture:** 보안 수정은 공유 유틸리티(`fs-helpers.ts`) → 3개 라우트 일괄 적용 → 미들웨어 순으로 진행. 파이프라인 버그는 최소 변경 원칙, pytest regression 방지. UX 단절은 신규 API + 페이지 추가.

**Tech Stack:** Python 3.8+, pytest, TypeScript 5, Next.js 16.2.2 App Router, Node.js `path` module, ffprobe (FFmpeg 번들)

---

## 파일 구조

| 파일 | 작업 | 목적 |
|------|------|------|
| `web/lib/fs-helpers.ts` | **신규** | channelId/runId 정규식 검증 + 경로 트래버설 방지 유틸리티 |
| `web/middleware.ts` | **신규** | Next.js 미들웨어 — proxy.ts 로직 활성화로 모든 /api/* 인증 적용 |
| `web/app/api/runs/[channelId]/route.ts` | **신규** | 채널별 Run 목록 JSON API |
| `web/app/runs/[channelId]/page.tsx` | **신규** | 채널별 Run 목록 UI (홈 채널 카드 링크 복원) |
| `web/app/api/runs/[channelId]/[runId]/seo/route.ts` | 수정 | 경로 트래버설 방지 + PATCH body 스키마 검증 |
| `web/app/api/runs/[channelId]/[runId]/bgm/route.ts` | 수정 | 경로 트래버설 방지 |
| `web/app/api/runs/[channelId]/[runId]/shorts/route.ts` | 수정 | 경로 트래버설 방지 |
| `src/step08/ffmpeg_composer.py` | 수정 | CRF=22 추가 + `add_subtitles` 실패 시 False 반환 |
| `src/step08/__init__.py` | 수정 | FFmpeg 3개 호출 반환값 검증 + RuntimeError 발생 |
| `src/step11/qa_gate.py` | 수정 | ffprobe로 실제 영상 길이 측정 (pct * 1.2 → pct/100 * duration) |
| `src/step08/metadata_generator.py` | 수정 | chapter_markers를 description 끝에 삽입 |
| `src/step05/dedup.py` | 수정 | `packages/` 하위 디렉토리 재귀 탐색 |
| `tests/test_step08_ffmpeg.py` | **신규** | FFmpeg composer 단위 테스트 |
| `tests/test_step08_metadata.py` | **신규** | 메타데이터 생성기 단위 테스트 |
| `tests/test_step11_qa.py` | **신규** | QA 게이트 단위 테스트 |
| `tests/test_step05_dedup.py` | **신규** | dedup 재귀 탐색 단위 테스트 |

---

### Task 1: 공유 경로 유효성 검사 유틸리티

**Files:**
- Create: `web/lib/fs-helpers.ts`

- [ ] **Step 1: 취약점 현황 확인**

현재 seo/bgm/shorts 라우트가 파라미터를 검증 없이 path.join에 사용하는지 확인:

```bash
cd web
grep -n "path.join" app/api/runs/\\[channelId\\]/\\[runId\\]/seo/route.ts
```

Expected output:
```
15:  const metaFile = path.join(kasRoot, 'runs', channelId, runId, 'step10', 'metadata.json')
```

`channelId`에 `../../etc/passwd`를 넣어도 아무 검증이 없음을 확인.

- [ ] **Step 2: `web/lib/fs-helpers.ts` 작성**

```typescript
import path from 'path'

const CHANNEL_ID_RE = /^CH[1-7]$/
const RUN_ID_RE     = /^run_CH[1-7]_\d{7,13}$/

/**
 * channelId / runId 형식 검증 후 허용된 kasRoot 하위 경로를 반환한다.
 * 형식 불일치 또는 경로 트래버설 시 null 반환.
 *
 * @param kasRoot  KAS_ROOT 환경변수 값
 * @param channelId URL 파라미터 (예: "CH1")
 * @param runId     URL 파라미터 (예: "run_CH1_1775143500")
 * @param ...sub    kasRoot/runs/{channelId}/{runId}/ 이후 경로 세그먼트
 * @returns         절대 경로 문자열, 또는 null (검증 실패)
 */
export function validateRunPath(
  kasRoot: string,
  channelId: string,
  runId: string,
  ...sub: string[]
): string | null {
  if (!CHANNEL_ID_RE.test(channelId)) return null
  if (!RUN_ID_RE.test(runId)) return null

  const allowedRoot = path.resolve(kasRoot)
  const requestedPath = path.resolve(
    path.join(kasRoot, 'runs', channelId, runId, ...sub)
  )

  if (!requestedPath.startsWith(allowedRoot + path.sep) &&
      requestedPath !== allowedRoot) {
    return null
  }

  return requestedPath
}

/**
 * channelId만 검증 (runs 목록 등 runId 없는 경우용).
 */
export function validateChannelPath(
  kasRoot: string,
  channelId: string,
  ...sub: string[]
): string | null {
  if (!CHANNEL_ID_RE.test(channelId)) return null

  const allowedRoot = path.resolve(kasRoot)
  const requestedPath = path.resolve(
    path.join(kasRoot, 'runs', channelId, ...sub)
  )

  if (!requestedPath.startsWith(allowedRoot + path.sep) &&
      requestedPath !== allowedRoot) {
    return null
  }

  return requestedPath
}
```

- [ ] **Step 3: TypeScript 컴파일 통과 확인**

```bash
cd web
npx tsc --noEmit
```

Expected: 오류 없이 종료 (exit code 0)

- [ ] **Step 4: 로직 검증 (node 스크립트)**

```bash
cd web
node -e "
const path = require('path');
const CHANNEL_ID_RE = /^CH[1-7]$/;
const RUN_ID_RE = /^run_CH[1-7]_\d{7,13}$/;
function validateRunPath(kasRoot, channelId, runId, ...sub) {
  if (!CHANNEL_ID_RE.test(channelId)) return null;
  if (!RUN_ID_RE.test(runId)) return null;
  const allowedRoot = path.resolve(kasRoot);
  const requestedPath = path.resolve(path.join(kasRoot, 'runs', channelId, runId, ...sub));
  if (!requestedPath.startsWith(allowedRoot + path.sep) && requestedPath !== allowedRoot) return null;
  return requestedPath;
}
// 정상 케이스
const r1 = validateRunPath('/kas', 'CH1', 'run_CH1_1234567890', 'step10', 'metadata.json');
console.assert(r1 !== null, 'FAIL: 정상 경로가 null 반환됨');
// 경로 트래버설
const r2 = validateRunPath('/kas', '../../etc', 'run_CH1_1234567890');
console.assert(r2 === null, 'FAIL: 트래버설 허용됨 channelId');
const r3 = validateRunPath('/kas', 'CH1', '../../etc/passwd');
console.assert(r3 === null, 'FAIL: 트래버설 허용됨 runId');
console.log('모든 검증 통과');
"
```

Expected: `모든 검증 통과`

- [ ] **Step 5: 커밋**

```bash
cd ..  # 프로젝트 루트
git add web/lib/fs-helpers.ts
git commit -m "feat: 경로 트래버설 방지 공유 유틸리티 fs-helpers.ts 추가"
```

---

### Task 2: API 라우트 경로 트래버설 방지 + SEO PATCH 검증

**Files:**
- Modify: `web/app/api/runs/[channelId]/[runId]/seo/route.ts`
- Modify: `web/app/api/runs/[channelId]/[runId]/bgm/route.ts`
- Modify: `web/app/api/runs/[channelId]/[runId]/shorts/route.ts`

- [ ] **Step 1: seo/route.ts 전면 교체**

```typescript
import { NextRequest, NextResponse } from 'next/server'
import fs from 'fs'
import { validateRunPath } from '@/lib/fs-helpers'

function getKasRoot(): string {
  return process.env.KAS_ROOT ?? require('path').join(process.cwd(), '..')
}

// SEO PATCH에서 허용할 최상위 키 목록 (임의 키 삽입 방지)
const ALLOWED_SEO_KEYS = new Set([
  'title', 'description', 'tags', 'category', 'thumbnail_url',
  'chapter_markers', 'selected_title', 'ab_variant',
])

export async function GET(
  _req: NextRequest,
  { params }: { params: Promise<{ channelId: string; runId: string }> }
) {
  const { channelId, runId } = await params
  const kasRoot = getKasRoot()

  const metaFile = validateRunPath(kasRoot, channelId, runId, 'step10', 'metadata.json')
  if (!metaFile) {
    return NextResponse.json({ error: '잘못된 채널 또는 Run ID' }, { status: 400 })
  }

  if (!fs.existsSync(metaFile)) {
    return NextResponse.json({ seo: null })
  }

  try {
    const raw = fs.readFileSync(metaFile, 'utf-8')
    const data = JSON.parse(raw)
    return NextResponse.json({ seo: data })
  } catch {
    return NextResponse.json({ error: 'metadata.json 파싱 오류' }, { status: 500 })
  }
}

export async function PATCH(
  req: NextRequest,
  { params }: { params: Promise<{ channelId: string; runId: string }> }
) {
  const { channelId, runId } = await params
  const kasRoot = getKasRoot()

  const metaFile = validateRunPath(kasRoot, channelId, runId, 'step10', 'metadata.json')
  if (!metaFile) {
    return NextResponse.json({ error: '잘못된 채널 또는 Run ID' }, { status: 400 })
  }

  if (!fs.existsSync(metaFile)) {
    return NextResponse.json({ error: 'metadata.json 없음' }, { status: 404 })
  }

  try {
    const body = await req.json()

    // 허용된 키만 필터링
    const safeBody: Record<string, unknown> = {}
    for (const [k, v] of Object.entries(body)) {
      if (ALLOWED_SEO_KEYS.has(k)) {
        safeBody[k] = v
      }
    }
    if (Object.keys(safeBody).length === 0) {
      return NextResponse.json({ error: '수정 가능한 필드가 없습니다' }, { status: 400 })
    }

    const raw = fs.readFileSync(metaFile, 'utf-8')
    const current = JSON.parse(raw)
    const updated = { ...current, ...safeBody, updated_at: new Date().toISOString() }
    fs.writeFileSync(metaFile, JSON.stringify(updated, null, 2), 'utf-8')
    return NextResponse.json({ ok: true, seo: updated })
  } catch {
    return NextResponse.json({ error: '저장 실패' }, { status: 500 })
  }
}
```

- [ ] **Step 2: bgm/route.ts 전면 교체**

```typescript
import { NextRequest, NextResponse } from 'next/server'
import fs from 'fs'
import { validateRunPath } from '@/lib/fs-helpers'

function getKasRoot(): string {
  return process.env.KAS_ROOT ?? require('path').join(process.cwd(), '..')
}

export async function GET(
  _req: NextRequest,
  { params }: { params: Promise<{ channelId: string; runId: string }> }
) {
  const { channelId, runId } = await params
  const kasRoot = getKasRoot()

  const reportFile = validateRunPath(kasRoot, channelId, runId, 'step09', 'render_report.json')
  if (!reportFile) {
    return NextResponse.json({ error: '잘못된 채널 또는 Run ID' }, { status: 400 })
  }

  if (!fs.existsSync(reportFile)) {
    return NextResponse.json({ bgm: null })
  }

  try {
    const raw = fs.readFileSync(reportFile, 'utf-8')
    const data = JSON.parse(raw)
    return NextResponse.json({ bgm: data })
  } catch {
    return NextResponse.json({ error: 'render_report.json 파싱 오류' }, { status: 500 })
  }
}
```

- [ ] **Step 3: shorts/route.ts 전면 교체**

```typescript
import { NextRequest, NextResponse } from 'next/server'
import fs from 'fs'
import { validateRunPath } from '@/lib/fs-helpers'

function getKasRoot(): string {
  return process.env.KAS_ROOT ?? require('path').join(process.cwd(), '..')
}

export async function GET(
  _req: NextRequest,
  { params }: { params: Promise<{ channelId: string; runId: string }> }
) {
  const { channelId, runId } = await params
  const kasRoot = getKasRoot()

  const shortsDir = validateRunPath(kasRoot, channelId, runId, 'step08_s')
  if (!shortsDir) {
    return NextResponse.json({ error: '잘못된 채널 또는 Run ID' }, { status: 400 })
  }

  if (!fs.existsSync(shortsDir)) {
    return NextResponse.json({ shorts: [] })
  }

  const files = fs.readdirSync(shortsDir).filter(f => f.endsWith('.mp4'))
  const shorts = files.map((f, i) => ({
    index: i + 1,
    filename: f,
    url: `/api/artifacts/${channelId}/${runId}/step08_s/${f}`,
  }))

  return NextResponse.json({ shorts })
}
```

> **주의**: shorts URL이 `/api/files/...`에서 `/api/artifacts/...`로 수정됨 (기존 shorts/route.ts의 `/api/files/` 경로는 존재하지 않는다 — CLAUDE.md 명시).

- [ ] **Step 4: TypeScript 컴파일 확인**

```bash
cd web
npx tsc --noEmit
```

Expected: exit code 0

- [ ] **Step 5: 커밋**

```bash
cd ..
git add web/app/api/runs/\\[channelId\\]/\\[runId\\]/seo/route.ts \
        web/app/api/runs/\\[channelId\\]/\\[runId\\]/bgm/route.ts \
        web/app/api/runs/\\[channelId\\]/\\[runId\\]/shorts/route.ts
git commit -m "fix: API 라우트 경로 트래버설 방지 + SEO PATCH 입력 스키마 검증"
```

---

### Task 3: API 인증 미들웨어 활성화

**Files:**
- Create: `web/middleware.ts`

**배경**: `web/proxy.ts`에 올바른 인증 로직이 있으나 Next.js는 반드시 `web/middleware.ts`에서 미들웨어를 export해야 한다. 현재 이 파일이 없어 모든 19개 API 라우트가 인증 없이 공개 상태다.

- [ ] **Step 1: 현재 middleware.ts가 없음을 확인**

```bash
ls web/middleware.ts 2>/dev/null && echo "EXISTS" || echo "NOT FOUND"
```

Expected: `NOT FOUND`

- [ ] **Step 2: `web/middleware.ts` 생성**

proxy.ts의 로직을 그대로 re-export한다. 이렇게 하면 proxy.ts의 로직은 그대로 유지하면서 Next.js가 미들웨어로 인식한다.

```typescript
export { proxy as middleware, config } from './proxy'
```

- [ ] **Step 3: TypeScript 컴파일 확인**

```bash
cd web
npx tsc --noEmit
```

Expected: exit code 0

- [ ] **Step 4: 개발 서버 동작 확인**

개발 서버(`npm run dev`)가 실행 중인 상태에서:

```bash
# DASHBOARD_PASSWORD 미설정 시 → 인증 bypass (개발 환경 의도된 동작)
curl -s -o /dev/null -w "%{http_code}" http://localhost:7002/api/pipeline/status
```

Expected: `200` (비밀번호 미설정 시 통과, proxy.ts L22 `if (!password) return NextResponse.next()`)

```bash
# DASHBOARD_PASSWORD 설정 후 쿠키 없이 접근 → /login 리다이렉트
DASHBOARD_PASSWORD=test123 node -e "
const http = require('http');
// 실제 확인은 next dev 재시작 후 브라우저에서 /api/* 직접 접근
console.log('미들웨어 파일 생성 완료. next dev 재시작 후 DASHBOARD_PASSWORD 설정하여 /api/pipeline/status 접근 시 /login 리다이렉트 확인');
"
```

- [ ] **Step 5: 커밋**

```bash
cd ..
git add web/middleware.ts
git commit -m "fix: API 인증 미들웨어 활성화 (proxy.ts re-export → middleware.ts 신규 생성)"
```

---

### Task 4: FFmpeg CRF 설정 + 반환값 검증

**Files:**
- Create: `tests/test_step08_ffmpeg.py`
- Modify: `src/step08/ffmpeg_composer.py`
- Modify: `src/step08/__init__.py`

**버그 1**: `image_to_clip`에 CRF 미지정 → 기본 CRF=23 (YouTube 권장 18-20).  
**버그 2**: `add_subtitles` 실패 시에도 `return True` → 자막 없는 영상이 다음 단계로 전달됨.  
**버그 3**: `__init__.py`에서 `concat_clips`, `add_narration`, `add_subtitles` 반환값 무시 → FFmpeg 실패해도 진행.

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/test_step08_ffmpeg.py` 생성:

```python
"""Step08 FFmpeg composer 단위 테스트."""
import subprocess
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest


def _load_ffmpeg_composer():
    """google.generativeai 체인 없이 ffmpeg_composer.py만 직접 로드."""
    import importlib.util, sys, types

    # google.generativeai mock (conftest.py와 동일한 패턴)
    if "google.generativeai" not in sys.modules:
        import google as _g
        m = types.ModuleType("google.generativeai")
        sys.modules["google.generativeai"] = m
        setattr(_g, "generativeai", m)

    spec = importlib.util.spec_from_file_location(
        "ffmpeg_composer",
        Path(__file__).parent.parent / "src" / "step08" / "ffmpeg_composer.py",
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


composer = _load_ffmpeg_composer()


class TestImageToClip:
    """image_to_clip CRF 설정 테스트."""

    def test_crf_22_in_command(self, tmp_path):
        """image_to_clip 커맨드에 -crf 22가 포함되어야 한다."""
        img = tmp_path / "test.png"
        img.write_bytes(b"fake_png")
        out = tmp_path / "out.mp4"

        captured_cmd = []

        def fake_run(cmd, **kwargs):
            captured_cmd.extend(cmd)
            r = MagicMock()
            r.returncode = 0
            return r

        with patch("subprocess.run", side_effect=fake_run):
            composer.image_to_clip(img, out, duration_sec=5.0)

        assert "-crf" in captured_cmd, "FFmpeg 커맨드에 -crf 플래그가 없음"
        crf_idx = captured_cmd.index("-crf")
        assert captured_cmd[crf_idx + 1] == "22", \
            f"CRF 값이 22가 아님: {captured_cmd[crf_idx + 1]}"

    def test_preset_medium_in_command(self, tmp_path):
        """-preset medium이 커맨드에 포함되어야 한다."""
        img = tmp_path / "test.png"
        img.write_bytes(b"fake_png")
        out = tmp_path / "out.mp4"

        captured_cmd = []

        def fake_run(cmd, **kwargs):
            captured_cmd.extend(cmd)
            r = MagicMock()
            r.returncode = 0
            return r

        with patch("subprocess.run", side_effect=fake_run):
            composer.image_to_clip(img, out)

        assert "-preset" in captured_cmd, "FFmpeg 커맨드에 -preset 플래그가 없음"
        preset_idx = captured_cmd.index("-preset")
        assert captured_cmd[preset_idx + 1] == "medium", \
            f"preset 값이 medium이 아님: {captured_cmd[preset_idx + 1]}"


class TestAddSubtitles:
    """add_subtitles 실패 시 False를 반환해야 한다."""

    def test_returns_false_on_ffmpeg_failure(self, tmp_path):
        """add_subtitles FFmpeg 실패 시 False를 반환해야 한다 (현재 True를 반환하는 버그)."""
        video = tmp_path / "video.mp4"
        video.write_bytes(b"fake_mp4")
        srt = tmp_path / "subs.srt"
        srt.write_text("1\n00:00:00,000 --> 00:00:01,000\n테스트\n\n", encoding="utf-8")
        out = tmp_path / "out.mp4"

        def fake_run_fail(cmd, **kwargs):
            r = MagicMock()
            r.returncode = 1
            r.stderr = "FFmpeg error"
            return r

        with patch("subprocess.run", side_effect=fake_run_fail):
            result = composer.add_subtitles(video, srt, out)

        assert result is False, \
            "add_subtitles FFmpeg 실패 시 False를 반환해야 하는데 True를 반환함 (버그)"
```

- [ ] **Step 2: 테스트 실패 확인**

```bash
pytest tests/test_step08_ffmpeg.py -v 2>&1 | head -40
```

Expected:
```
FAILED tests/test_step08_ffmpeg.py::TestImageToClip::test_crf_22_in_command - AssertionError: FFmpeg 커맨드에 -crf 플래그가 없음
FAILED tests/test_step08_ffmpeg.py::TestAddSubtitles::test_returns_false_on_ffmpeg_failure - AssertionError: add_subtitles FFmpeg 실패 시 False를 반환해야 하는데 True를 반환함 (버그)
```

- [ ] **Step 3: `src/step08/ffmpeg_composer.py` 수정**

`image_to_clip` 함수에 `-crf 22 -preset medium` 추가, `add_subtitles` 실패 시 `False` 반환:

```python
import subprocess, shutil
from loguru import logger
from pathlib import Path
from src.core.config import FFMPEG_PATH

def image_to_clip(image_path: Path, output_path: Path, duration_sec: float = 5.0) -> bool:
    cmd = [FFMPEG_PATH, "-y", "-loop", "1", "-i", str(image_path),
           "-t", str(duration_sec),
           "-vf", "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2",
           "-c:v", "libx264", "-crf", "22", "-preset", "medium",
           "-pix_fmt", "yuv420p", str(output_path)]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    if r.returncode != 0:
        logger.error(f"FFMPEG_IMAGE_TO_CLIP: {r.stderr[:300]}")
        return False
    return True

def concat_clips(clip_paths: list, output_path: Path) -> bool:
    lf = output_path.parent / "concat_list.txt"
    with open(lf, "w", encoding="utf-8") as f:
        for p in clip_paths:
            f.write(f"file '{p.as_posix()}'\n")
    cmd = [FFMPEG_PATH, "-y", "-f", "concat", "-safe", "0", "-i", str(lf),
           "-c", "copy", str(output_path)]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    lf.unlink(missing_ok=True)
    if r.returncode != 0:
        logger.error(f"FFMPEG_CONCAT: {r.stderr[:300]}")
        return False
    return True

def add_narration(video_path: Path, narration_path: Path, output_path: Path) -> bool:
    cmd = [FFMPEG_PATH, "-y", "-i", str(video_path), "-i", str(narration_path),
           "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest", str(output_path)]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    if r.returncode != 0:
        logger.error(f"FFMPEG_ADD_NARRATION: {r.stderr[:300]}")
        return False
    return True

def add_subtitles(video_path: Path, srt_path: Path, output_path: Path) -> bool:
    """자막 추가. FFmpeg 실패 시 fallback 없이 False 반환 (손상 없는 영상 보장)."""
    srt = srt_path.as_posix().replace(":", "\\:")
    cmd = [FFMPEG_PATH, "-y", "-i", str(video_path),
           "-vf", f"subtitles='{srt}'", "-c:a", "copy", str(output_path)]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    if r.returncode != 0:
        logger.warning(f"FFMPEG_SUBTITLES 실패 (자막 미추가): {r.stderr[:200]}")
        return False
    return True

def overlay_bgm(video_path: Path, bgm_path: Path, output_path: Path, bgm_volume: float = 0.08) -> bool:
    cmd = [FFMPEG_PATH, "-y", "-i", str(video_path), "-i", str(bgm_path),
           "-filter_complex",
           f"[1:a]volume={bgm_volume},aloop=loop=-1:size=2e+09[bgm];"
           "[0:a][bgm]amix=inputs=2:duration=first:dropout_transition=3[aout]",
           "-map", "0:v", "-map", "[aout]", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
           str(output_path)]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    if r.returncode != 0:
        logger.error(f"FFMPEG_BGM_OVERLAY: {r.stderr[:300]}")
        return False
    return True
```

- [ ] **Step 4: `src/step08/__init__.py` L161-178 반환값 검증 추가**

현재 코드 (`concat_clips(ordered_clips, concat_path)` 반환값 무시 부분)를 아래로 교체:

```python
    # 교체 대상: L161-178 (concat_path 생성부터 final_video까지)
    concat_path = step08_dir / "video_raw.mp4"
    if not concat_clips(ordered_clips, concat_path):
        raise RuntimeError(f"STEP08_FAIL: concat_clips 실패 — {channel_id}/{run_id}")
    if not concat_path.exists() or concat_path.stat().st_size == 0:
        raise RuntimeError(f"STEP08_FAIL: video_raw.mp4 생성 실패 — {channel_id}/{run_id}")

    logger.info(f"[STEP08] {channel_id}/{run_id} narration 생성 중...")
    narration_path = step08_dir / "narration.wav"
    generate_narration(script, narration_path, channel_id)

    with_narr = step08_dir / "video_narr.mp4"
    if not add_narration(concat_path, narration_path, with_narr):
        raise RuntimeError(f"STEP08_FAIL: add_narration 실패 — {channel_id}/{run_id}")
    if not with_narr.exists() or with_narr.stat().st_size == 0:
        raise RuntimeError(f"STEP08_FAIL: video_narr.mp4 생성 실패 — {channel_id}/{run_id}")

    srt_path = step08_dir / "subtitles.srt"
    generate_subtitles(script, narration_path, srt_path)

    with_subs = step08_dir / "video_subs.mp4"
    if not add_subtitles(with_narr, srt_path, with_subs):
        logger.warning(f"[STEP08] 자막 추가 실패 — narration 영상으로 진행: {channel_id}/{run_id}")
        with_subs = with_narr  # 자막 없이 진행 (업로드 차단 대신 경고)

    final_video = step08_dir / "video.mp4"
    shutil.copy2(with_subs, final_video)
```

> **설계 결정**: `add_subtitles` 실패 시 `RuntimeError`가 아닌 경고 후 자막 없는 영상으로 진행. 자막은 업로드 필수 조건이 아니며 QA에서 별도 확인함. `concat_clips`/`add_narration` 실패는 영상 자체가 없어 RuntimeError.

- [ ] **Step 5: 테스트 통과 확인**

```bash
pytest tests/test_step08_ffmpeg.py -v
```

Expected:
```
PASSED tests/test_step08_ffmpeg.py::TestImageToClip::test_crf_22_in_command
PASSED tests/test_step08_ffmpeg.py::TestImageToClip::test_preset_medium_in_command
PASSED tests/test_step08_ffmpeg.py::TestAddSubtitles::test_returns_false_on_ffmpeg_failure
```

- [ ] **Step 6: 커밋**

```bash
git add tests/test_step08_ffmpeg.py \
        src/step08/ffmpeg_composer.py \
        src/step08/__init__.py
git commit -m "fix: FFmpeg CRF=22 설정 + 반환값 검증 (concat/narration 실패 시 RuntimeError)"
```

---

### Task 5: QA Vision 프레임 추출 시간 계산 수정

**Files:**
- Create: `tests/test_step11_qa.py`
- Modify: `src/step11/qa_gate.py`

**버그**: `str(pct * 1.2)` — 영상이 120초라고 가정하여 고정 오프셋 사용. 실제 영상은 660-780초이므로 5%=6초, 90%=108초 위치만 추출됨 (최초 108초 범위만 검사).

**수정**: `ffprobe`로 실제 길이를 측정하여 `pct/100 * duration`으로 계산.

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/test_step11_qa.py` 생성:

```python
"""Step11 QA 게이트 — 프레임 추출 시간 계산 테스트."""
import subprocess
from pathlib import Path
from unittest.mock import patch, MagicMock, call
import pytest


def _load_qa_gate():
    import importlib.util, sys, types
    if "google.generativeai" not in sys.modules:
        import google as _g
        m = types.ModuleType("google.generativeai")
        sys.modules["google.generativeai"] = m
        setattr(_g, "generativeai", m)
    for mod_name in ["src.core.ssot", "src.core.config"]:
        if mod_name not in sys.modules:
            fake = types.ModuleType(mod_name)
            fake.read_json = lambda p: {}
            fake.write_json = lambda p, d: None
            fake.json_exists = lambda p: False
            fake.now_iso = lambda: "2026-01-01T00:00:00"
            fake.get_run_dir = lambda ch, run: Path("/tmp/fake")
            fake.GEMINI_API_KEY = "fake_key"
            fake.GEMINI_TEXT_MODEL = "gemini-2.0-flash"
            sys.modules[mod_name] = fake
    spec = importlib.util.spec_from_file_location(
        "qa_gate",
        Path(__file__).parent.parent / "src" / "step11" / "qa_gate.py",
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


qa_gate = _load_qa_gate()


class TestGeminiVisionFrameExtraction:
    """_gemini_vision_qa의 프레임 추출 시간 계산이 실제 영상 길이 기반이어야 한다."""

    def test_frame_time_uses_actual_duration_not_fixed_120s(self, tmp_path):
        """720초 영상의 50% 위치는 360초여야 한다 (현재: 50*1.2=60초 — 버그)."""
        video = tmp_path / "video.mp4"
        video.write_bytes(b"fake_mp4_content_720s")

        ffmpeg_calls = []

        def fake_run(cmd, **kwargs):
            ffmpeg_calls.append(cmd)
            r = MagicMock()
            r.returncode = 1  # 프레임 추출 실패 → 함수가 skipped 반환하도록
            r.stdout = ""
            r.stderr = ""
            return r

        with patch("subprocess.run", side_effect=fake_run), \
             patch.dict("os.environ", {"GEMINI_API_KEY": "fake"}):
            # ffprobe로 720초를 반환하는 mock
            original_run = subprocess.run

            call_count = [0]
            def smart_fake_run(cmd, **kwargs):
                call_count[0] += 1
                r = MagicMock()
                # 첫 번째 호출 = ffprobe (duration 측정)
                if "ffprobe" in str(cmd):
                    r.returncode = 0
                    r.stdout = "720.0"
                    r.stderr = ""
                else:
                    # ffmpeg frame extraction
                    ffmpeg_calls.append(cmd)
                    r.returncode = 1
                    r.stdout = ""
                    r.stderr = "error"
                return r

            with patch("subprocess.run", side_effect=smart_fake_run):
                qa_gate._gemini_vision_qa(video)

        # ffmpeg 프레임 추출 호출이 있었다면 -ss 값을 확인
        frame_cmds = [c for c in ffmpeg_calls if "ffmpeg" in str(c) or "-ss" in c]
        if frame_cmds:
            ss_values = []
            for cmd in frame_cmds:
                if "-ss" in cmd:
                    ss_idx = list(cmd).index("-ss")
                    ss_values.append(float(cmd[ss_idx + 1]))

            if ss_values:
                # 50% 위치: 기대값 360초 (720 * 0.50), 현재 버그값 60초 (50 * 1.2)
                assert any(s > 200 for s in ss_values), \
                    f"50% 프레임이 200초 이후에 추출되어야 하는데 실제 값: {ss_values}"

    def test_ffprobe_called_for_duration(self, tmp_path):
        """_gemini_vision_qa가 ffprobe를 호출하여 실제 영상 길이를 측정해야 한다."""
        video = tmp_path / "video.mp4"
        video.write_bytes(b"fake_mp4")

        subprocess_calls = []

        def fake_run(cmd, **kwargs):
            subprocess_calls.append(cmd)
            r = MagicMock()
            r.returncode = 0
            r.stdout = "720.0"
            r.stderr = ""
            return r

        with patch("subprocess.run", side_effect=fake_run):
            qa_gate._gemini_vision_qa(video)

        cmds_str = [str(c) for c in subprocess_calls]
        assert any("ffprobe" in c for c in cmds_str), \
            "ffprobe를 호출하지 않음 — 실제 영상 길이를 측정해야 한다"
```

- [ ] **Step 2: 테스트 실패 확인**

```bash
pytest tests/test_step11_qa.py::TestGeminiVisionFrameExtraction::test_ffprobe_called_for_duration -v
```

Expected:
```
FAILED ... AssertionError: ffprobe를 호출하지 않음 — 실제 영상 길이를 측정해야 한다
```

- [ ] **Step 3: `src/step11/qa_gate.py` 수정**

`_gemini_vision_qa` 함수 내부 프레임 추출 블록 (L44-64)을 다음으로 교체:

```python
        # ── 실제 영상 길이 측정 (ffprobe) ──────────────────────────────
        duration_cmd = [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(video_path),
        ]
        try:
            dur_result = subprocess.run(
                duration_cmd, capture_output=True, text=True, timeout=10
            )
            video_duration = float(dur_result.stdout.strip()) if dur_result.returncode == 0 else 120.0
        except Exception:
            video_duration = 120.0  # ffprobe 실패 시 fallback

        # ── 5프레임 추출 (0%, 25%, 50%, 75%, 90% 위치) ─────────────
        frames_dir = video_path.parent / "_qa_frames"
        frames_dir.mkdir(exist_ok=True)
        frame_files = []

        for i, pct in enumerate([5, 25, 50, 75, 90]):
            frame_path = frames_dir / f"frame_{i:02d}.jpg"
            seek_sec = pct / 100.0 * video_duration
            cmd = [
                "ffmpeg", "-y", "-ss", f"{seek_sec:.1f}",
                "-i", str(video_path),
                "-frames:v", "1",
                "-q:v", "2",
                str(frame_path),
            ]
            result = subprocess.run(cmd, capture_output=True, timeout=15)
            if result.returncode == 0 and frame_path.exists():
                frame_files.append(frame_path)
```

- [ ] **Step 4: 테스트 통과 확인**

```bash
pytest tests/test_step11_qa.py -v
```

Expected:
```
PASSED tests/test_step11_qa.py::TestGeminiVisionFrameExtraction::test_ffprobe_called_for_duration
```

- [ ] **Step 5: 커밋**

```bash
git add tests/test_step11_qa.py src/step11/qa_gate.py
git commit -m "fix: QA Vision 프레임 추출 시간 계산 — ffprobe로 실제 영상 길이 측정"
```

---

### Task 6: chapter_markers description 자동 삽입

**Files:**
- Create: `tests/test_step08_metadata.py`
- Modify: `src/step08/metadata_generator.py`

**버그**: `algorithm_policy.py`에서 `chapter_markers_required: True`, `chapter_min_count: 5`를 요구하고 스크립트에도 포함되지만, `generate_metadata()`가 description 생성 시 `seo.chapter_markers`를 삽입하지 않음.

YouTube 챕터 마커 형식 예시:
```
00:00 인트로
01:30 본론 시작
```

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/test_step08_metadata.py` 생성:

```python
"""Step08 metadata_generator — chapter_markers description 삽입 테스트."""
import json
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest


def _load_metadata_generator():
    import importlib.util, sys, types

    for mod_name in ["google.generativeai"]:
        if mod_name not in sys.modules:
            import google as _g
            m = types.ModuleType(mod_name)
            m.configure = lambda **kw: None
            m.GenerativeModel = MagicMock()
            m.GenerationConfig = MagicMock()
            sys.modules[mod_name] = m
            setattr(_g, "generativeai", m)

    for mod_name in ["src.quota.gemini_quota"]:
        if mod_name not in sys.modules:
            fake = types.ModuleType(mod_name)
            fake.throttle_if_needed = lambda: None
            fake.record_request = lambda: None
            sys.modules[mod_name] = fake

    spec = importlib.util.spec_from_file_location(
        "metadata_generator",
        Path(__file__).parent.parent / "src" / "step08" / "metadata_generator.py",
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


meta_gen = _load_metadata_generator()


class TestChapterMarkersInDescription:
    """generate_metadata가 chapter_markers를 description에 삽입해야 한다."""

    def _make_script_with_chapters(self) -> dict:
        return {
            "title_candidates": ["테스트 제목"],
            "seo": {
                "description_first_2lines": "설명 첫 두 줄 내용입니다.",
                "chapter_markers": [
                    {"time": "00:00", "title": "인트로"},
                    {"time": "01:30", "title": "본론 시작"},
                    {"time": "04:00", "title": "핵심 내용"},
                    {"time": "07:30", "title": "결론"},
                    {"time": "10:00", "title": "마무리"},
                ],
            },
            "affiliate_insert": {"text": "관련 링크"},
            "financial_disclaimer": "투자 주의 문구",
            "ai_label": "AI 제작 참여",
            "sections": [],
            "video_spec": {},
            "target_duration_sec": 720,
        }

    def test_chapter_markers_in_description_file(self, tmp_path):
        """description.txt에 00:00 형식의 챕터 마커가 포함되어야 한다."""
        script = self._make_script_with_chapters()
        topic = {"title": "테스트 주제"}

        # Gemini 태그 응답 mock
        mock_model = MagicMock()
        mock_resp = MagicMock()
        mock_resp.text = "태그1, 태그2, 태그3"
        mock_model.generate_content.return_value = mock_resp

        import google.generativeai as genai
        with patch.object(genai, "GenerativeModel", return_value=mock_model), \
             patch.object(genai, "configure"):
            meta_gen.generate_metadata("CH1", "run_CH1_test", script, tmp_path, topic)

        desc_path = tmp_path / "description.txt"
        assert desc_path.exists(), "description.txt가 생성되지 않음"

        content = desc_path.read_text(encoding="utf-8")
        assert "00:00" in content, \
            "description.txt에 챕터 마커(00:00)가 없음 — generate_metadata가 chapter_markers를 삽입해야 한다"
        assert "인트로" in content, "챕터 마커 제목 '인트로'가 description에 없음"

    def test_description_without_chapters_still_works(self, tmp_path):
        """chapter_markers가 없는 스크립트도 정상 처리되어야 한다."""
        script = {
            "title_candidates": ["제목"],
            "seo": {"description_first_2lines": "설명"},
            "affiliate_insert": {"text": ""},
            "financial_disclaimer": "",
            "ai_label": "AI 제작",
            "sections": [],
            "video_spec": {},
            "target_duration_sec": 720,
        }
        topic = {"title": "주제"}

        mock_model = MagicMock()
        mock_resp = MagicMock()
        mock_resp.text = "태그1, 태그2"
        mock_model.generate_content.return_value = mock_resp

        import google.generativeai as genai
        with patch.object(genai, "GenerativeModel", return_value=mock_model), \
             patch.object(genai, "configure"):
            # 예외 없이 완료되어야 함
            meta_gen.generate_metadata("CH1", "run_CH1_test", script, tmp_path, topic)

        assert (tmp_path / "description.txt").exists()
```

- [ ] **Step 2: 테스트 실패 확인**

```bash
pytest tests/test_step08_metadata.py::TestChapterMarkersInDescription::test_chapter_markers_in_description_file -v
```

Expected:
```
FAILED ... AssertionError: description.txt에 챕터 마커(00:00)가 없음
```

- [ ] **Step 3: `src/step08/metadata_generator.py` description 빌드 부분 수정**

`generate_metadata` 내 description 생성 블록(L38-48)을 다음으로 교체:

```python
    # 설명
    seo = script.get("seo", {})
    desc_first = seo.get("description_first_2lines", "")

    # chapter_markers 포맷: [{"time": "00:00", "title": "인트로"}, ...]
    chapters = seo.get("chapter_markers", [])
    chapter_block = ""
    if chapters:
        lines = [f"{c.get('time', '00:00')} {c.get('title', '')}" for c in chapters]
        chapter_block = "\n\n" + "\n".join(lines)

    description = (
        f"{desc_first}"
        f"{chapter_block}\n\n"
        f"▼ 관련 링크\n"
        f"─────────────────────────────\n"
        f"🔗 {script.get('affiliate_insert', {}).get('text', '')}\n\n"
        f"⚠️ {script.get('financial_disclaimer', '') or script.get('medical_disclaimer', '') or ''}\n\n"
        f"{script.get('ai_label', '이 영상은 AI가 제작에 참여했습니다.')}"
    )
    (step08_dir / "description.txt").write_text(description, encoding="utf-8")
```

- [ ] **Step 4: 테스트 통과 확인**

```bash
pytest tests/test_step08_metadata.py -v
```

Expected:
```
PASSED tests/test_step08_metadata.py::TestChapterMarkersInDescription::test_chapter_markers_in_description_file
PASSED tests/test_step08_metadata.py::TestChapterMarkersInDescription::test_description_without_chapters_still_works
```

- [ ] **Step 5: 커밋**

```bash
git add tests/test_step08_metadata.py src/step08/metadata_generator.py
git commit -m "fix: chapter_markers를 YouTube description에 자동 삽입"
```

---

### Task 7: dedup packages/ 하위 디렉토리 재귀 탐색

**Files:**
- Create: `tests/test_step05_dedup.py`
- Modify: `src/step05/dedup.py`

**버그**: `store_dir.glob("*.json")`은 루트 JSON만 탐색. `knowledge_package.py`가 `packages/` 하위 디렉토리에 저장하는 knowledge package 파일을 발견하지 못함 → 동일 주제 반복 생성 가능.

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/test_step05_dedup.py` 생성:

```python
"""Step05 dedup — packages/ 하위 디렉토리 재귀 탐색 테스트."""
import json
from pathlib import Path
import pytest
from unittest.mock import patch


class TestLoadExistingTopics:
    """_load_existing_topics가 packages/ 하위 JSON을 탐색해야 한다."""

    def test_finds_topics_in_packages_subdir(self, tmp_path, monkeypatch):
        """packages/ 하위 knowledge package를 기존 주제로 인식해야 한다."""
        from src.step05.dedup import _load_existing_topics, _normalize
        from src.core.config import DATA_DIR

        # 가상 knowledge_store 구조 생성
        store_dir = tmp_path / "knowledge_store" / "CH1"
        packages_dir = store_dir / "packages"
        packages_dir.mkdir(parents=True)

        # packages/ 하위에 knowledge package 저장 (knowledge_package.py와 동일 형식)
        pkg = {
            "channel_id": "CH1",
            "reinterpreted_title": "금리 인하의 경제적 영향",
            "topics": [],
        }
        (packages_dir / "pkg_001.json").write_text(
            json.dumps(pkg, ensure_ascii=False), encoding="utf-8"
        )

        # DATA_DIR을 tmp_path로 대체
        monkeypatch.setattr("src.step05.dedup.DATA_DIR", tmp_path)

        existing = _load_existing_topics("CH1")

        normalized_target = _normalize("금리 인하의 경제적 영향")
        assert normalized_target in existing, \
            f"packages/ 하위 주제 '{normalized_target}'이 기존 주제 목록에 없음. " \
            f"glob('*.json')이 재귀 탐색을 하지 않는 버그. 실제 존재 목록: {existing}"

    def test_root_json_still_found(self, tmp_path, monkeypatch):
        """루트 JSON 파일은 기존처럼 탐색되어야 한다."""
        from src.step05.dedup import _load_existing_topics, _normalize

        store_dir = tmp_path / "knowledge_store" / "CH1"
        store_dir.mkdir(parents=True)

        root_data = {"topic": "블랙홀의 비밀"}
        (store_dir / "topics.json").write_text(
            json.dumps(root_data, ensure_ascii=False), encoding="utf-8"
        )

        monkeypatch.setattr("src.step05.dedup.DATA_DIR", tmp_path)

        existing = _load_existing_topics("CH1")
        assert _normalize("블랙홀의 비밀") in existing, "루트 JSON 주제가 탐색되지 않음"


class TestDeduplicateTopics:
    """deduplicate_topics가 packages/ 하위 주제와 중복을 올바르게 감지해야 한다."""

    def test_duplicate_in_packages_subdir_is_removed(self, tmp_path, monkeypatch):
        """packages/ 하위에 있는 주제와 중복되는 후보는 제거되어야 한다."""
        from src.step05.dedup import deduplicate_topics

        store_dir = tmp_path / "knowledge_store" / "CH1"
        packages_dir = store_dir / "packages"
        packages_dir.mkdir(parents=True)

        pkg = {"reinterpreted_title": "금리인하경제영향"}
        (packages_dir / "pkg.json").write_text(
            json.dumps(pkg, ensure_ascii=False), encoding="utf-8"
        )

        monkeypatch.setattr("src.step05.dedup.DATA_DIR", tmp_path)

        # "금리인하경제영향"과 유사한 후보
        candidates = ["금리인하경제영향", "완전히 새로운 주제"]
        result = deduplicate_topics("CH1", candidates, similarity_threshold=0.75)

        assert "완전히 새로운 주제" in result, "새로운 주제가 필터링됨"
        assert "금리인하경제영향" not in result, \
            "packages/에 있는 주제와 동일한 후보가 제거되지 않음 (버그)"
```

- [ ] **Step 2: 테스트 실패 확인**

```bash
pytest tests/test_step05_dedup.py::TestLoadExistingTopics::test_finds_topics_in_packages_subdir -v
```

Expected:
```
FAILED ... AssertionError: packages/ 하위 주제 '금리인하의경제적영향'이 기존 주제 목록에 없음. glob('*.json')이 재귀 탐색을 하지 않는 버그.
```

- [ ] **Step 3: `src/step05/dedup.py` 수정**

`_load_existing_topics` 내 L29의 glob 패턴 변경:

```python
def _load_existing_topics(channel_id: str) -> Set[str]:
    """knowledge_store에서 기존 주제 목록 로드 (packages/ 하위 포함)."""
    store_dir = DATA_DIR / "knowledge_store" / channel_id
    if not store_dir.exists():
        return set()

    existing: Set[str] = set()
    # glob("*.json") → glob("**/*.json") : packages/ 하위 재귀 탐색
    for json_file in store_dir.glob("**/*.json"):
        try:
            data = read_json(json_file)
            # 단일 주제 파일
            if "topic" in data:
                existing.add(_normalize(data["topic"]))
            # 주제 목록 파일
            if "topics" in data:
                for t in data["topics"]:
                    if isinstance(t, str):
                        existing.add(_normalize(t))
                    elif isinstance(t, dict) and "reinterpreted_title" in t:
                        existing.add(_normalize(t["reinterpreted_title"]))
            # knowledge_package.py 형식: 루트에 reinterpreted_title
            if "reinterpreted_title" in data:
                existing.add(_normalize(data["reinterpreted_title"]))
        except Exception:
            pass

    return existing
```

- [ ] **Step 4: 테스트 통과 확인**

```bash
pytest tests/test_step05_dedup.py -v
```

Expected:
```
PASSED tests/test_step05_dedup.py::TestLoadExistingTopics::test_finds_topics_in_packages_subdir
PASSED tests/test_step05_dedup.py::TestLoadExistingTopics::test_root_json_still_found
PASSED tests/test_step05_dedup.py::TestDeduplicateTopics::test_duplicate_in_packages_subdir_is_removed
```

- [ ] **Step 5: 커밋**

```bash
git add tests/test_step05_dedup.py src/step05/dedup.py
git commit -m "fix: dedup glob을 재귀 탐색으로 변경하여 packages/ 하위 knowledge package 누락 수정"
```

---

### Task 8: /runs/{channelId} 목록 페이지 신규 생성

**Files:**
- Create: `web/app/api/runs/[channelId]/route.ts`
- Create: `web/app/runs/[channelId]/page.tsx`

**버그**: 홈 화면의 채널 카드가 `/runs/CH1` 등으로 링크하지만 해당 경로가 존재하지 않아 404. Run 상세 페이지의 "뒤로가기"도 동일하게 404.

- [ ] **Step 1: 404 현상 확인**

```bash
# 개발 서버가 실행 중이라면:
curl -s -o /dev/null -w "%{http_code}" http://localhost:7002/runs/CH1
```

Expected: `404`

- [ ] **Step 2: `web/app/api/runs/[channelId]/route.ts` 생성**

이 API는 특정 채널의 전체 Run 목록을 반환한다. 파일시스템의 `runs/{channelId}/` 하위 디렉토리를 스캔하여 각 Run의 `manifest.json` 요약을 반환한다.

```typescript
import { NextRequest, NextResponse } from 'next/server'
import fs from 'fs'
import path from 'path'
import { validateChannelPath } from '@/lib/fs-helpers'

function getKasRoot(): string {
  return process.env.KAS_ROOT ?? path.join(process.cwd(), '..')
}

export interface RunSummary {
  run_id: string
  run_state: 'RUNNING' | 'COMPLETED' | 'FAILED' | string
  created_at: string
  completed_at?: string
  topic_title?: string
  qa_pass?: boolean | null
}

export async function GET(
  _req: NextRequest,
  { params }: { params: Promise<{ channelId: string }> }
) {
  const { channelId } = await params
  const kasRoot = getKasRoot()

  const channelRunsDir = validateChannelPath(kasRoot, channelId)
  if (!channelRunsDir) {
    return NextResponse.json({ error: '잘못된 채널 ID' }, { status: 400 })
  }

  if (!fs.existsSync(channelRunsDir)) {
    return NextResponse.json({ runs: [] })
  }

  const entries = fs.readdirSync(channelRunsDir, { withFileTypes: true })
  const runs: RunSummary[] = []

  for (const entry of entries) {
    if (!entry.isDirectory() || !entry.name.startsWith('run_')) continue

    const runDir = path.join(channelRunsDir, entry.name)
    const manifestPath = path.join(runDir, 'manifest.json')

    if (!fs.existsSync(manifestPath)) continue

    try {
      const manifest = JSON.parse(fs.readFileSync(manifestPath, 'utf-8'))

      // QA 결과 (있으면 로드)
      let qa_pass: boolean | null = null
      const qaPath = path.join(runDir, 'step11', 'qa_result.json')
      if (fs.existsSync(qaPath)) {
        try {
          const qa = JSON.parse(fs.readFileSync(qaPath, 'utf-8'))
          qa_pass = qa.overall_pass ?? null
        } catch {
          // qa_result.json 파싱 실패 시 무시
        }
      }

      runs.push({
        run_id: manifest.run_id ?? entry.name,
        run_state: manifest.run_state ?? 'UNKNOWN',
        created_at: manifest.created_at ?? '',
        completed_at: manifest.completed_at,
        topic_title: manifest.topic?.reinterpreted_title ?? manifest.topic?.title,
        qa_pass,
      })
    } catch {
      // manifest.json 파싱 실패 시 스킵
    }
  }

  // 최신 Run이 먼저 오도록 정렬
  runs.sort((a, b) => b.created_at.localeCompare(a.created_at))

  return NextResponse.json({ runs, channel_id: channelId })
}
```

- [ ] **Step 3: API 동작 확인**

```bash
cd web && npm run build 2>&1 | tail -5
```

Expected: `✓ Compiled successfully` (오류 없음)

- [ ] **Step 4: `web/app/runs/[channelId]/page.tsx` 생성**

```tsx
'use client'

import { useState, useEffect } from 'react'
import { useParams } from 'next/navigation'
import Link from 'next/link'
import { ArrowLeft, CheckCircle2, XCircle, Loader2, Clock, PlayCircle } from 'lucide-react'
import type { RunSummary } from '@/app/api/runs/[channelId]/route'

const G = {
  card: {
    background: 'rgba(255,255,255,0.55)',
    backdropFilter: 'blur(20px)',
    WebkitBackdropFilter: 'blur(20px)',
    border: '1px solid rgba(238,36,0,0.12)',
    borderRadius: '1rem',
    boxShadow: '0 8px 32px rgba(144,0,0,0.08)',
  } as React.CSSProperties,
  text: { primary: '#1a0505', secondary: '#5c1a1a', muted: '#9b6060' },
}

function StateIcon({ state }: { state: string }) {
  if (state === 'COMPLETED') return <CheckCircle2 size={16} style={{ color: '#16a34a' }} />
  if (state === 'FAILED') return <XCircle size={16} style={{ color: '#dc2626' }} />
  if (state === 'RUNNING') return <Loader2 size={16} style={{ color: '#ca8a04' }} className="animate-spin" />
  return <Clock size={16} style={{ color: G.text.muted }} />
}

function QaBadge({ pass }: { pass: boolean | null }) {
  if (pass === null) return <span style={{ color: G.text.muted, fontSize: '0.75rem' }}>QA 미실행</span>
  if (pass) return <span style={{ color: '#16a34a', fontSize: '0.75rem', fontWeight: 600 }}>QA 통과</span>
  return <span style={{ color: '#dc2626', fontSize: '0.75rem', fontWeight: 600 }}>QA 실패</span>
}

export default function ChannelRunsPage() {
  const params = useParams()
  const channelId = params.channelId as string
  const [runs, setRuns] = useState<RunSummary[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetch(`/api/runs/${channelId}`)
      .then(r => r.json())
      .then(data => {
        if (data.error) throw new Error(data.error)
        setRuns(data.runs ?? [])
      })
      .catch(e => setError(e.message))
      .finally(() => setLoading(false))
  }, [channelId])

  return (
    <div style={{ padding: '2rem', maxWidth: '900px', margin: '0 auto' }}>
      {/* 헤더 */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', marginBottom: '2rem' }}>
        <Link href="/" style={{ color: G.text.muted, display: 'flex', alignItems: 'center', gap: '0.25rem', textDecoration: 'none' }}>
          <ArrowLeft size={16} />
          <span style={{ fontSize: '0.875rem' }}>홈</span>
        </Link>
        <h1 style={{ margin: 0, color: G.text.primary, fontSize: '1.5rem', fontFamily: 'var(--font-baskerville)' }}>
          {channelId} 실행 이력
        </h1>
      </div>

      {/* 로딩 */}
      {loading && (
        <div style={{ display: 'flex', justifyContent: 'center', padding: '4rem' }}>
          <Loader2 size={32} style={{ color: '#900000' }} className="animate-spin" />
        </div>
      )}

      {/* 오류 */}
      {error && (
        <div style={{ ...G.card, padding: '1.5rem', color: '#dc2626' }}>
          오류: {error}
        </div>
      )}

      {/* 빈 상태 */}
      {!loading && !error && runs.length === 0 && (
        <div style={{ ...G.card, padding: '3rem', textAlign: 'center' }}>
          <PlayCircle size={48} style={{ color: G.text.muted, margin: '0 auto 1rem' }} />
          <p style={{ color: G.text.primary, fontWeight: 600, margin: '0 0 0.5rem' }}>아직 실행 이력이 없습니다</p>
          <p style={{ color: G.text.muted, fontSize: '0.875rem', margin: 0 }}>
            파이프라인 실행 후 여기에 Run 목록이 표시됩니다.
          </p>
        </div>
      )}

      {/* Run 목록 */}
      {!loading && runs.length > 0 && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
          {runs.map(run => (
            <Link
              key={run.run_id}
              href={`/runs/${channelId}/${run.run_id}`}
              style={{ textDecoration: 'none' }}
            >
              <div
                style={{ ...G.card, padding: '1.25rem 1.5rem', cursor: 'pointer' }}
                onMouseEnter={e => (e.currentTarget.style.boxShadow = '0 12px 40px rgba(144,0,0,0.14)')}
                onMouseLeave={e => (e.currentTarget.style.boxShadow = G.card.boxShadow as string)}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                  {/* 좌측: Run 정보 */}
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.375rem' }}>
                      <StateIcon state={run.run_state} />
                      <span style={{ color: G.text.primary, fontWeight: 600, fontSize: '0.9rem',
                        overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                        {run.topic_title ?? run.run_id}
                      </span>
                    </div>
                    <div style={{ fontSize: '0.75rem', color: G.text.muted }}>
                      {run.run_id} · {run.created_at ? new Date(run.created_at).toLocaleString('ko-KR') : '-'}
                    </div>
                  </div>

                  {/* 우측: QA 배지 */}
                  <div style={{ marginLeft: '1rem', flexShrink: 0 }}>
                    <QaBadge pass={run.qa_pass} />
                  </div>
                </div>
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  )
}
```

- [ ] **Step 5: 빌드 통과 확인**

```bash
cd web
npm run build 2>&1 | tail -10
```

Expected: `✓ Compiled successfully` + `/runs/[channelId]` 라우트가 목록에 표시됨

- [ ] **Step 6: 커밋**

```bash
cd ..
git add web/app/api/runs/\\[channelId\\]/route.ts \
        web/app/runs/\\[channelId\\]/page.tsx
git commit -m "feat: 채널별 Run 목록 페이지 + API 신규 생성 (홈 채널 카드 링크 복원)"
```

---

## 자기 검토 (Self-Review)

### 스펙 커버리지 체크

| P0 항목 | 구현된 Task |
|---------|------------|
| 4.1 API 인증 미들웨어 | Task 3 — `web/middleware.ts` 신규 생성 |
| 4.2 경로 트래버설 방지 | Task 1+2 — `fs-helpers.ts` + 3개 라우트 적용 |
| 4.3 SEO PATCH 입력 검증 | Task 2 — `ALLOWED_SEO_KEYS` 필터링 |
| 1.2 FFmpeg 반환값 검증 | Task 4 — `__init__.py` RuntimeError + `add_subtitles` False 반환 |
| 8.1 FFmpeg CRF 설정 | Task 4 — `image_to_clip`에 `-crf 22 -preset medium` 추가 |
| 7.1 QA Vision 프레임 버그 | Task 5 — ffprobe로 실제 영상 길이 측정 |
| 7.2 chapter_markers 미삽입 | Task 6 — description에 마커 블록 삽입 |
| 9.1 dedup 경로 버그 | Task 7 — `glob("*.json")` → `glob("**/*.json")` |
| 3.1 runs 목록 페이지 | Task 8 — API + 페이지 신규 생성 |

모든 P0 항목 커버됨.

### 플레이스홀더 스캔

"TBD", "TODO", "나중에 구현" 없음. 모든 단계에 실제 코드 포함됨.

### 타입 일관성 체크

- `validateRunPath` / `validateChannelPath` — Task 1에서 정의, Task 2·8에서 동일 이름으로 사용 ✓
- `RunSummary` 인터페이스 — Task 8 API 라우트에서 export, 페이지에서 import ✓
- `G.card` / `G.text` 상수 패턴 — CLAUDE.md `monitor/page.tsx` 구조와 동일 ✓

---

## 실행 핸드오프

계획 저장 위치: `docs/superpowers/plans/2026-04-07-p0-critical-fixes.md`

**두 가지 실행 방식:**

**1. Subagent-Driven (권장)** — 태스크 단위로 신선한 서브에이전트 파견, 각 태스크 완료 후 검토

**2. Inline Execution** — 현재 세션에서 `superpowers:executing-plans` 스킬로 순차 실행

**어떤 방식으로 진행하시겠습니까?**
