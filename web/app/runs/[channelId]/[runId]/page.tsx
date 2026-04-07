'use client'

import { useState, useEffect } from 'react'
import { useParams } from 'next/navigation'
import Link from 'next/link'
import {
  ArrowLeft, FileText, Image as ImageIcon, Mic, Video,
  CheckCircle2, XCircle, AlertTriangle, Loader2, Clapperboard,
  Music2, Type, Search, DollarSign, BarChart2,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import type { RunArtifacts } from '@/app/api/runs/[channelId]/[runId]/route'

// ─── 공통 스타일 ──────────────────────────────────────────────────────────────

const G = {
  card: {
    background: 'rgba(255,255,255,0.55)',
    backdropFilter: 'blur(20px)',
    WebkitBackdropFilter: 'blur(20px)',
    border: '1px solid rgba(238,36,0,0.12)',
    borderRadius: '1rem',
    boxShadow: '0 8px 32px rgba(144,0,0,0.08)',
  } as React.CSSProperties,
}

// ─── 탭 정의 ─────────────────────────────────────────────────────────────────

const TABS = [
  { id: 'script',    label: '스크립트', icon: FileText },
  { id: 'images',    label: '이미지',   icon: ImageIcon },
  { id: 'video',     label: '영상',     icon: Video },
  { id: 'shorts',    label: 'Shorts',   icon: Clapperboard },
  { id: 'audio',     label: '음성',     icon: Mic },
  { id: 'thumbnail', label: '썸네일',   icon: ImageIcon },
  { id: 'title',     label: '제목',     icon: Type },
  { id: 'seo',       label: 'SEO',      icon: Search },
  { id: 'qa',        label: 'QA',       icon: CheckCircle2 },
  { id: 'cost',      label: '비용',     icon: DollarSign },
] as const

type TabId = typeof TABS[number]['id']

// ─── 스크립트 탭 ──────────────────────────────────────────────────────────────

function ScriptTab({ artifacts }: { artifacts: RunArtifacts | null }) {
  const step08 = artifacts?.step08
  if (!step08?.has_script) return <EmptyState icon={FileText} msg="스크립트 파일을 찾을 수 없습니다" sub="Step06/07 실행 후 생성됩니다" />

  return (
    <div style={G.card} className="p-6">
      <h3 className="font-bold text-lg mb-4" style={{ fontFamily: "'Libre Baskerville', serif", color: '#1a0505' }}>
        {step08.selected_title ?? artifacts?.manifest?.topic_title ?? '제목 없음'}
      </h3>
      <div className="mb-4 p-4 rounded-xl" style={{ background: 'rgba(238,36,0,0.06)', border: '1px solid rgba(238,36,0,0.12)' }}>
        <p className="text-xs font-bold mb-2" style={{ color: '#ee2400' }}>🎣 도입부 후킹</p>
        <p className="text-sm leading-relaxed" style={{ color: '#5c1a1a' }}>
          스크립트 파일이 생성되었습니다. 원본 파일에서 후킹 내용을 확인하세요.
        </p>
      </div>
      <div className="p-4 rounded-xl" style={{ background: 'rgba(0,0,0,0.03)', border: '1px solid rgba(238,36,0,0.06)' }}>
        <p className="text-xs mb-2" style={{ color: '#9b6060' }}>장면 수</p>
        <p className="text-2xl font-bold" style={{ fontFamily: "'Libre Baskerville', serif", color: '#1a0505' }}>{step08.section_count}</p>
      </div>
    </div>
  )
}

// ─── 이미지 탭 ───────────────────────────────────────────────────────────────

function ImagesTab({ artifacts, channelId, runId }: { artifacts: RunArtifacts | null; channelId: string; runId: string }) {
  const images = artifacts?.step08?.image_paths ?? []

  if (!images.length) return <EmptyState icon={ImageIcon} msg="생성된 이미지가 없습니다" sub="Step08 실행 후 생성됩니다" />

  return (
    <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
      {images.map((img: string, i: number) => (
        <div key={i} className="aspect-video rounded-xl overflow-hidden" style={G.card}>
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src={`/api/artifacts/${channelId}/${runId}/step08/${img}`}
            alt={`장면 ${i + 1}`}
            className="w-full h-full object-cover"
          />
        </div>
      ))}
    </div>
  )
}

// ─── 영상 탭 ─────────────────────────────────────────────────────────────────

function VideoTab({ artifacts, channelId, runId }: { artifacts: RunArtifacts | null; channelId: string; runId: string }) {
  const hasVideo = artifacts?.step08?.has_video

  if (!hasVideo) return <EmptyState icon={Video} msg="최종 영상이 없습니다" sub="Step08 FFmpeg 합성 완료 후 생성됩니다" />

  return (
    <div style={G.card} className="p-5">
      <h3 className="font-bold mb-3" style={{ fontFamily: "'Libre Baskerville', serif", color: '#1a0505' }}>최종 영상</h3>
      <video
        controls
        className="w-full rounded-xl"
        style={{ maxHeight: '480px', background: '#000' }}
        src={`/api/artifacts/${channelId}/${runId}/step08/final.mp4`}
      >
        브라우저가 video 태그를 지원하지 않습니다.
      </video>
    </div>
  )
}

// ─── Shorts 탭 ───────────────────────────────────────────────────────────────

function ShortsTab({ channelId, runId }: { channelId: string; runId: string }) {
  const [shorts, setShorts] = useState<{ index: number; filename: string; url: string }[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetch(`/api/runs/${channelId}/${runId}/shorts`)
      .then(r => r.ok ? r.json() : { shorts: [] })
      .then(d => setShorts(d.shorts ?? []))
      .finally(() => setLoading(false))
  }, [channelId, runId])

  if (loading) return <div className="flex justify-center py-12"><Loader2 className="h-6 w-6 animate-spin" style={{ color: '#ee2400' }} /></div>
  if (!shorts.length) return <EmptyState icon={Clapperboard} msg="Shorts 파일이 없습니다" sub="Step08-S (Shorts 자동 추출) 완료 후 생성됩니다" />

  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
      {shorts.map(s => (
        <div key={s.index} style={G.card} className="p-4">
          <p className="text-xs font-bold mb-3" style={{ color: '#9b6060' }}>Shorts {s.index}</p>
          <video
            controls
            className="w-full rounded-lg"
            style={{ background: '#000', aspectRatio: '9/16', objectFit: 'cover' }}
            src={`/api/artifacts/${channelId}/${runId}/step08_s/${s.filename}`}
          />
          <p className="text-xs mt-2 truncate" style={{ fontFamily: "'DM Mono', monospace", color: '#9b6060' }}>{s.filename}</p>
        </div>
      ))}
    </div>
  )
}

