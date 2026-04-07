import { createClient } from '@supabase/supabase-js'
import type { Database } from '@/lib/types'

/**
 * service_role key를 사용하는 서버 전용 Supabase 클라이언트.
 * Server Action / API Route 내부에서만 사용할 것.
 * 클라이언트 컴포넌트에서 절대 import 금지.
 */
export function createAdminClient() {
  const url = process.env.NEXT_PUBLIC_SUPABASE_URL
  const key = process.env.SUPABASE_SERVICE_ROLE_KEY

  if (!url || !key) {
    throw new Error('NEXT_PUBLIC_SUPABASE_URL 또는 SUPABASE_SERVICE_ROLE_KEY 미설정')
  }

  return createClient<Database>(url, key, {
    auth: { persistSession: false },
  })
}
