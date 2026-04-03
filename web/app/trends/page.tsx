import { TrendingUp, CheckCircle, XCircle, Clock } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'

// mock 데이터 (Step05 knowledge store)
const mockTopics = [
  { id: 1, channel_id: 'CH1', reinterpreted_title: '금리 인상이 내 지갑을 얇게 만드는 5가지 방법', score: 85, grade: 'auto', is_trending: true, topic_type: 'trending' },
  { id: 2, channel_id: 'CH1', reinterpreted_title: '부동산 하락장에서 살아남는 투자 전략', score: 72, grade: 'review', is_trending: false, topic_type: 'evergreen' },
  { id: 3, channel_id: 'CH2', reinterpreted_title: '양자컴퓨터가 현실이 된다면 우리 생활은?', score: 91, grade: 'auto', is_trending: true, topic_type: 'trending' },
  { id: 4, channel_id: 'CH2', reinterpreted_title: '블랙홀 사건지평선의 비밀', score: 68, grade: 'review', is_trending: false, topic_type: 'evergreen' },
]

function GradeBadge({ grade }: { grade: string }) {
  if (grade === 'auto')
    return <Badge className="bg-green-500 hover:bg-green-600 text-white">자동 승인</Badge>
  if (grade === 'review')
    return <Badge variant="outline" className="border-yellow-500 text-yellow-600">검토 필요</Badge>
  return <Badge variant="destructive">거부됨</Badge>
}

export default function TrendsPage() {
  const autoCount = mockTopics.filter((t) => t.grade === 'auto').length
  const reviewCount = mockTopics.filter((t) => t.grade === 'review').length

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">트렌드 주제 관리</h1>
        <p className="text-muted-foreground text-sm">수집된 트렌드 주제 검토 및 승인/거부</p>
      </div>

      {/* 요약 */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">자동 승인</CardTitle>
            <CheckCircle className="h-4 w-4 text-green-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{autoCount}</div>
            <p className="text-xs text-muted-foreground mt-1">점수 80+ 자동 통과</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">검토 대기</CardTitle>
            <Clock className="h-4 w-4 text-yellow-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-yellow-600">{reviewCount}</div>
            <p className="text-xs text-muted-foreground mt-1">수동 검토 필요</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">거부됨</CardTitle>
            <XCircle className="h-4 w-4 text-destructive" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">0</div>
            <p className="text-xs text-muted-foreground mt-1">블랙리스트 주제</p>
          </CardContent>
        </Card>
      </div>

      {/* 주제 테이블 */}
      <Card>
        <CardHeader>
          <div className="flex items-center gap-2">
            <TrendingUp className="h-4 w-4" />
            <CardTitle>수집된 주제 목록</CardTitle>
          </div>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>채널</TableHead>
                <TableHead>주제</TableHead>
                <TableHead className="text-center">점수</TableHead>
                <TableHead className="text-center">트렌딩</TableHead>
                <TableHead className="text-center">상태</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {mockTopics.map((topic) => (
                <TableRow key={topic.id}>
                  <TableCell>
                    <Badge variant="secondary">{topic.channel_id}</Badge>
                  </TableCell>
                  <TableCell className="max-w-xs">
                    <p className="truncate text-sm">{topic.reinterpreted_title}</p>
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
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  )
}