// ─── 음성(BGM) 탭 ────────────────────────────────────────────────────────────

function AudioTab({ artifacts, channelId, runId }: { artifacts: RunArtifacts | null; channelId: string; runId: string }) {
  const [bgm, setBgm] = useState<{ tone?: string; file?: string } | null>(null)

  useEffect(() => {
    fetch(`/api/runs/${channelId}/${runId}/bgm`)
      .then(r => r.ok ? r.json() : null)
      .then(d => setBgm(d?.bgm ?? null))
  }, [channelId, runId])

  const narrationFile = artifacts?.step08?.has_narration ? 'narration.mp3' : null

  return (
    <div className="space-y-4">
      {/* 나레이션 */}
      <div style={G.card} className="p-5">
        <div className="flex items-center gap-3 mb-4">
          <Mic className="h-5 w-5" style={{ color: '#ee2400' }} />
          <h3 className="font-bold" style={{ fontFamily: "'Libre Baskerville', serif", color: '#1a0505' }}>나레이션</h3>
        </div>
        {narrationFile ? (
          <audio controls className="w-full" src={`/api/artifacts/${channelId}/${runId}/step08/${narrationFile}`} />
        ) : (
          <p className="text-sm" style={{ color: '#9b6060' }}>나레이션 파일이 없습니다 (Step08 완료 후 생성)</p>
        )}
      </div>

      {/* BGM */}
      <div style={G.card} className="p-5">
        <div className="flex items-center gap-3 mb-4">
          <Music2 className="h-5 w-5" style={{ color: '#ee2400' }} />
          <h3 className="font-bold" style={{ fontFamily: "'Libre Baskerville', serif", color: '#1a0505' }}>BGM</h3>
          {bgm?.tone && (
            <span className="text-xs px-2 py-0.5 rounded-full ml-auto" style={{ background: 'rgba(238,36,0,0.1)', color: '#ee2400' }}>
              {bgm.tone}
            </span>
          )}
        </div>
        {bgm?.file ? (
          <audio controls className="w-full" src={`/api/artifacts/${channelId}/${runId}/step09/${bgm.file}`} />
        ) : (
          <p className="text-sm" style={{ color: '#9b6060' }}>BGM 파일이 없습니다 (Step09 완료 후 생성)</p>
        )}
      </div>
    </div>
  )
}

