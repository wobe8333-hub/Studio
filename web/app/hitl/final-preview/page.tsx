'use client'

import { useState, useEffect } from 'react'
import { Play, SkipForward, Loader2, ExternalLink } from 'lucide-react'

interface PreviewItem {
  episode_id: string
  channel_id: string
  title: string
  video_url: string | null
  duration_sec: number
  tags: string[]
  thumbnail_url: string | null
  upload_ready: boolean
}

export default function FinalPreviewPage() {
  const [items, setItems] = useState<PreviewItem[]>([])
  const [loading, setLoading] = useState(true)
  const [uploading, setUploading] = useState<string | null>(null)

  useEffect(() => {
    fetch('/api/hitl/final-preview')
      .then((r) => r.json())
      .then((data) => setItems(data.items ?? []))
      .catch(() => setItems([]))
      .finally(() => setLoading(false))
  }, [])

  const handleUpload = async (episodeId: string) => {
    setUploading(episodeId)
    await fetch('/api/hitl/final-preview', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ episode_id: episodeId, action: 'upload' }),
    })
    setUploading(null)
    setItems((prev) => prev.filter((i) => i.episode_id !== episodeId))
    alert(`${episodeId} 업로드가 시작되었습니다.`)
  }

  const handleSkip = async (episodeId: string) => {
    await fetch('/api/hitl/final-preview', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ episode_id: episodeId, action: 'auto_upload' }),
    })
    setItems((prev) => prev.filter((i) => i.episode_id !== episodeId))
  }

  const formatDuration = (sec: number) => {
    const m = Math.floor(sec / 60)
    const s = sec % 60
    return `${m}:${s.toString().padStart(2, '0')}`
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
        <h1 className="text-2xl font-bold">업로드 전 최종 프리뷰</h1>
        <p className="text-sm text-muted-foreground">
          영상을 확인 후 업로드하거나, Skip하면 자동으로 업로드됩니다. (Gate 3)
        </p>
      </div>

      {items.length === 0 ? (
        <div className="rounded-lg border border-dashed p-8 text-center text-muted-foreground">
          업로드 대기 중인 영상이 없습니다.
        </div>
      ) : (
        <div className="space-y-6">
          {items.map((item) => (
            <div key={item.episode_id} className="rounded-xl border p-5 space-y-4">
              <div className="flex items-start justify-between gap-4">
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-mono bg-muted px-2 py-0.5 rounded">
                      {item.channel_id}
                    </span>
                    <span className="text-xs text-muted-foreground">
                      {formatDuration(item.duration_sec)}
                    </span>
                  </div>
                  <h2 className="font-semibold">{item.title}</h2>
                </div>
                <span className="text-xs text-muted-foreground shrink-0">{item.episode_id}</span>
              </div>

              {item.video_url ? (
                <div className="rounded-lg overflow-hidden bg-black aspect-video">
                  <video
                    src={item.video_url}
                    controls
                    className="w-full h-full"
                    preload="metadata"
                  />
                </div>
              ) : (
                <div className="rounded-lg bg-muted aspect-video flex items-center justify-center text-muted-foreground">
                  <Play className="w-12 h-12 opacity-30" />
                  <span className="ml-2 text-sm">미리보기 URL 없음</span>
                </div>
              )}

              {item.tags.length > 0 && (
                <div className="flex flex-wrap gap-1.5">
                  {item.tags.slice(0, 8).map((tag) => (
                    <span
                      key={tag}
                      className="text-xs bg-muted px-2 py-0.5 rounded-full text-muted-foreground"
                    >
                      #{tag}
                    </span>
                  ))}
                  {item.tags.length > 8 && (
                    <span className="text-xs text-muted-foreground">+{item.tags.length - 8}개</span>
                  )}
                </div>
              )}

              <div className="flex gap-3">
                <button
                  onClick={() => handleUpload(item.episode_id)}
                  disabled={uploading === item.episode_id}
                  className="flex-1 py-2.5 rounded-lg bg-amber-500 text-white font-medium
                             hover:bg-amber-600 transition-colors flex items-center justify-center gap-2
                             disabled:opacity-40"
                >
                  {uploading === item.episode_id ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : (
                    <ExternalLink className="w-4 h-4" />
                  )}
                  지금 업로드
                </button>
                <button
                  onClick={() => handleSkip(item.episode_id)}
                  className="flex-1 py-2.5 rounded-lg bg-muted hover:bg-muted/80 font-medium
                             transition-colors flex items-center justify-center gap-2"
                >
                  <SkipForward className="w-4 h-4" />
                  Skip (자동 업로드)
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
