'use client'

import { useEffect, useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'
import { Loader2 } from 'lucide-react'

interface SustainabilityItem {
  channel_id?: string
  topic_capacity?: number
  depletion_risk?: 'HIGH' | 'MEDIUM' | 'LOW'
  remaining_unique_topics?: number
  estimated_months_left?: number
}

function riskColor(risk: string) {
  if (risk === 'HIGH') return { bg: 'rgba(238,36,0,0.1)', text: '#ee2400' }
  if (risk === 'MEDIUM') return { bg: 'rgba(245,158,11,0.1)', text: '#f59e0b' }
  return { bg: 'rgba(34,197,94,0.1)', text: '#22c55e' }
}

export function SustainabilitySection() {
  const [items, setItems] = useState<SustainabilityItem[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetch('/api/sustainability')
      .then(r => r.ok ? r.json() : { sustainability: [] })
      .then(d => setItems(d.sustainability ?? []))
      .finally(() => setLoading(false))
  }, [])

  if (loading) return (
    <Card>
      <CardContent className="py-8 text-center">
        <Loader2 className="h-5 w-5 animate-spin mx-auto" style={{ color: '#ee2400' }} />
      </CardContent>
    </Card>
  )

  return (
    <div className="space-y-4">
      <div>
        <h2 className="text-lg font-bold" style={{ fontFamily: "'Libre Baskerville', serif", color: '#1a0505' }}>주제 지속성 분석</h2>
        <p className="text-xs mt-0.5" style={{ color: '#9b6060' }}>채널별 주제 소진 위험도 — Step17 지속성 보고서 기반</p>
      </div>
      {items.length === 0 ? (
        <Card>
          <CardContent className="py-10 text-center">
            <p className="text-sm text-muted-foreground">지속성 데이터 없음 (파이프라인 Step17 완료 후 생성)</p>
          </CardContent>
        </Card>
      ) : (
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {items.map((item, i) => {
            const c = riskColor(item.depletion_risk ?? 'LOW')
            const capacity = item.topic_capacity ?? 0
            return (
              <Card key={item.channel_id ?? i}>
                <CardHeader className="pb-2">
                  <div className="flex items-center justify-between">
                    <CardTitle className="text-sm">{item.channel_id ?? `채널 ${i + 1}`}</CardTitle>
                    <Badge style={{ background: c.bg, color: c.text, border: 'none' }}>
                      {item.depletion_risk ?? 'N/A'}
                    </Badge>
                  </div>
                </CardHeader>
                <CardContent className="space-y-3">
                  <div>
                    <div className="flex justify-between text-xs mb-1">
                      <span className="text-muted-foreground">주제 용량</span>
                      <span className="font-medium">{(capacity * 100).toFixed(0)}%</span>
                    </div>
                    <Progress value={capacity * 100} className="h-1.5" />
                  </div>
                  {item.remaining_unique_topics != null && (
                    <div className="flex justify-between text-xs">
                      <span className="text-muted-foreground">잔여 고유 주제</span>
                      <span className="font-medium">{item.remaining_unique_topics}개</span>
                    </div>
                  )}
                  {item.estimated_months_left != null && (
                    <div className="flex justify-between text-xs">
                      <span className="text-muted-foreground">예상 지속 기간</span>
                      <span className="font-medium">{item.estimated_months_left}개월</span>
                    </div>
                  )}
                </CardContent>
              </Card>
            )
          })}
        </div>
      )}
    </div>
  )
}
