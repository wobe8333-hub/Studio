import Link from 'next/link'
import { Home, SearchX } from 'lucide-react'
import { Button } from '@/components/ui/button'

export default function NotFound() {
  return (
    <div className="flex flex-col items-center justify-center min-h-[60vh] gap-6 p-8 text-center">
      <div className="flex items-center justify-center w-16 h-16 rounded-full bg-primary/10">
        <SearchX className="w-8 h-8 text-primary" />
      </div>
      <div className="space-y-2">
        <h2 className="text-xl font-semibold">페이지를 찾을 수 없습니다</h2>
        <p className="text-sm text-muted-foreground">
          요청한 페이지 또는 채널이 존재하지 않습니다.
        </p>
      </div>
      <Button render={<Link href="/" />} variant="outline" size="sm">
        <Home className="w-4 h-4 mr-2" />
        대시보드로 돌아가기
      </Button>
    </div>
  )
}
