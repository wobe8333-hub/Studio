'use client'

import { useState, useEffect } from 'react'
import Image from 'next/image'
import { Ban, CheckCircle2, Loader2, Info } from 'lucide-react'

interface ThumbnailSet {
  episode_id: string
  channel_id: string
  title: string
  thumbnail_urls: string[]
  status: 'pending' | 'ok' | 'blocked'
}

export default function ThumbnailVetoPage() {
  const [sets, setSets] = useState<ThumbnailSet[]>([])
  const [loading, setLoading] = useState(true)
  const [decisions, setDecisions] = useState<Record<string, 'ok' | 'blocked'>>({})
  const [submitting, setSubmitting] = useState(false)

  useEffect(() => {
    fetch('/api/hitl/thumbnail-veto')
      .then((r) => r.json())
      .then((data) => setSets(data.sets ?? []))
      .catch(() => setSets([]))
      .finally(() => setLoading(false))
  }, [])

  const decide = (id: string, verdict: 'ok' | 'blocked') =>
    setDecisions((prev) => ({ ...prev, [id]: verdict }))

  const handleSubmit = async () => {
    setSubmitting(true)
    await fetch('/api/hitl/thumbnail-veto', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ decisions }),
    })
    setSubmitting(false)
    alert('거부권 결과가 저장되었습니다. YouTube가 72h 내 최고 CTR 변형을 자동 채택합니다.')
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <Loader2 className="w-8 h-8 animate-spin text-amber-500" />
      </div>
    )
  }

  return (
    <div className="max-w-4xl mx-auto px-4 py-8 space-y-6">
      <div className="space-y-1">
        <h1 className="text-2xl font-bold">썸네일 거부권 검토</h1>
        <div className="flex items-start gap-2 text-sm text-muted-foreground bg-amber-500/10 border border-amber-500/20 rounded-lg p-3">
          <Info className="w-4 h-4 text-amber-500 shrink-0 mt-0.5" />
          <p>
            3종 썸네일이 YouTube에 자동 업로드됩니다. 어떤 이미지가 더 나은지 고민하실 필요 없습니다 —
            YouTube 알고리즘이 72시간 내 최고 CTR 변형을 자동 채택합니다.
            <br />
            <strong>정책 위반 등 심각한 문제가 있는 경우에만 전면 차단</strong>해 주세요.
          </p>
        </div>
      </div>

      {sets.length === 0 ? (
        <div className="rounded-lg border border-dashed p-8 text-center text-muted-foreground">
          검토 대기 중인 썸네일이 없습니다.
        </div>
      ) : (
        <div className="space-y-8">
          {sets.map((s) => {
            const verdict = decisions[s.episode_id]
            return (
              <div
                key={s.episode_id}
                className={`rounded-xl border p-5 space-y-4 transition-colors ${
                  verdict === 'blocked'
                    ? 'border-red-500 bg-red-500/5'
                    : verdict === 'ok'
                      ? 'border-green-500 bg-green-500/5'
                      : 'border-border'
                }`}
              >
                <div className="flex items-center justify-between">
                  <div>
                    <span className="text-xs font-mono bg-muted px-2 py-0.5 rounded mr-2">
                      {s.channel_id}
                    </span>
                    <span className="font-semibold">{s.title}</span>
                  </div>
                  <span className="text-xs text-muted-foreground">{s.episode_id}</span>
                </div>

                <div className="grid grid-cols-3 gap-3">
                  {s.thumbnail_urls.map((url, i) => (
                    <div key={i} className="aspect-video relative rounded-lg overflow-hidden bg-muted">
                      {url ? (
                        <Image
                          src={url}
                          alt={`썸네일 변형 ${i + 1}`}
                          fill
                          className="object-cover"
                        />
                      ) : (
                        <div className="flex items-center justify-center h-full text-xs text-muted-foreground">
                          변형 {i + 1}
                        </div>
                      )}
                      <div className="absolute bottom-1 left-1 text-xs bg-black/60 text-white px-1.5 py-0.5 rounded">
                        변형 {i + 1}
                      </div>
                    </div>
                  ))}
                </div>

                <div className="flex gap-3">
                  <button
                    onClick={() => decide(s.episode_id, 'ok')}
                    className={`flex-1 py-2.5 rounded-lg font-medium transition-colors flex items-center justify-center gap-2 ${
                      verdict === 'ok'
                        ? 'bg-green-500 text-white'
                        : 'bg-muted hover:bg-green-500/10 text-green-600'
                    }`}
                  >
                    <CheckCircle2 className="w-4 h-4" />
                    문제 없음 (10초 확인)
                  </button>
                  <button
                    onClick={() => decide(s.episode_id, 'blocked')}
                    className={`flex-1 py-2.5 rounded-lg font-medium transition-colors flex items-center justify-center gap-2 ${
                      verdict === 'blocked'
                        ? 'bg-red-500 text-white'
                        : 'bg-muted hover:bg-red-500/10 text-red-600'
                    }`}
                  >
                    <Ban className="w-4 h-4" />
                    전면 차단 (정책 위반)
                  </button>
                </div>
              </div>
            )
          })}
        </div>
      )}

      {sets.length > 0 && (
        <button
          onClick={handleSubmit}
          disabled={Object.keys(decisions).length === 0 || submitting}
          className="w-full py-3 rounded-xl bg-amber-500 text-white font-semibold
                     disabled:opacity-40 hover:bg-amber-600 transition-colors flex items-center justify-center gap-2"
        >
          {submitting && <Loader2 className="w-4 h-4 animate-spin" />}
          결정 저장
        </button>
      )}
    </div>
  )
}