// ─── 썸네일 탭 ──────────────────────────────────────────────────────────────

function ThumbnailTab({ channelId, runId }: { channelId: string; runId: string }) {
  const variants = ['thumbnail_v1', 'thumbnail_v2', 'thumbnail_v3']
  return (
    <div className="space-y-4">
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {variants.map((v, i) => (
          <div key={v} style={G.card} className="p-4">
            <p className="text-xs font-bold mb-3" style={{ color: '#9b6060' }}>썸네일 {String.fromCharCode(65 + i)}</p>
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src={`/api/artifacts/${channelId}/${runId}/step10/${v}.jpg`}
              alt={`썸네일 ${String.fromCharCode(65 + i)}`}
              className="w-full rounded-lg"
              style={{ border: '1px solid rgba(238,36,0,0.12)', aspectRatio: '16/9', objectFit: 'cover' }}
              onError={e => {
                const el = e.target as HTMLImageElement
                if (el.src.endsWith('.jpg')) {
                  el.src = `/api/artifacts/${channelId}/${runId}/step10/${v}.png`
                } else {
                  el.style.display = 'none'
                }
              }}
            />
          </div>
        ))}
      </div>
      <p className="text-xs text-center" style={{ color: '#9b6060' }}>
        3종 썸네일 A/B/C 비교 · Step10 완료 후 생성됩니다
      </p>
    </div>
  )
}

// ─── 제목 A/B/C 탭 ──────────────────────────────────────────────────────────

function TitleTab({ artifacts, channelId, runId }: { artifacts: RunArtifacts | null; channelId: string; runId: string }) {
  const titles = artifacts?.step08?.title_candidates ?? []
  const [selected, setSelected] = useState<number | null>(null)
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)

  if (!titles.length) return <EmptyState icon={Type} msg="제목 후보가 없습니다" sub="Step10 완료 후 생성됩니다" />

  const typeLabels = ['호기심 자극형', '권위 신뢰형', '이익 제공형']

  async function handleSelect(i: number) {
    setSelected(i)
    setSaving(true)
    setSaved(false)
    await fetch(`/api/runs/${channelId}/${runId}/seo`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ selected_title_index: i, selected_title: (titles as string[])[i] }),
    })
    setSaving(false)
    setSaved(true)
    setTimeout(() => setSaved(false), 2000)
  }

  return (
    <div className="space-y-3">
      {saved && (
        <div className="px-4 py-2 rounded-xl text-sm font-medium" style={{ background: 'rgba(34,197,94,0.1)', color: '#22c55e' }}>
          ✓ 제목이 저장되었습니다
        </div>
      )}
      {(titles as string[]).map((title: string, i: number) => (
        <div
          key={i}
          style={{
            ...G.card,
            border: selected === i ? '2px solid #ee2400' : '1px solid rgba(238,36,0,0.12)',
          }}
          className="p-5"
        >
          <div className="flex items-center gap-2 mb-2">
            <span className="text-xs font-bold px-2.5 py-1 rounded-full" style={{ background: 'rgba(238,36,0,0.1)', color: '#ee2400' }}>
              {String.fromCharCode(65 + i)} — {typeLabels[i] ?? `타입 ${i + 1}`}
            </span>
            {selected === i && (
              <span className="text-[10px] font-bold px-2 py-0.5 rounded-full ml-auto" style={{ background: 'rgba(34,197,94,0.15)', color: '#22c55e' }}>
                선택됨
              </span>
            )}
          </div>
          <p className="text-base font-medium leading-snug mb-3" style={{ color: '#1a0505' }}>{title}</p>
          <button
            onClick={() => handleSelect(i)}
            disabled={saving}
            className="text-xs px-3 py-1.5 rounded-lg transition-all"
            style={{
              background: selected === i ? 'rgba(34,197,94,0.1)' : 'rgba(238,36,0,0.08)',
              color: selected === i ? '#22c55e' : '#5c1a1a',
              border: `1px solid ${selected === i ? 'rgba(34,197,94,0.3)' : 'rgba(238,36,0,0.15)'}`,
            }}
          >
            {saving && selected === i ? '저장 중...' : '이 제목 선택'}
          </button>
        </div>
      ))}
    </div>
  )
}

