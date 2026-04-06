import { Skeleton } from '@/components/ui/skeleton'

// 전역 로딩 UI — Supabase fetch 지연 시 즉시 표시
export default function Loading() {
  return (
    <div className="flex flex-col gap-6 p-4 md:p-6">
      {/* KPI 카드 스켈레톤 */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        {Array.from({ length: 4 }).map((_, i) => (
          <Skeleton key={i} className="h-28 rounded-xl" />
        ))}
      </div>

      {/* 섹션 제목 */}
      <Skeleton className="h-6 w-40 rounded-md" />

      {/* 채널 카드 스켈레톤 */}
      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-4">
        {Array.from({ length: 6 }).map((_, i) => (
          <Skeleton key={i} className="h-48 rounded-xl" />
        ))}
      </div>
    </div>
  )
}
