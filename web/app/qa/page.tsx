'use client'

import { useState, useEffect, useTransition, useCallback } from 'react'
import {
  ClipboardCheck, CheckCircle2, XCircle, ChevronRight,
  Type, Image as ImageIcon, Loader2,
} from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'
import { approveHumanReview, selectTitleVariant, selectThumbnailVariant } from './actions'
import type { QaPendingRun, VariantManifest } from '@/lib/fs-helpers'

const MODE_LABEL: Record<string, string> = {
  authority: '권위형',
  curiosity: '호기심형',
  benefit: '이득형',
}

function QaCheckRow({ label, pass }: { label: string; pass: boolean }) {
  return (
    <div className="flex items-center gap-2 text-sm">
      {pass
        ? <CheckCircle2 className="h-4 w-4 text-green-400 shrink-0" />
        : <XCircle className="h-4 w-4 text-red-400 shrink-0" />}
      <span className={pass ? 'text-muted-foreground' : 'text-red-300'}>{label}</span>
    </div>
  )
}

function QaCard({ item, onApprove }: { item: QaPendingRun; onApprove: () => void }) {
  const [isPending, startTransition] = useTransition()
  const qa = item.qaResult

  function handleApprove() {
    startTransition(async () => {
      await approveHumanReview(item.channelId, item.runId)
      onApprove()
    })
  }

  return (
    <Card className="glass-card">
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between gap-2">
          <div>
            <CardTitle className="text-base flex items-center gap-2">
              <span className="font-mono text-amber-400">{item.channelId}</span>
              <ChevronRight className="h-4 w-4 text-muted-foreground" />
              <span className="text-sm font-normal text-muted-foreground truncate max-w-[240px]">
                {item.runId}
              </span>
            </CardTitle>
            <CardDescription className="mt-1 text-xs">
              QA 타임스탬프: {qa.qa_timestamp?.slice(0, 16).replace('T', ' ')}
            </CardDescription>
          </div>
          <Badge variant="outline" className="border-amber-500/40 text-amber-400 shrink-0">
            검수 대기
          </Badge>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="space-y-1.5 p-3 rounded-lg bg-white/[0.03] border border-white/[0.06]">
          <QaCheckRow label="애니메이션 품질" pass={qa.animation_quality_check.pass} />
          <QaCheckRow label="스크립트 정확성" pass={qa.script_accuracy_check.pass} />
          <QaCheckRow label="YouTube 정책" pass={qa.youtube_policy_check.pass} />
          <QaCheckRow label="수익 공식" pass={qa.affiliate_formula_check.formula_correct} />
        </div>
        <div className="flex items-center justify-between">
          <span className="text-xs text-muted-foreground">
            자동 QA: {qa.overall_pass ? '통과' : '미통과'} · SLA {qa.human_review.sla_hours}시간
          </span>
          <Button
            size="sm"
            onClick={handleApprove}
            disabled={isPending}
            className="bg-green-500/10 border border-green-500/30 text-green-400 hover:bg-green-500/20 hover:shadow-[0_0_12px_rgba(34,197,94,0.3)] transition-shadow"
          >
            {isPending ? (
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
            ) : (
              <CheckCircle2 className="h-3.5 w-3.5 mr-1.5" />
            )}
            수동 검수 승인
          </Button>
        </div>
      </CardContent>
    </Card>
  )
}