// ─── SEO 편집 탭 ────────────────────────────────────────────────────────────

function SeoTab({ channelId, runId }: { channelId: string; runId: string }) {
  const [seo, setSeo] = useState<{ description?: string; tags?: string[] } | null>(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [desc, setDesc] = useState('')
  const [tags, setTags] = useState('')

  useEffect(() => {
    fetch(`/api/runs/${channelId}/${runId}/seo`)
      .then(r => r.ok ? r.json() : null)
      .then(d => {
        if (d?.seo) {
          setSeo(d.seo)
          setDesc(d.seo.description ?? '')
          setTags((d.seo.tags ?? []).join(', '))
        }
      })
      .finally(() => setLoading(false))
  }, [channelId, runId])

  async function handleSave() {
    setSaving(true)
    await fetch(`/api/runs/${channelId}/${runId}/seo`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ description: desc, tags: tags.split(',').map(t => t.trim()).filter(Boolean) }),
    })
    setSaving(false)
  }

  if (loading) return <div className="flex justify-center py-12"><Loader2 className="h-6 w-6 animate-spin" style={{ color: '#ee2400' }} /></div>
  if (!seo) return <EmptyState icon={Search} msg="SEO 메타데이터가 없습니다" sub="Step10 완료 후 생성됩니다" />

  return (
    <div style={G.card} className="p-6">
      <h3 className="font-bold mb-4" style={{ fontFamily: "'Libre Baskerville', serif", color: '#1a0505' }}>SEO 메타데이터 편집</h3>
      <div className="space-y-4">
        <div>
          <label className="text-xs font-semibold mb-1.5 block" style={{ color: '#5c1a1a' }}>설명 (Description)</label>
          <textarea
            value={desc}
            onChange={e => setDesc(e.target.value)}
            rows={5}
            className="w-full rounded-xl px-4 py-3 text-sm resize-none outline-none"
            style={{ background: 'rgba(238,36,0,0.04)', border: '1px solid rgba(238,36,0,0.12)', color: '#1a0505' }}
          />
        </div>
        <div>
          <label className="text-xs font-semibold mb-1.5 block" style={{ color: '#5c1a1a' }}>태그 (쉼표로 구분)</label>
          <input
            type="text"
            value={tags}
            onChange={e => setTags(e.target.value)}
            className="w-full rounded-xl px-4 py-2.5 text-sm outline-none"
            style={{ background: 'rgba(238,36,0,0.04)', border: '1px solid rgba(238,36,0,0.12)', color: '#1a0505' }}
          />
          <p className="text-xs mt-1" style={{ color: '#9b6060' }}>현재 {tags.split(',').filter(Boolean).length}개 태그</p>
        </div>
        <button
          onClick={handleSave}
          disabled={saving}
          className="flex items-center gap-2 px-5 py-2.5 rounded-xl text-sm font-semibold transition-all disabled:opacity-60"
          style={{ background: '#900000', color: '#ffefea', boxShadow: '0 4px 16px rgba(144,0,0,0.25)' }}
        >
          {saving ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : null}
          {saving ? '저장 중...' : '저장하기'}
        </button>
      </div>
    </div>
  )
}

