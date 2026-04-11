'use client'

import { useState, useMemo, useEffect, useTransition } from 'react'
import { TrendingUp, CheckCircle, XCircle, Clock, ThumbsUp, ThumbsDown, Filter } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { createClient } from '@/lib/supabase/client'
import { updateTopicGrade } from './actions'

type Grade = 'auto' | 'review' | 'approved' | 'rejected'

interface Breakdown {
  interest: number
  fit: number
  revenue: number
  urgency: number
}

interface Topic {
  id: number
  channel_id: string
  reinterpreted_title: string
  score: number
  grade: Grade
  is_trending: boolean
  topic_type: string
  breakdown?: Breakdown
}

// Supabase 미연동 시 사용하는 초기 mock 데이터
const MOCK_TOPICS: Topic[] = [
  { id: 1, channel_id: 'CH1', reinterpreted_title: '금리 인상이 내 지갑을 얇게 만드는 5가지 방법', score: 85, grade: 'auto', is_trending: true, topic_type: 'trending' },
  { id: 2, channel_id: 'CH1', reinterpreted_title: '부동산 하락장에서 살아남는 투자 전략', score: 72, grade: 'review', is_trending: false, topic_type: 'evergreen' },
  { id: 3, channel_id: 'CH2', reinterpreted_title: '양자컴퓨터가 현실이 된다면 우리 생활은?', score: 91, grade: 'auto', is_trending: true, topic_type: 'trending' },
  { id: 4, channel_id: 'CH2', reinterpreted_title: '블랙홀 사건지평선의 비밀', score: 68, grade: 'review', is_trending: false, topic_type: 'evergreen' },
]

const CHANNEL_OPTIONS = ['전체', 'CH1', 'CH2', 'CH3', 'CH4', 'CH5', 'CH6', 'CH7']
const GRADE_OPTIONS = [
  { value: 'all', label: '전체 상태' },
  { value: 'auto', label: '자동 승인' },
  { value: 'approved', label: '수동 승인' },
  { value: 'review', label: '검토 대기' },
  { value: 'rejected', label: '거부됨' },
]

function GradeBadge({ grade }: { grade: Grade }) {
  if (grade === 'auto')
    return <Badge className="bg-green-500 hover:bg-green-600 text-white">자동 승인</Badge>
  if (grade === 'approved')
    return <Badge className="bg-blue-500 hover:bg-blue-600 text-white">수동 승인</Badge>
  if (grade === 'rejected')
    return <Badge variant="destructive">거부됨</Badge>
  return <Badge variant="outline" className="border-yellow-500 text-yellow-600">검토 필요</Badge>
}

