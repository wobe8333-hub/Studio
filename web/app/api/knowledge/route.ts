import { NextRequest, NextResponse } from 'next/server'
import fs from 'fs/promises'
import path from 'path'
import { getKasRoot } from '@/lib/fs-helpers'

export interface KnowledgeTopic {
  original_topic: string
  reinterpreted_title: string
  category: string
  score: number
  grade: string
  is_trending: boolean
  trend_collected_at: string
  topic_type: string
}

export interface SeriesEntry {
  series_name: string
  episode_count: number
  episodes: { episode: number; title: string }[]
}

export interface ChannelKnowledge {
  channel_id: string
  topics: KnowledgeTopic[]
  series: SeriesEntry[]
}

/** assets.jsonl을 파싱해 KnowledgeTopic[] 반환 */
async function readTopics(channelId: string, kasRoot: string): Promise<KnowledgeTopic[]> {
  const jsonlPath = path.join(kasRoot, 'data', 'knowledge_store', channelId, 'discovery', 'raw', 'assets.jsonl')
  try {
    const text = await fs.readFile(jsonlPath, 'utf-8')
    const topics: KnowledgeTopic[] = []
    for (const line of text.split('\n')) {
      if (!line.trim()) continue
      try {
        const m = JSON.parse(line) as Record<string, unknown>
        const ot = (m.original_trend ?? {}) as Record<string, unknown>
        topics.push({
          original_topic:      String(ot.topic ?? m.reinterpreted_title ?? ''),
          reinterpreted_title: String(m.reinterpreted_title ?? ''),
          category:            String(m.category ?? ''),
          score:               Number(m.score ?? 0),
          grade:               String(m.grade ?? ''),
          is_trending:         Boolean(m.is_trending),
          trend_collected_at:  String(m.trend_collected_at ?? ''),
          topic_type:          String(m.topic_type ?? 'trending'),
        })
      } catch { /* 잘못된 줄 무시 */ }
    }
    return topics
  } catch {
    return []
  }
}

/** series/*.json 목록 반환 */
async function readSeries(channelId: string, kasRoot: string): Promise<SeriesEntry[]> {
  const seriesDir = path.join(kasRoot, 'data', 'knowledge_store', channelId, 'series')
  const result: SeriesEntry[] = []
  try {
    const files = await fs.readdir(seriesDir)
    for (const file of files) {
      if (!file.endsWith('.json')) continue
      try {
        const raw = JSON.parse(
          await fs.readFile(path.join(seriesDir, file), 'utf-8')
        ) as Record<string, unknown>
        const eps = Array.isArray(raw.episodes) ? (raw.episodes as Record<string, unknown>[]) : []
        result.push({
          series_name:   String(raw.base_topic ?? file.replace('.json', '')),
          episode_count: Number(raw.episode_count ?? eps.length),
          episodes:      eps.map((e) => ({
            episode: Number(e.episode ?? 0),
            title:   String(e.title ?? ''),
          })),
        })
      } catch { /* 파일 읽기 실패 무시 */ }
    }
  } catch { /* series/ 없음 */ }
  return result
}

/**
 * GET /api/knowledge?channel=CH1
 * channel 파라미터 없으면 전체 채널 반환.
 */
export async function GET(req: NextRequest) {
  const kasRoot = getKasRoot()
  const channelParam = req.nextUrl.searchParams.get('channel')

  const knowledgeRoot = path.join(kasRoot, 'data', 'knowledge_store')
  let channelIds: string[]

  if (channelParam) {
    // CH1~CH99 패턴만 허용 (경로 탈출 + 임의 문자열 방지)
    if (!/^CH\d+$/.test(channelParam)) {
      return NextResponse.json({ error: 'Invalid channel' }, { status: 400 })
    }
    channelIds = [channelParam]
  } else {
    try {
      const entries = await fs.readdir(knowledgeRoot)
      channelIds = entries.filter((e) => /^CH\d+$/.test(e))
    } catch {
      channelIds = []
    }
  }

  const channels: ChannelKnowledge[] = await Promise.all(
    channelIds.map(async (ch) => ({
      channel_id: ch,
      topics:     await readTopics(ch, kasRoot),
      series:     await readSeries(ch, kasRoot),
    }))
  )

  return NextResponse.json({ channels })
}