function VariantCard({ channelId, runId, manifest, onUpdate }: {
  channelId: string
  runId: string
  manifest: VariantManifest
  onUpdate: () => void
}) {
  const [isPending, startTransition] = useTransition()

  function handleSelectTitle(ref: string) {
    startTransition(async () => {
      await selectTitleVariant(channelId, runId, ref)
      onUpdate()
    })
  }

  function handleSelectThumbnail(ref: string) {
    startTransition(async () => {
      await selectThumbnailVariant(channelId, runId, ref)
      onUpdate()
    })
  }

  return (
    <Card className="glass-card">
      <CardHeader className="pb-3">
        <CardTitle className="text-base flex items-center gap-2">
          <span className="font-mono text-blue-400">{channelId}</span>
          <ChevronRight className="h-4 w-4 text-muted-foreground" />
          <span className="text-sm font-normal text-muted-foreground truncate max-w-[240px]">
            {runId}
          </span>
        </CardTitle>
        <CardDescription>Step10 배리언트 선택</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div>
          <p className="text-xs text-muted-foreground flex items-center gap-1.5 mb-2">
            <Type className="h-3.5 w-3.5" /> 제목 배리언트
          </p>
          <div className="space-y-2">
            {manifest.title_variants.map((v) => {
              const isSelected = manifest.selected_title_ref === v.ref
              return (
                <div
                  key={v.ref}
                  className={cn(
                    'flex items-start justify-between gap-3 p-2.5 rounded-lg border transition-colors cursor-pointer',
                    isSelected
                      ? 'border-amber-500/50 bg-amber-500/10 glow-amber'
                      : 'border-white/[0.06] bg-white/[0.02] hover:bg-white/[0.04]',
                  )}
                  onClick={() => !isPending && handleSelectTitle(v.ref)}
                >
                  <div className="flex-1 min-w-0">
                    <p className="text-sm leading-snug">{v.title}</p>
                    <p className="text-xs text-muted-foreground mt-0.5">
                      {MODE_LABEL[v.mode] ?? v.mode}
                      {v.seo_keyword_included && ' · SEO ✓'}
                    </p>
                  </div>
                  {isSelected && (
                    <CheckCircle2 className="h-4 w-4 text-amber-400 shrink-0 mt-0.5" />
                  )}
                </div>
              )
            })}
          </div>
        </div>

        {manifest.thumbnail_variants.length > 0 && (
          <div>
            <p className="text-xs text-muted-foreground flex items-center gap-1.5 mb-2">
              <ImageIcon className="h-3.5 w-3.5" /> 썸네일 배리언트
            </p>
            <div className="flex gap-2">
              {manifest.thumbnail_variants.map((v) => {
                const isSelected = manifest.selected_thumbnail_ref === v.ref
                const proxyUrl = `/api/artifacts/${v.path.replace(/\\/g, '/')}`
                return (
                  <button
                    key={v.ref}
                    onClick={() => !isPending && handleSelectThumbnail(v.ref)}
                    className={cn(
                      'relative flex-1 aspect-video rounded-lg border overflow-hidden transition-all',
                      isSelected
                        ? 'border-amber-500/60 shadow-[0_0_12px_rgba(245,158,11,0.4)]'
                        : 'border-white/[0.08] hover:border-white/20',
                    )}
                  >
                    {/* eslint-disable-next-line @next/next/no-img-element */}
                    <img
                      src={proxyUrl}
                      alt={`썸네일 ${v.ref}`}
                      className="w-full h-full object-cover"
                      onError={(e) => {
                        (e.target as HTMLImageElement).style.display = 'none'
                      }}
                    />
                    <div className="absolute bottom-0 inset-x-0 bg-black/60 px-2 py-1 text-xs text-center">
                      {v.ref}
                    </div>
                    {isSelected && (
                      <div className="absolute top-1 right-1">
                        <CheckCircle2 className="h-4 w-4 text-amber-400" />
                      </div>
                    )}
                  </button>
                )
              })}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  )
}

export default function QaPage() {
  const [pendingQa, setPendingQa] = useState<QaPendingRun[]>([])
  const [variants, setVariants] = useState<Array<{
    channelId: string; runId: string; manifest: VariantManifest
  }>>([])
  const [loading, setLoading] = useState(true)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const [qaRes, varRes] = await Promise.all([
        fetch('/api/qa-data?type=pending'),
        fetch('/api/qa-data?type=variants'),
      ])
      const qaData = await qaRes.json()
      const varData = await varRes.json()
      setPendingQa(qaData)
      setVariants(varData)
    } catch { /* 네트워크 에러 무시 */ } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { load() }, [load])

  return (
    <div className="relative space-y-6 ambient-bg overflow-hidden">
      <div>
        <div className="flex items-center gap-2">
          <ClipboardCheck className="h-5 w-5" style={{ color: '#ee2400' }} />
          <h1 className="text-2xl font-bold" style={{ fontFamily: "'Libre Baskerville', serif", color: '#1a0505' }}>QA 검수</h1>
        </div>
        <p className="text-sm mt-1" style={{ color: '#9b6060' }}>수동 검수 승인 및 Step10 배리언트 선택</p>
      </div>

      {loading ? (
        <div className="flex items-center justify-center py-16 text-muted-foreground">
          <Loader2 className="h-5 w-5 animate-spin mr-2" />
          <span>로딩 중...</span>
        </div>
      ) : (
        <>
          <section className="space-y-3">
            <h2 className="text-sm font-semibold text-muted-foreground uppercase tracking-wide">
              수동 검수 대기 ({pendingQa.length})
            </h2>
            {pendingQa.length === 0 ? (
              <Card className="glass-card">
                <CardContent className="py-10 text-center text-muted-foreground text-sm">
                  <CheckCircle2 className="h-8 w-8 mx-auto mb-2 text-green-400" />
                  검수 대기 항목 없음
                </CardContent>
              </Card>
            ) : (
              pendingQa.map((item) => (
                <QaCard key={`${item.channelId}-${item.runId}`} item={item} onApprove={load} />
              ))
            )}
          </section>

          {variants.length > 0 && (
            <section className="space-y-3">
              <h2 className="text-sm font-semibold text-muted-foreground uppercase tracking-wide">
                배리언트 선택 ({variants.length})
              </h2>
              {variants.map((v) => (
                <VariantCard
                  key={`${v.channelId}-${v.runId}`}
                  channelId={v.channelId}
                  runId={v.runId}
                  manifest={v.manifest}
                  onUpdate={load}
                />
              ))}
            </section>
          )}
        </>
      )}
    </div>
  )
}
