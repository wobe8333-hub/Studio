'use client'

import { useEffect, useState } from 'react'
import { AlertTriangle, X } from 'lucide-react'
import { HitlSignal } from '@/lib/fs-helpers'

const TYPE_LABEL: Record<string, string> = {
  pytest_failure:   'pytest 실패',
  pipeline_failure: '파이프라인 실패',
  schema_mismatch:  '스키마 불일치',
}

export function HitlBanner() {
  const [signals, setSignals] = useState<HitlSignal[]>([])

  useEffect(() => {
    fetch('/api/hitl-signals')
      .then((r) => r.json())
      .then((data: HitlSignal[]) => setSignals(data))
      .catch(() => {/* 조용히 실패 */})
  }, [])

  async function dismiss(id: string) {
    await fetch('/api/hitl-signals', {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ id }),
    })
    setSignals((prev) => prev.filter((s) => s.id !== id))
  }

  if (signals.length === 0) return null

  return (
    <div className="px-4 md:px-6 pt-2 space-y-1.5">
      {signals.map((signal) => (
        <div
          key={signal.id}
          className="flex items-start gap-3 rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-2.5 text-sm glow-danger"
        >
          <AlertTriangle className="h-4 w-4 text-red-400 mt-0.5 shrink-0" />
          <div className="flex-1 min-w-0">
            <span className="font-semibold text-red-300">
              [{TYPE_LABEL[signal.type] ?? signal.type}]
            </span>{' '}
            <span className="text-red-200/80">
              {(signal.details as { error?: string; run_id?: string }).error
                ?? (signal.details as { run_id?: string }).run_id
                ?? '운영자 확인 필요'}
            </span>
            <span className="ml-2 text-red-400/60 text-xs">
              {signal.timestamp?.slice(0, 16).replace('T', ' ')}
            </span>
          </div>
          <button
            onClick={() => dismiss(signal.id)}
            className="shrink-0 text-red-400/60 hover:text-red-300 transition-colors"
            aria-label="닫기"
          >
            <X className="h-4 w-4" />
          </button>
        </div>
      ))}
    </div>
  )
}
