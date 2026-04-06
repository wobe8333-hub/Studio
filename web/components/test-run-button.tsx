'use client'
import { useState } from 'react'

const CHANNELS = ['CH1', 'CH2', 'CH3', 'CH4', 'CH5', 'CH6', 'CH7']

export function TestRunButton() {
  const [loading, setLoading] = useState(false)
  const [channelId, setChannelId] = useState('CH1')

  async function handleClick() {
    setLoading(true)
    try {
      await fetch('/api/pipeline/trigger', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ channel_id: channelId, month_number: 1, dry_run: true }),
      })
      window.location.href = '/monitor'
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex items-center gap-2">
      <select
        value={channelId}
        onChange={e => setChannelId(e.target.value)}
        className="rounded-lg px-3 py-2 text-sm outline-none cursor-pointer"
        style={{
          background: 'rgba(255,255,255,0.55)',
          backdropFilter: 'blur(20px)',
          border: '1px solid rgba(238,36,0,0.12)',
          color: '#5c1a1a',
        }}
      >
        {CHANNELS.map(ch => (
          <option key={ch} value={ch}>{ch}</option>
        ))}
      </select>
      <button
        onClick={handleClick}
        disabled={loading}
        className="flex items-center gap-2 rounded-lg px-4 py-2 text-sm font-semibold transition-all disabled:opacity-60"
        style={{
          background: loading ? 'rgba(144,0,0,0.5)' : '#900000',
          color: '#ffefea',
          boxShadow: '0 4px 16px rgba(144,0,0,0.3)',
        }}
      >
        {loading ? (
          <>
            <span className="h-3.5 w-3.5 rounded-full border-2 border-[#ffefea]/30 border-t-[#ffefea] animate-spin" />
            실행 중...
          </>
        ) : (
          <>▶ 테스트 런</>
        )}
      </button>
    </div>
  )
}
