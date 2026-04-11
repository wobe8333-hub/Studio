import { NextRequest, NextResponse } from 'next/server'
import { spawn } from 'child_process'
import { getKasRoot, getPythonExecutable } from '@/lib/fs-helpers'

const AGENT_MAP: Record<string, string> = {
  // 기존 4개
  dev_maintenance:    'from src.agents.dev_maintenance import DevMaintenanceAgent; import json; print(json.dumps(DevMaintenanceAgent().run()))',
  analytics_learning: 'from src.agents.analytics_learning import AnalyticsLearningAgent; import json; print(json.dumps(AnalyticsLearningAgent().run()))',
  ui_ux:             'from src.agents.ui_ux import UiUxAgent; import json; print(json.dumps(UiUxAgent().run()))',
  video_style:       'from src.agents.video_style import VideoStyleAgent; import json; print(json.dumps(VideoStyleAgent().run()))',
  // 신규 2개
  script_quality:    'from src.agents.script_quality import ScriptQualityAgent; import json; print(json.dumps(ScriptQualityAgent().run()))',
  cost_optimizer:    'from src.agents.cost_optimizer import CostOptimizerAgent; import json; print(json.dumps(CostOptimizerAgent().run()))',
}

/** subprocess 실행 후 stdout/stderr/code를 항상 반환 (non-zero exit 무시) */
function runPython(script: string, cwd: string): Promise<{ stdout: string; stderr: string; code: number }> {
  return new Promise((resolve) => {
    // getPythonExecutable() — Windows Store 스텁 대신 py 런처 사용 (0xC0000142 방지)
    const proc = spawn(getPythonExecutable(), ['-c', script], {
      cwd,
      shell: true,
      env: { ...process.env, PYTHONIOENCODING: 'utf-8', PYTHONUTF8: '1' },
    })
    let stdout = ''
    let stderr = ''
    proc.stdout.on('data', (d: Buffer) => { stdout += d.toString() })
    proc.stderr.on('data', (d: Buffer) => { stderr += d.toString() })
    const timer = setTimeout(() => { proc.kill(); resolve({ stdout, stderr, code: -1 }) }, 120_000)
    proc.on('close', (code) => { clearTimeout(timer); resolve({ stdout, stderr, code: code ?? 0 }) })
  })
}

/**
 * POST /api/agents/run
 * body: { agent_id: 'dev_maintenance' | 'analytics_learning' | 'ui_ux' | 'video_style' }
 * KAS 루트에서 python -c "..." 로 Sub-Agent 실행 후 결과 반환.
 * pytest 내부 실패(non-zero exit)도 OK로 처리 — JSON 결과만 파싱.
 */
export async function POST(req: NextRequest) {
  const body = await req.json().catch(() => ({})) as Record<string, unknown>
  const agentId = String(body.agent_id ?? '')

  const script = AGENT_MAP[agentId]
  if (!script) {
    return NextResponse.json({ error: `알 수 없는 agent_id: ${agentId}` }, { status: 400 })
  }

  const kasRoot = getKasRoot()
  const { stdout, stderr, code } = await runPython(script, kasRoot)

  // 마지막 줄에 JSON 결과가 있음 (loguru 로그는 stderr로 분리됨)
  const lines = stdout.trim().split('\n').filter(Boolean)
  const lastLine = lines[lines.length - 1] ?? ''
  let result: unknown = null
  try { result = JSON.parse(lastLine) } catch { result = { raw: stdout.trim() } }

  return NextResponse.json({ ok: true, agent_id: agentId, exit_code: code, result })
}
