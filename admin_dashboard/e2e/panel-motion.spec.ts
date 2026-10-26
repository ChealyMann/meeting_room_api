import { expect, test, type Page } from '@playwright/test'

// The side panel's motion, frame by frame, without the real API. The record answers after
// 60ms, so the loading panel is swapped for the form while it is still sliding in.
const ME = {
  id: 1,
  name_en: 'Sok Dara',
  email: 'dara@company.com',
  roles: [{ code: 'ADMIN', name_en: 'Admin', name_kh: 'អ្នកគ្រប់គ្រង' }],
  must_change_password: false,
  avatar_url: null,
  updated_at: '2026-10-01T00:00:00Z',
}
const OFFICE = {
  id: 3,
  name_en: 'Head Office',
  name_kh: 'ការិយាល័យកណ្តាល',
  description: null,
  address: 'Norodom Blvd',
  province: { code: 'PP', name_en: 'Phnom Penh', name_kh: 'ភ្នំពេញ' },
  map_query: null,
  is_active: true,
  created_at: '2026-10-01T00:00:00Z',
  updated_at: '2026-10-01T00:00:00Z',
}

async function officesPage(page: Page) {
  await page.addInitScript(() => sessionStorage.setItem('nbc.admin.refresh', 'R0'))
  await page.route('**/api/v1/**', async (route) => {
    const path = new URL(route.request().url()).pathname
    if (path === '/api/v1/auth/refresh') {
      return route.fulfill({ json: { access_token: 'A1', refresh_token: 'R1', token_type: 'bearer' } })
    }
    if (path === '/api/v1/me') return route.fulfill({ json: ME })
    if (path === '/api/v1/locations/3') {
      await new Promise((ok) => setTimeout(ok, 60))
      return route.fulfill({ json: OFFICE })
    }
    if (path === '/api/v1/locations') return route.fulfill({ json: { items: [OFFICE], page: 1, size: 20, total: 1 } })
    return route.fulfill({ json: { items: [], page: 1, size: 20, total: 0 } })
  })
  await page.setViewportSize({ width: 1366, height: 800 })
  await page.goto('/offices')
  await expect(page.locator('tbody tr')).toHaveCount(1)
}

/** Every frame for `ms`: the left edge of each panel on screen and the scrim's opacity. */
function frames(page: Page, ms: number) {
  return page.evaluate(
    (ms) =>
      new Promise<Array<{ t: number; x: number[]; scrim: number[] }>>((done) => {
        const out: Array<{ t: number; x: number[]; scrim: number[] }> = []
        const start = performance.now()
        const tick = () => {
          out.push({
            t: performance.now() - start,
            x: [...document.querySelectorAll('aside.panel')].map((el) => el.getBoundingClientRect().x),
            scrim: [...document.querySelectorAll('.scrim')].map((el) => Number(getComputedStyle(el).opacity)),
          })
          if (performance.now() - start < ms) requestAnimationFrame(tick)
          else done(out)
        }
        tick()
      }),
    ms,
  )
}

test('the panel slides in once, without jumping back or blinking', async ({ page }) => {
  await officesPage(page)

  const recording = frames(page, 700)
  await page.locator('tbody tr').first().click()
  const seen = (await recording).filter((f) => f.x.length)

  // The front panel only ever moves left, and the scrim only ever gets darker.
  for (let i = 1; i < seen.length; i++) {
    expect(Math.min(...seen[i]!.x)).toBeLessThanOrEqual(Math.min(...seen[i - 1]!.x) + 1)
    expect(Math.max(...seen[i]!.scrim, 0)).toBeGreaterThanOrEqual(Math.max(...seen[i - 1]!.scrim, 0) - 0.01)
  }
  expect(Math.round(Math.min(...seen[seen.length - 1]!.x))).toBe(1366 - 440)
})

test('the panel slides out when it closes', async ({ page }) => {
  await officesPage(page)
  await page.locator('tbody tr').first().click()
  await expect(page.getByRole('dialog')).toContainText('Head Office')
  await expect.poll(async () => Math.round((await page.getByRole('dialog').boundingBox())!.x)).toBe(1366 - 440)

  const recording = frames(page, 500)
  await page.getByRole('dialog').getByRole('button', { name: 'Close' }).click()
  const seen = await recording

  // Part way out at some frame, and gone at the end.
  expect(seen.some((f) => f.x.some((x) => x > 1366 - 440 + 20 && x < 1366 - 20))).toBe(true)
  expect(seen[seen.length - 1]!.x).toEqual([])
})
