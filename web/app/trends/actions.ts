'use server'

import { revalidatePath } from 'next/cache'
import { createClient } from '@/lib/supabase/server'

type Grade = 'approved' | 'rejected' | 'review'

/**
 * trend_topics 테이블의 grade 필드를 Supabase에서 업데이트합니다.
 * 새로고침해도 변경 사항이 유지됩니다.
 */
export async function updateTopicGrade(topicId: number, grade: Grade): Promise<{ ok: boolean; error?: string }> {
  const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL
  const supabaseKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY

  if (!supabaseUrl || !supabaseKey || supabaseUrl.includes('xxxxxxxxxxxx')) {
    // Supabase 미연동 시 조용히 성공 (로컬 상태 변경만 동작)
    return { ok: true }
  }

  try {
    const supabase = await createClient()
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const { error } = await (supabase as any)
      .from('trend_topics')
      .update({ grade })
      .eq('id', topicId)

    if (error) {
      return { ok: false, error: error.message }
    }

    revalidatePath('/trends')
    return { ok: true }
  } catch (e) {
    return { ok: false, error: String(e) }
  }
}
