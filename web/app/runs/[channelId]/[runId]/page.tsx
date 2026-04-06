'use client'

import { useState, useEffect, useCallback } from 'react'
import { useParams } from 'next/navigation'
import Link from 'next/link'
import {
  ArrowLeft, FileText, Image as ImageIcon, Mic, Video,
  CheckCircle2, XCircle, AlertTriangle, Loader2, Clapperboard,
} from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'
import type { RunArtifacts } from '@/app/api/runs/[channelId]/[runId]/route'

const STATE_CLASS: Record<string, string> = {
  RUNNING:   'bg-blue-500/15 border-blue-500/30 text-blue-400',
  COMPLETED: 'bg-green-500/15 border-green-500/30 text-green-400',
  FAILED:    'bg-red-500/15 border-red-500/30 text-red-400',
  PENDING:   'bg-amber-500/15 border-amber-500/30 text-amber-400',
}

function ArtifactRow({
  icon: Icon,
  label,
  ok,
  detail,
}: {
  icon: React.ElementType
  label: string
  ok: boolean | null
  detail?: string
}) {
  return (
    <div className="flex items-center gap-3 py-2 border-b border-white/[0.04] last:border-0">
      <Icon className="h-4 w-4 text-muted-foreground shrink-0" />
      <span className="flex-1 text-sm">{label}</span>
      {detail && <span className="text-xs text-muted-foreground">{detail}</span>}
      {ok === null ? (
        <AlertTriangle className="h-4 w-4 text-muted-foreground" />
      ) : ok ? (
        <CheckCircle2 className="h-4 w-4 text-green-400" />
      ) : (
        <XCircle className="h-4 w-4 text-red-400" />
      )}
    </div>
  )
}

