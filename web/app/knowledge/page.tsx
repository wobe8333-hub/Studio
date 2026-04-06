'use client'

import { useState, useEffect, useCallback } from 'react'
import { BookOpen, TrendingUp, Layers, Loader2, RefreshCw } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'
import type { ChannelKnowledge, KnowledgeTopic, SeriesEntry } from '@/app/api/knowledge/route'

const CHANNEL_LABELS: Record<string, string> = {
  CH1: '경제', CH2: '부동산', CH3: '심리',
  CH4: '미스터리', CH5: '전쟁사', CH6: '과학', CH7: '역사',
}

const GRADE_CLASS: Record<string, string> = {
  approved: 'bg-green-500/15 border-green-500/30 text-green-400',
  reject:   'bg-red-500/15 border-red-500/30 text-red-400',
}

function TopicRow({ topic }: { topic: KnowledgeTopic }) {
  return (
    <div className="flex items-start gap-3 py-2.5 border-b border-white/[0.04] last:border-0">
      <div className="flex-1 min-w-0">
        <p className="text-sm leading-snug truncate">{topic.reinterpreted_title || topic.original_topic}</p>
        <p className="text-xs text-muted-foreground mt-0.5">
          {topic.category} · {topic.trend_collected_at?.slice(0, 10)}
        </p>
      </div>
      <div className="flex items-center gap-2 shrink-0">
        <span className="text-xs text-muted-foreground">{topic.score.toFixed(1)}</span>
        <Badge className={cn('border text-xs', GRADE_CLASS[topic.grade] ?? 'border-white/20 text-white/60')}>
          {topic.grade}
        </Badge>
        {topic.is_trending && (
          <TrendingUp className="h-3.5 w-3.5 text-amber-400" />
        )}
      </div>
    </div>
  )
}

function SeriesCard({ series }: { series: SeriesEntry }) {
  return (
    <div className="rounded-lg border border-white/[0.06] bg-white/[0.02] px-4 py-3">
      <div className="flex items-center justify-between mb-2">
        <p className="text-sm font-medium">{series.series_name}</p>
        <Badge className="border border-amber-500/30 bg-amber-500/10 text-amber-400 text-xs">
          {series.episode_count}편
        </Badge>
      </div>
      <div className="space-y-1">
        {series.episodes.map((ep) => (
          <p key={ep.episode} className="text-xs text-muted-foreground">
            EP{ep.episode} — {ep.title}
          </p>
        ))}
      </div>
    </div>
  )
}

function ChannelKnowledgePanel({ ck }: { ck: ChannelKnowledge }) {
  const [tab, setTab] = useState<'topics' | 'series'>('topics')

  return (
    <Card className="glass-card">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="text-base flex items-center gap-2">
              <BookOpen className="h-4 w-4 text-amber-400" />
              {ck.channel_id} — {CHANNEL_LABELS[ck.channel_id] ?? ck.channel_id}
            </CardTitle>
            <CardDescription>
              트렌드 {ck.topics.length}개 · 시리즈 {ck.series.length}개
            </CardDescription>
          </div>
          <div className="flex gap-1">
            <Button
              size="sm"
              variant={tab === 'topics' ? 'default' : 'ghost'}
              onClick={() => setTab('topics')}
              className={cn('text-xs h-7', tab === 'topics' && 'bg-amber-500/15 border border-amber-500/30 text-amber-400')}
            >
              <TrendingUp className="h-3 w-3 mr-1" />트렌드
            </Button>
            <Button
              size="sm"
              variant={tab === 'series' ? 'default' : 'ghost'}
              onClick={() => setTab('series')}
              className={cn('text-xs h-7', tab === 'series' && 'bg-blue-500/15 border border-blue-500/30 text-blue-400')}
            >
              <Layers className="h-3 w-3 mr-1" />시리즈
            </Button>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        {tab === 'topics' && (
          ck.topics.length === 0 ? (
            <p className="text-sm text-muted-foreground text-center py-4">수집된 트렌드 없음</p>
          ) : (
            <div className="max-h-64 overflow-y-auto">
              {ck.topics.map((t, i) => <TopicRow key={i} topic={t} />)}
            </div>
          )
        )}
        {tab === 'series' && (
          ck.series.length === 0 ? (
            <p className="text-sm text-muted-foreground text-center py-4">등록된 시리즈 없음</p>
          ) : (
            <div className="space-y-3">
              {ck.series.map((s, i) => <SeriesCard key={i} series={s} />)}
            </div>
          )
        )}
      </CardContent>
    </Card>
  )
}

export default function KnowledgePage() {
  const [channels, setChannels] = useState<ChannelKnowledge[]>([])
  const [loading, setLoading] = useState(true)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const res = await fetch('/api/knowledge')
      const data: { channels: ChannelKnowledge[] } = await res.json()
      setChannels(data.channels.filter((c) => c.topics.length > 0 || c.series.length > 0))
    } catch { /* 무시 */ } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { load() }, [load])

  return (
    <div className="relative space-y-6 ambient-bg overflow-hidden">
      <div className="flex items-center justify-between">
        <div>
          <div className="flex items-center gap-2">
            <BookOpen className="h-5 w-5" />
            <h1 className="text-2xl font-bold tracking-tight">지식 수집</h1>
          </div>
          <p className="text-muted-foreground text-sm mt-1">
            채널별 트렌드 토픽 및 시리즈 계획
          </p>
        </div>
        <Button
          size="sm"
          variant="ghost"
          onClick={load}
          disabled={loading}
          className="text-muted-foreground"
        >
          <RefreshCw className={cn('h-4 w-4', loading && 'animate-spin')} />
        </Button>
      </div>

      {loading ? (
        <div className="flex items-center justify-center h-48">
          <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
        </div>
      ) : channels.length === 0 ? (
        <Card className="glass-card">
          <CardContent className="py-12 text-center text-muted-foreground text-sm">
            지식 수집 데이터가 없습니다. 파이프라인을 실행하면 데이터가 표시됩니다.
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-4">
          {channels.map((ck) => (
            <ChannelKnowledgePanel key={ck.channel_id} ck={ck} />
          ))}
        </div>
      )}
    </div>
  )
}