export default function TrendsPage() {
  const [topics, setTopics] = useState<Topic[]>(MOCK_TOPICS)
  const [channelFilter, setChannelFilter] = useState('전체')
  const [gradeFilter, setGradeFilter] = useState('all')
  const [isPending, startTransition] = useTransition()

  // Supabase에서 실제 트렌드 주제 로드
  useEffect(() => {
    const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL
    const supabaseKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY
    if (!supabaseUrl || !supabaseKey || supabaseUrl.includes('xxxxxxxxxxxx')) return

    const supabase = createClient()
    supabase
      .from('trend_topics')
      .select('id, channel_id, reinterpreted_title, score, grade, is_trending, topic_type, breakdown')
      .order('score', { ascending: false })
      .limit(100)
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      .then(({ data }: { data: any[] | null }) => {
        if (!data || data.length === 0) return
        setTopics(
          data.map((row) => ({
            id: row.id,
            channel_id: row.channel_id ?? '',
            reinterpreted_title: row.reinterpreted_title ?? '',
            score: row.score ?? 0,
            grade: (row.grade as Grade) ?? 'review',
            is_trending: row.is_trending ?? false,
            topic_type: row.topic_type ?? '',
            breakdown: row.breakdown ?? undefined,
          }))
        )
      })
  }, [])

  // Supabase mutation + 로컬 상태 낙관적 업데이트
  const updateGrade = (id: number, grade: Grade) => {
    // 낙관적 업데이트 (서버 응답 전에 UI 즉시 반영)
    setTopics((prev) => prev.map((t) => (t.id === id ? { ...t, grade } : t)))

    startTransition(async () => {
      const result = await updateTopicGrade(id, grade as 'approved' | 'rejected' | 'review')
      if (!result.ok) {
        // 실패 시 롤백
        console.error('[Trends] grade 업데이트 실패:', result.error)
        setTopics((prev) => prev.map((t) => (t.id === id ? { ...t, grade: 'review' } : t)))
      }
    })
  }

  const filtered = useMemo(() => {
    return topics.filter((t) => {
      const byChannel = channelFilter === '전체' || t.channel_id === channelFilter
      const byGrade = gradeFilter === 'all' || t.grade === gradeFilter
      return byChannel && byGrade
    })
  }, [topics, channelFilter, gradeFilter])

  const autoCount = topics.filter((t) => t.grade === 'auto').length
  const approvedCount = topics.filter((t) => t.grade === 'approved').length
  const reviewCount = topics.filter((t) => t.grade === 'review').length
  const rejectedCount = topics.filter((t) => t.grade === 'rejected').length

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold" style={{ fontFamily: "'Libre Baskerville', serif", color: '#1a0505' }}>
          트렌드 주제 관리
        </h1>
        <p className="text-sm mt-1" style={{ color: '#9b6060' }}>
          수집된 트렌드 주제 검토 및 승인/거부 · 점수 = 관심도40% + 적합도25% + 수익성20% + 긴급도15%
        </p>
      </div>

      {/* 요약 카드 */}
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <div className="glass-card p-4">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs" style={{ color: '#9b6060' }}>자동 승인</span>
            <CheckCircle className="h-4 w-4 text-green-500" />
          </div>
          <div className="text-2xl font-bold" style={{ fontFamily: "'Libre Baskerville', serif", color: '#1a0505' }}>{autoCount}</div>
          <p className="text-xs mt-1" style={{ color: '#9b6060' }}>점수 80+ 자동 통과</p>
        </div>

        <div className="glass-card p-4">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs" style={{ color: '#9b6060' }}>수동 승인</span>
            <ThumbsUp className="h-4 w-4" style={{ color: '#ee2400' }} />
          </div>
          <div className="text-2xl font-bold" style={{ fontFamily: "'Libre Baskerville', serif", color: '#ee2400' }}>{approvedCount}</div>
          <p className="text-xs mt-1" style={{ color: '#9b6060' }}>검토 후 승인됨</p>
        </div>

        <div className="glass-card p-4">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs" style={{ color: '#9b6060' }}>검토 대기</span>
            <Clock className="h-4 w-4" style={{ color: '#f59e0b' }} />
          </div>
          <div className="text-2xl font-bold" style={{ fontFamily: "'Libre Baskerville', serif", color: '#f59e0b' }}>{reviewCount}</div>
          <p className="text-xs mt-1" style={{ color: '#9b6060' }}>수동 검토 필요</p>
        </div>

        <div className="glass-card p-4">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs" style={{ color: '#9b6060' }}>거부됨</span>
            <XCircle className="h-4 w-4" style={{ color: '#ef4444' }} />
          </div>
          <div className="text-2xl font-bold" style={{ fontFamily: "'Libre Baskerville', serif", color: '#ef4444' }}>{rejectedCount}</div>
          <p className="text-xs mt-1" style={{ color: '#9b6060' }}>블랙리스트 주제</p>
        </div>
      </div>

      {/* 주제 테이블 */}
      <Card>
        <CardHeader>
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <div className="flex items-center gap-2">
              <TrendingUp className="h-4 w-4" />
              <CardTitle>수집된 주제 목록</CardTitle>
              <span className="text-xs text-muted-foreground">
                ({filtered.length} / {topics.length})
              </span>
              {isPending && (
                <span className="text-xs text-muted-foreground animate-pulse">저장 중...</span>
              )}
            </div>
            {/* 필터 */}
            <div className="flex items-center gap-2">
              <Filter className="h-4 w-4 text-muted-foreground shrink-0" />
              {/* 채널 탭 버튼 — 기존 Select 교체 */}
              <div className="flex gap-1 flex-wrap p-1 rounded-xl" style={{ background: 'var(--tab-bg)', border: '1px solid var(--tab-border)' }}>
                {CHANNEL_OPTIONS.map(ch => (
                  <button
                    key={ch}
                    onClick={() => setChannelFilter(ch)}
                    className="px-3 py-1.5 rounded-lg text-xs font-medium transition-all"
                    style={{ background: channelFilter === ch ? '#900000' : 'transparent', color: channelFilter === ch ? '#ffefea' : '#9b6060' }}
                  >
                    {ch}
                  </button>
                ))}
              </div>
              <Select value={gradeFilter} onValueChange={(v) => v && setGradeFilter(v)}>
                <SelectTrigger className="h-8 w-32 text-xs">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {GRADE_OPTIONS.map((g) => (
                    <SelectItem key={g.value} value={g.value} className="text-xs">{g.label}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          {filtered.length === 0 ? (
            <p className="text-sm text-muted-foreground text-center py-8">
              해당 조건의 주제가 없습니다.
            </p>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>채널</TableHead>
                  <TableHead>주제</TableHead>
                  <TableHead className="text-center">점수</TableHead>
                  <TableHead className="text-center">트렌딩</TableHead>
                  <TableHead className="text-center">상태</TableHead>
                  <TableHead className="text-center">액션</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filtered.map((topic) => (
                  <TableRow key={topic.id}>
                    <TableCell>
                      <Badge variant="secondary">{topic.channel_id}</Badge>
                    </TableCell>
                    <TableCell className="max-w-xs">
                      <p className="truncate text-sm">{topic.reinterpreted_title}</p>
                      <p className="text-xs text-muted-foreground mt-0.5">{topic.topic_type}</p>
                      {/* 점수 구성 배지 */}
                      <div className="flex gap-1 flex-wrap mt-1">
                        {[
                          { label: '관심도', pct: 40, key: 'interest' as const },
                          { label: '적합도', pct: 25, key: 'fit' as const },
                          { label: '수익성', pct: 20, key: 'revenue' as const },
                          { label: '긴급도', pct: 15, key: 'urgency' as const },
                        ].map(s => {
                          const val = topic.breakdown
                            ? Math.round(topic.breakdown[s.key])
                            : Math.round(topic.score * s.pct / 100)
                          return (
                            <span key={s.label} className="text-[9px] px-1.5 py-0.5 rounded" style={{ background: 'rgba(238,36,0,0.07)', color: '#9b6060' }}>
                              {s.label} {s.pct}%·{val}
                            </span>
                          )
                        })}
                      </div>
                    </TableCell>
                    <TableCell className="text-center">
                      <span className={`font-semibold ${topic.score >= 80 ? 'text-green-600' : 'text-yellow-600'}`}>
                        {topic.score}
                      </span>
                    </TableCell>
                    <TableCell className="text-center">
                      {topic.is_trending ? (
                        <TrendingUp className="h-4 w-4 text-orange-500 mx-auto" />
                      ) : (
                        <span className="text-muted-foreground text-xs">—</span>
                      )}
                    </TableCell>
                    <TableCell className="text-center">
                      <GradeBadge grade={topic.grade} />
                    </TableCell>
                    <TableCell className="text-center">
                      {topic.grade === 'review' ? (
                        <div className="flex items-center justify-center gap-1.5">
                          <Button
                            size="sm"
                            variant="outline"
                            className="h-7 px-2 text-xs bg-green-500/10 border border-green-500/30 text-green-400 hover:bg-green-500/20 hover:shadow-[0_0_12px_rgba(34,197,94,0.3)] transition-shadow"
                            onClick={() => updateGrade(topic.id, 'approved')}
                            disabled={isPending}
                          >
                            <ThumbsUp className="h-3 w-3 mr-1" />
                            승인
                          </Button>
                          <Button
                            size="sm"
                            variant="outline"
                            className="h-7 px-2 text-xs border-red-500/30 text-red-400 hover:bg-red-500/10 hover:shadow-[0_0_12px_rgba(239,68,68,0.25)] transition-shadow"
                            onClick={() => updateGrade(topic.id, 'rejected')}
                            disabled={isPending}
                          >
                            <ThumbsDown className="h-3 w-3 mr-1" />
                            거부
                          </Button>
                        </div>
                      ) : topic.grade === 'approved' || topic.grade === 'rejected' ? (
                        <Button
                          size="sm"
                          variant="ghost"
                          className="h-7 px-2 text-xs text-muted-foreground"
                          onClick={() => updateGrade(topic.id, 'review')}
                          disabled={isPending}
                        >
                          되돌리기
                        </Button>
                      ) : (
                        <span className="text-xs text-muted-foreground">—</span>
                      )}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