export default function RunDetailPage() {
  const { channelId, runId } = useParams<{ channelId: string; runId: string }>()
  const [data, setData] = useState<RunArtifacts | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [selectedImg, setSelectedImg] = useState<string | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const res = await fetch(`/api/runs/${channelId}/${runId}`)
      if (!res.ok) throw new Error(`${res.status}`)
      setData(await res.json())
    } catch (e) {
      setError(String(e))
    } finally {
      setLoading(false)
    }
  }, [channelId, runId])

  useEffect(() => { load() }, [load])

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
      </div>
    )
  }

  if (error || !data) {
    return (
      <div className="space-y-4">
        <Link href="/monitor">
          <Button variant="ghost" size="sm"><ArrowLeft className="h-4 w-4 mr-1" />모니터로</Button>
        </Link>
        <p className="text-sm text-red-400">Run을 찾을 수 없습니다: {error}</p>
      </div>
    )
  }

  const { manifest, step08, step11, cost_krw } = data

  return (
    <div className="relative space-y-6 ambient-bg overflow-hidden">
      {/* 헤더 */}
      <div>
        <Link href="/monitor">
          <Button variant="ghost" size="sm" className="mb-3 -ml-2">
            <ArrowLeft className="h-4 w-4 mr-1" />모니터로
          </Button>
        </Link>
        <div className="flex items-start gap-3">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span className="font-mono text-sm text-amber-400">{manifest.channel_id}</span>
              <Badge className={cn('border text-xs', STATE_CLASS[manifest.run_state] ?? 'border-white/20 text-white/60')}>
                {manifest.run_state}
              </Badge>
              {cost_krw !== null && cost_krw > 0 && (
                <span className="text-xs text-muted-foreground">₩{cost_krw.toLocaleString()}</span>
              )}
            </div>
            <h1 className="text-xl font-bold tracking-tight leading-snug">{manifest.topic_title}</h1>
            <p className="text-xs text-muted-foreground mt-1">
              {manifest.run_id} · {manifest.created_at?.slice(0, 10)}
              {manifest.topic_score > 0 && ` · 점수 ${manifest.topic_score}`}
            </p>
          </div>
        </div>
      </div>

      {/* Step08 아티팩트 */}
      <Card className="glass-card">
        <CardHeader className="pb-3">
          <CardTitle className="text-base flex items-center gap-2">
            <Clapperboard className="h-4 w-4 text-amber-400" />
            Step08 — 영상 제작
          </CardTitle>
          {step08 ? (
            <CardDescription>
              {step08.section_count}개 섹션 ·
              이미지 {step08.image_paths.length}장 ·
              {step08.manim ? ` Manim 성공 ${step08.manim.success}/${step08.manim.attempted}` : ''}
            </CardDescription>
          ) : (
            <CardDescription>Step08 아직 미실행</CardDescription>
          )}
        </CardHeader>
        <CardContent className="space-y-4">
          {step08 ? (
            <>
              {/* 아티팩트 체크리스트 */}
              <div className="rounded-lg border border-white/[0.06] bg-white/[0.02] px-4 py-1">
                <ArtifactRow icon={FileText} label="스크립트" ok={step08.has_script} detail={`${step08.section_count}섹션`} />
                <ArtifactRow icon={Mic} label="나레이션" ok={step08.has_narration} />
                <ArtifactRow icon={Video} label="최종 영상 (video.mp4)" ok={step08.has_video} />
                <ArtifactRow
                  icon={ImageIcon}
                  label="AI 이미지"
                  ok={step08.image_paths.length > 0}
                  detail={`${step08.image_paths.length}장`}
                />
                {step08.manim && (
                  <ArtifactRow
                    icon={Clapperboard}
                    label="Manim 애니메이션"
                    ok={step08.manim.fallback_rate < 0.5}
                    detail={`fallback ${Math.round(step08.manim.fallback_rate * 100)}%`}
                  />
                )}
              </div>

              {/* 제목 후보 */}
              {step08.title_candidates.length > 0 && (
                <div>
                  <p className="text-xs text-muted-foreground mb-2 uppercase tracking-wide font-semibold">제목 후보</p>
                  <div className="space-y-1">
                    {step08.title_candidates.map((t, i) => (
                      <div
                        key={i}
                        className={cn(
                          'rounded-lg px-3 py-2 text-sm border',
                          step08.selected_title === t
                            ? 'border-amber-500/30 bg-amber-500/10 text-amber-300'
                            : 'border-white/[0.06] bg-white/[0.02] text-muted-foreground',
                        )}
                      >
                        {step08.selected_title === t && <span className="text-amber-400 mr-1.5">✓</span>}
                        {t}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* 이미지 갤러리 */}
              {step08.image_paths.length > 0 && (
                <div>
                  <p className="text-xs text-muted-foreground mb-2 uppercase tracking-wide font-semibold">이미지 갤러리</p>
                  <div className="grid grid-cols-3 gap-2">
                    {step08.image_paths.map((imgPath, i) => (
                      <button
                        key={i}
                        onClick={() => setSelectedImg(imgPath)}
                        className="rounded-lg overflow-hidden border border-white/[0.06] hover:border-amber-500/30 transition-colors aspect-video bg-white/[0.02]"
                      >
                        {/* eslint-disable-next-line @next/next/no-img-element */}
                        <img
                          src={`/api/artifacts/${imgPath}`}
                          alt={`scene ${i + 1}`}
                          className="w-full h-full object-cover"
                          loading="lazy"
                        />
                      </button>
                    ))}
                  </div>
                </div>
              )}
            </>
          ) : (
            <p className="text-sm text-muted-foreground text-center py-4">아직 영상 제작이 시작되지 않았습니다.</p>
          )}
        </CardContent>
      </Card>

      {/* Step11 QA */}
      <Card className={cn('glass-card', step11 ? (step11.overall_pass ? 'glow-success' : 'glow-danger') : '')}>
        <CardHeader className="pb-3">
          <CardTitle className="text-base flex items-center gap-2">
            <CheckCircle2 className="h-4 w-4 text-blue-400" />
            Step11 — QA 검수
          </CardTitle>
        </CardHeader>
        <CardContent>
          {step11 ? (
            <div className="rounded-lg border border-white/[0.06] bg-white/[0.02] px-4 py-1">
              <ArtifactRow icon={CheckCircle2} label="애니메이션 품질" ok={step11.animation_ok} />
              <ArtifactRow icon={CheckCircle2} label="스크립트 정확도" ok={step11.script_ok} />
              <ArtifactRow icon={CheckCircle2} label="YouTube 정책" ok={step11.policy_ok} />
              <ArtifactRow
                icon={CheckCircle2}
                label="휴먼 리뷰"
                ok={!step11.human_review_required || step11.human_review_completed}
                detail={step11.human_review_required ? (step11.human_review_completed ? '완료' : '대기') : '불필요'}
              />
            </div>
          ) : (
            <p className="text-sm text-muted-foreground text-center py-4">Step11 QA 미실행</p>
          )}
        </CardContent>
      </Card>

      {/* 이미지 라이트박스 */}
      {selectedImg && (
        <div
          className="fixed inset-0 z-50 bg-black/80 flex items-center justify-center p-4"
          onClick={() => setSelectedImg(null)}
        >
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src={`/api/artifacts/${selectedImg}`}
            alt="확대 보기"
            className="max-w-full max-h-full rounded-xl object-contain"
            onClick={(e) => e.stopPropagation()}
          />
        </div>
      )}
    </div>
  )
}
