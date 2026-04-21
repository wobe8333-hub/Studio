'use client'

import { useState, useEffect } from 'react'
import { CheckCircle, XCircle, Edit3, Loader2 } from 'lucide-react'

interface SeriesItem {
  channel_id: string
  series_name: string
  episode_titles: string[]
  planned_week: string
}

interface ApprovalState {
  [key: string]: 'pending' | 'approved' | 'rejected'
}

export default function SeriesApprovalPage() {
  const [series, setSeries] = useState<SeriesItem[]>([])
  const [approvals, setApprovals] = useState<ApprovalState>({})
  const [loading, setLoading] = useState(true)
  const [submitting, setSubmitting] = useState(false)

  useEffect(() => {
    fetch('/api/hitl/series-plan')
      .then((r) => r.json())
      .then((data) => {
        setSeries(data.series ?? [])
        const init: ApprovalState = {}
        ;(data.series ?? []).forEach((s: SeriesItem) => {
          init[s.series_name] = 'pending'
        })
        setApprovals(init)
      })
      .catch(() => setSeries([]))
      .finally(() => setLoading(false))
  }, [])

  const handleApprove = (key: string) =>
    setApprovals((prev) => ({ ...prev, [key]: 'approved' }))
  const handleReject = (key: string) =>
    setApprovals((prev) => ({ ...prev, [key]: 'rejected' }))

  const handleSubmit = async () => {
    setSubmitting(true)
    await fetch('/api/hitl/series-plan', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ approvals }),
    })
    setSubmitting(false)
    alert('시리즈 승인 결과가 저장되었습니다.')
  }

  const allDecided = series.length > 0 && series.every((s) => approvals[s.series_name] !== 'pending')

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <Loader2 className="w-8 h-8 animate-spin text-amber-500" />
      </div>
    )
  }

  return (
    <div className="max-w-3xl mx-auto px-4 py-8 space-y-6">
      <div className="space-y-1">
        <h1 className="text-2xl font-bold">월간 시리즈 승인</h1>
        <p className="text-sm text-muted-foreground">
          이번 달 7채널 시리즈 기획을 검토하고 승인·거절해 주세요. (Gate 1)
        </p>
      </div>

      {series.length === 0 ? (
        <div className="rounded-lg border border-dashed p-8 text-center text-muted-foreground">
          승인 대기 중인 시리즈가 없습니다.
        </div>
      ) : (
        <div className="space-y-4">
          {series.map((s) => {
            const state = approvals[s.series_name]
            return (
              <div
                key={s.series_name}
                className={`rounded-xl border p-5 transition-colors ${
                  state === 'approved'
                    ? 'border-green-500 bg-green-500/5'
                    : state === 'rejected'
                      ? 'border-red-500 bg-red-500/5'
                      : 'border-border'
                }`}
              >
                <div className="flex items-start justify-between gap-4">
                  <div className="space-y-2 flex-1">
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-mono bg-muted px-2 py-0.5 rounded">
                        {s.channel_id}
                      </span>
                      <h2 className="font-semibold">{s.series_name}</h2>
                    </div>
                    <ul className="text-sm text-muted-foreground space-y-0.5 pl-2">
                      {s.episode_titles.map((t, i) => (
                        <li key={i} className="before:content-['•'] before:mr-1">
                          {t}
                        </li>
                      ))}
                    </ul>
                  </div>
                  <div className="flex gap-2 shrink-0">
                    <button
                      onClick={() => handleApprove(s.series_name)}
                      className="p-2 rounded-lg hover:bg-green-500/10 text-green-500 transition-colors"
                      title="승인"
                    >
                      <CheckCircle className="w-6 h-6" />
                    </button>
                    <button
                      onClick={() => handleReject(s.series_name)}
                      className="p-2 rounded-lg hover:bg-red-500/10 text-red-500 transition-colors"
                      title="거절"
                    >
                      <XCircle className="w-6 h-6" />
                    </button>
                  </div>
                </div>
              </div>
            )
          })}
        </div>
      )}

      {series.length > 0 && (
        <button
          onClick={handleSubmit}
          disabled={!allDecided || submitting}
          className="w-full py-3 rounded-xl bg-amber-500 text-white font-semibold
                     disabled:opacity-40 hover:bg-amber-600 transition-colors flex items-center justify-center gap-2"
        >
          {submitting && <Loader2 className="w-4 h-4 animate-spin" />}
          승인 결과 저장
        </button>
      )}
    </div>
  )
}
