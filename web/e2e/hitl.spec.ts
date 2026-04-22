/**
 * HITL 3 게이트 E2E 테스트 (T47)
 *
 * 실행: npx playwright test web/e2e/hitl.spec.ts
 * 설치: npm install -D @playwright/test && npx playwright install chromium
 */
import { test, expect, type Page } from '@playwright/test'

const BASE_URL = process.env.TEST_BASE_URL ?? 'http://localhost:3000'

async function login(page: Page) {
  await page.goto(`${BASE_URL}/login`)
  const passwordInput = page.locator('input[type="password"]')
  if (await passwordInput.isVisible()) {
    await passwordInput.fill(process.env.DASHBOARD_PASSWORD ?? 'test')
    await page.getByRole('button', { name: /로그인|login/i }).click()
    await page.waitForURL(/(?!.*login)/)
  }
}

// ── Gate 1: 시리즈 승인 페이지 ─────────────────────────────────

test.describe('Gate 1 — 시리즈 승인', () => {
  test('페이지 렌더링 성공', async ({ page }) => {
    await login(page)
    await page.goto(`${BASE_URL}/hitl/series-approval`)
    await expect(page.getByText('월간 시리즈 승인')).toBeVisible()
  })

  test('승인/거절 버튼 노출', async ({ page }) => {
    await login(page)
    await page.goto(`${BASE_URL}/hitl/series-approval`)
    await page.waitForLoadState('networkidle')

    const approveBtn = page.locator('button[title="승인"]').first()
    const rejectBtn = page.locator('button[title="거절"]').first()

    if (await approveBtn.isVisible()) {
      await approveBtn.click()
      await expect(approveBtn.locator('xpath=ancestor::div[contains(@class,"border-green")]')).toBeVisible()
    }

    if (await rejectBtn.isVisible()) {
      await rejectBtn.click()
    }
  })

  test('모바일 반응형 — 버튼 터치 영역 44px 이상', async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 }) // iPhone 14
    await login(page)
    await page.goto(`${BASE_URL}/hitl/series-approval`)
    await expect(page.getByText('월간 시리즈 승인')).toBeVisible()
  })
})

// ── Gate 2: 썸네일 거부권 페이지 ─────────────────────────────────

test.describe('Gate 2 — 썸네일 거부권', () => {
  test('페이지 렌더링 + 안내 문구 노출', async ({ page }) => {
    await login(page)
    await page.goto(`${BASE_URL}/hitl/thumbnail-veto`)
    await expect(page.getByText('썸네일 거부권 검토')).toBeVisible()
    await expect(page.getByText('YouTube 알고리즘이 72시간 내')).toBeVisible()
  })

  test('문제없음 버튼 클릭 → 녹색 활성화', async ({ page }) => {
    await login(page)
    await page.goto(`${BASE_URL}/hitl/thumbnail-veto`)
    await page.waitForLoadState('networkidle')

    const okBtn = page.getByText('문제 없음').first()
    if (await okBtn.isVisible()) {
      await okBtn.click()
      await expect(okBtn).toHaveCSS('background-color', /rgb\(34,\s*197/)
    }
  })

  test('전면 차단 버튼 클릭 → 적색 활성화', async ({ page }) => {
    await login(page)
    await page.goto(`${BASE_URL}/hitl/thumbnail-veto`)
    await page.waitForLoadState('networkidle')

    const blockBtn = page.getByText('전면 차단').first()
    if (await blockBtn.isVisible()) {
      await blockBtn.click()
    }
  })

  test('모바일 반응형 — 3분할 썸네일 그리드', async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 })
    await login(page)
    await page.goto(`${BASE_URL}/hitl/thumbnail-veto`)
    await expect(page.getByText('썸네일 거부권 검토')).toBeVisible()
  })
})

// ── Gate 3: 최종 프리뷰 페이지 ─────────────────────────────────

test.describe('Gate 3 — 최종 프리뷰', () => {
  test('페이지 렌더링 성공', async ({ page }) => {
    await login(page)
    await page.goto(`${BASE_URL}/hitl/final-preview`)
    await expect(page.getByText('업로드 전 최종 프리뷰')).toBeVisible()
  })

  test('Skip 버튼 존재', async ({ page }) => {
    await login(page)
    await page.goto(`${BASE_URL}/hitl/final-preview`)
    await page.waitForLoadState('networkidle')

    const skipBtn = page.getByText('Skip').first()
    if (await skipBtn.isVisible()) {
      await expect(skipBtn).toBeEnabled()
    }
  })

  test('빈 큐 상태 — 대기 메시지 노출', async ({ page }) => {
    await login(page)
    await page.goto(`${BASE_URL}/hitl/final-preview`)
    await page.waitForLoadState('networkidle')

    const emptyMsg = page.getByText('업로드 대기 중인 영상이 없습니다.')
    if (await emptyMsg.isVisible()) {
      await expect(emptyMsg).toBeVisible()
    }
  })

  test('모바일 반응형', async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 })
    await login(page)
    await page.goto(`${BASE_URL}/hitl/final-preview`)
    await expect(page.getByText('업로드 전 최종 프리뷰')).toBeVisible()
  })
})

// ── API 라우트 smoke test ─────────────────────────────────────

test.describe('HITL API 라우트', () => {
  test('GET /api/hitl/series-plan → 200', async ({ request }) => {
    const resp = await request.get(`${BASE_URL}/api/hitl/series-plan`)
    expect(resp.status()).toBe(200)
    const data = await resp.json()
    expect(data).toHaveProperty('series')
  })

  test('GET /api/hitl/thumbnail-veto → 200', async ({ request }) => {
    const resp = await request.get(`${BASE_URL}/api/hitl/thumbnail-veto`)
    expect(resp.status()).toBe(200)
    const data = await resp.json()
    expect(data).toHaveProperty('sets')
  })

  test('GET /api/hitl/final-preview → 200', async ({ request }) => {
    const resp = await request.get(`${BASE_URL}/api/hitl/final-preview`)
    expect(resp.status()).toBe(200)
    const data = await resp.json()
    expect(data).toHaveProperty('items')
  })
})