// ─── QA 탭 ──────────────────────────────────────────────────────────────────

function QaTab({ artifacts }: { artifacts: RunArtifacts | null }) {
  const qa = artifacts?.step11

  if (!qa) return <EmptyState icon={CheckCircle2} msg="QA 결과가 없습니다" sub="Step11 완료 후 생성됩니다" />

  const passed = qa.overall_pass ?? false

  const checks = [
    { label: '애니메이션 OK', passed: qa.animation_ok },
    { label: '스크립트 OK', passed: qa.script_ok },
    { label: '정책 준수', passed: qa.policy_ok },
    { label: '수동 검토 필요', passed: !qa.human_review_required, invert: true },
    { label: '수동 검토 완료', passed: qa.human_review_completed },
  ]

  return (
    <div className="space-y-4">
      <div style={G.card} className="p-6">
        <div className="flex items-center gap-4 mb-5">
          <div className="h-16 w-16 rounded-full flex items-center justify-center" style={{ background: passed ? 'rgba(34,197,94,0.1)' : 'rgba(238,36,0,0.1)', border: `2px solid ${passed ? '#22c55e' : '#ee2400'}` }}>
            {passed
              ? <CheckCircle2 className="h-8 w-8 text-green-500" />
              : <XCircle className="h-8 w-8" style={{ color: '#ee2400' }} />
            }
          </div>
          <div>
            <p className="text-2xl font-bold" style={{ fontFamily: "'Libre Baskerville', serif", color: '#1a0505' }}>
              {passed ? '통과' : '실패'}
            </p>
            <p className="text-sm" style={{ color: passed ? '#22c55e' : '#ee2400' }}>
              {passed ? 'QA 통과' : 'QA 실패'}
            </p>
          </div>
        </div>

        <div className="space-y-2">
          {checks.map(({ label, passed: p }) => (
            <div key={label} className="flex items-center gap-3 py-2.5 border-b last:border-0" style={{ borderColor: 'rgba(238,36,0,0.08)' }}>
              {p
                ? <CheckCircle2 className="h-4 w-4 text-green-500 shrink-0" />
                : <XCircle className="h-4 w-4 shrink-0" style={{ color: '#ee2400' }} />
              }
              <p className="text-sm" style={{ color: '#1a0505' }}>{label}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

// ─── 비용 탭 ────────────────────────────────────────────────────────────────

function CostTab({ artifacts }: { artifacts: RunArtifacts | null }) {
  const costKrw = artifacts?.cost_krw

  if (costKrw == null) return <EmptyState icon={DollarSign} msg="비용 내역이 없습니다" sub="파이프라인 실행 완료 후 생성됩니다" />

  return (
    <div style={G.card} className="p-6">
      <h3 className="font-bold mb-4" style={{ fontFamily: "'Libre Baskerville', serif", color: '#1a0505' }}>이번 Run 비용</h3>
      <div className="flex items-center gap-4 p-5 rounded-xl" style={{ background: 'rgba(238,36,0,0.05)', border: '1px solid rgba(238,36,0,0.1)' }}>
        <DollarSign className="h-8 w-8" style={{ color: '#ee2400' }} />
        <div>
          <p className="text-3xl font-bold" style={{ fontFamily: "'Libre Baskerville', serif", color: '#1a0505' }}>
            ₩{costKrw.toLocaleString()}
          </p>
          <p className="text-xs mt-1" style={{ color: '#9b6060' }}>API 비용 합산 (Gemini + YouTube)</p>
        </div>
      </div>
    </div>
  )
}

// ─── 빈 상태 ─────────────────────────────────────────────────────────────────

function EmptyState({ icon: Icon, msg, sub }: { icon: React.ElementType; msg: string; sub?: string }) {
  return (
    <div style={G.card} className="p-12 text-center">
      <Icon className="h-12 w-12 mx-auto mb-4" style={{ color: 'rgba(238,36,0,0.25)' }} />
      <p className="text-base font-bold" style={{ fontFamily: "'Libre Baskerville', serif", color: '#1a0505' }}>{msg}</p>
      {sub && <p className="text-sm mt-1" style={{ color: '#9b6060' }}>{sub}</p>}
    </div>
  )
}

// ─── 메인 페이지 ─────────────────────────────────────────────────────────────

export default function RunDetailPage() {
  const params = useParams<{ channelId: string; runId: string }>()
  const { channelId, runId } = params

  const [artifacts, setArtifacts] = useState<RunArtifacts | null>(null)
  const [loading, setLoading] = useState(true)
  const [tab, setTab] = useState<TabId>('script')

  useEffect(() => {
    fetch(`/api/runs/${channelId}/${runId}`)
      .then(r => r.ok ? r.json() : null)
      .then(d => setArtifacts(d))
      .finally(() => setLoading(false))
  }, [channelId, runId])

  return (
    <div className="space-y-5">
      {/* 헤더 */}
      <div>
        <Link
          href={`/runs/${channelId}`}
          className="inline-flex items-center gap-1.5 text-sm mb-3"
          style={{ color: '#9b6060' }}
        >
          <ArrowLeft className="h-3.5 w-3.5" />
          {channelId} Run 목록
        </Link>
        <div className="flex items-center justify-between gap-4">
          <div>
            <h1 className="text-xl font-bold" style={{ fontFamily: "'Libre Baskerville', serif", color: '#1a0505' }}>
              {runId}
            </h1>
            <p className="text-sm mt-0.5" style={{ color: '#9b6060' }}>{channelId} · 결과물 검수 허브</p>
          </div>
          {artifacts?.manifest?.run_state && (
            <span
              className="text-xs font-bold px-3 py-1 rounded-full"
              style={{
                background: artifacts.manifest.run_state === 'COMPLETED' ? 'rgba(34,197,94,0.12)' : artifacts.manifest.run_state === 'FAILED' ? 'rgba(238,36,0,0.12)' : 'rgba(238,36,0,0.08)',
                color: artifacts.manifest.run_state === 'COMPLETED' ? '#22c55e' : artifacts.manifest.run_state === 'FAILED' ? '#ee2400' : '#9b6060',
              }}
            >
              {artifacts.manifest.run_state}
            </span>
          )}
        </div>
      </div>

      {loading ? (
        <div className="flex justify-center py-12"><Loader2 className="h-6 w-6 animate-spin" style={{ color: '#ee2400' }} /></div>
      ) : (
        <>
          {/* 탭 바 */}
          <div className="flex gap-1 overflow-x-auto p-1 rounded-xl" style={{ background: 'rgba(255,255,255,0.4)', border: '1px solid rgba(238,36,0,0.1)' }}>
            {TABS.map(t => (
              <button
                key={t.id}
                onClick={() => setTab(t.id)}
                className="flex items-center gap-1.5 px-3 py-2 rounded-lg text-xs font-medium transition-all whitespace-nowrap"
                style={{
                  background: tab === t.id ? '#900000' : 'transparent',
                  color: tab === t.id ? '#ffefea' : '#9b6060',
                }}
              >
                <t.icon className="h-3 w-3" />
                {t.label}
              </button>
            ))}
          </div>

          {/* 탭 컨텐츠 */}
          <div>
            {tab === 'script'    && <ScriptTab artifacts={artifacts} />}
            {tab === 'images'    && <ImagesTab artifacts={artifacts} channelId={channelId} runId={runId} />}
            {tab === 'video'     && <VideoTab artifacts={artifacts} channelId={channelId} runId={runId} />}
            {tab === 'shorts'    && <ShortsTab channelId={channelId} runId={runId} />}
            {tab === 'audio'     && <AudioTab artifacts={artifacts} channelId={channelId} runId={runId} />}
            {tab === 'thumbnail' && <ThumbnailTab channelId={channelId} runId={runId} />}
            {tab === 'title'     && <TitleTab artifacts={artifacts} channelId={channelId} runId={runId} />}
            {tab === 'seo'       && <SeoTab channelId={channelId} runId={runId} />}
            {tab === 'qa'        && <QaTab artifacts={artifacts} />}
            {tab === 'cost'      && <CostTab artifacts={artifacts} />}
          </div>
        </>
      )}
    </div>
  )
}
