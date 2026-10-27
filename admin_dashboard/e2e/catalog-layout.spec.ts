import { expect, test, type Page } from '@playwright/test'

// Runs without the real API: every /api/v1 call gets a fake answer.
const ME = {
  id: 1,
  name_en: 'Sok Dara',
  email: 'dara@company.com',
  roles: [{ code: 'ADMIN', name_en: 'Admin', name_kh: 'អ្នកគ្រប់គ្រង' }],
  must_change_password: false,
  avatar_url: null,
  updated_at: '2026-10-01T00:00:00Z',
}
const stamps = { created_at: '2026-10-01T00:00:00Z', updated_at: '2026-10-01T00:00:00Z' }
const ROOM_TYPES = Array.from({ length: 20 }, (_, i) => ({
  id: 2 + i,
  name_en: `Room type with a fairly long English name ${i + 1}`,
  name_kh: `ប្រភេទបន្ទប់ដែលមានឈ្មោះវែង ${i + 1}`,
  sort_order: i,
  is_active: i % 5 !== 0,
  ...stamps,
}))
const ICONS = ['projector', 'mic', 'tv', 'old-icon', null]
const ITEMS = Array.from({ length: 20 }, (_, i) => ({
  id: 4 + i,
  name: `Equipment item with a long name number ${i + 1}`,
  icon: ICONS[i % ICONS.length],
  sort_order: i,
  is_active: true,
  ...stamps,
}))
const LISTS: Record<string, unknown[]> = { '/api/v1/categories': ROOM_TYPES, '/api/v1/equipment': ITEMS }

async function signedIn(page: Page, path: string) {
  await page.addInitScript(() => sessionStorage.setItem('nbc.admin.refresh', 'R0'))
  await page.route('**/api/v1/**', (route) => {
    const url = new URL(route.request().url())
    if (url.pathname === '/api/v1/auth/refresh') {
      return route.fulfill({ json: { access_token: 'A1', refresh_token: 'R1', token_type: 'bearer' } })
    }
    if (url.pathname === '/api/v1/me') return route.fulfill({ json: ME })
    if (url.pathname === '/api/v1/equipment/4') return route.fulfill({ json: ITEMS[0] })
    const items = LISTS[url.pathname]
    if (items) return route.fulfill({ json: { items, page: 1, size: 20, total: 57 } })
    return route.fulfill({ json: { items: [], page: 1, size: 20, total: 0 } })
  })
  await page.goto(path)
}

const sideways = (page: Page) => page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth)

for (const path of ['/room-types', '/equipment']) {
  for (const width of [1366, 900, 390]) {
    test(`${path} at ${width}px: no sideways page scroll, paging visible`, async ({ page }) => {
      await page.setViewportSize({ width, height: 800 })
      await signedIn(page, path)

      await expect(page.locator('tbody tr')).toHaveCount(20)
      expect(await sideways(page)).toBe(0)
      await page.locator('nav[aria-label="Pages"]').scrollIntoViewIfNeeded()
      await expect(page.locator('nav[aria-label="Pages"]')).toBeVisible()
    })
  }
}

test('the icon grid fits a phone without sideways scroll', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 800 })
  await signedIn(page, '/equipment?id=4')

  const grid = page.getByRole('radiogroup', { name: 'Icons' })
  await expect(grid).toBeVisible()
  expect(await grid.evaluate((el) => el.scrollWidth - el.clientWidth)).toBe(0)
  expect(await sideways(page)).toBe(0)
})
