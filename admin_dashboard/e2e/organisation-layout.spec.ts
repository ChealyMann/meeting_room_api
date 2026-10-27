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
const PP = { code: 'PP', name_en: 'Phnom Penh', name_kh: 'ភ្នំពេញ' }
const stamps = { is_active: true, created_at: '2026-10-01T00:00:00Z', updated_at: '2026-10-01T00:00:00Z' }
const OFFICES = [3, 4].map((id) => ({ id, name_en: `Office with a fairly long name ${id}`, name_kh: `ការិយាល័យ ${id}`, description: null, address: null, province: PP, map_query: null, ...stamps }))
const DEPARTMENTS = Array.from({ length: 20 }, (_, i) => ({
  id: 3 + i,
  location_id: 3 + (i % 2),
  name_en: `Department with a fairly long English name ${i + 1}`,
  name_kh: `នាយកដ្ឋានដែលមានឈ្មោះវែង ${i + 1}`,
  sort_order: i,
  ...stamps,
}))
const DIVISIONS = Array.from({ length: 20 }, (_, i) => ({
  id: 12 + i,
  department_id: 3 + (i % 6),
  name_en: `Division with a fairly long English name ${i + 1}`,
  name_kh: `ការិយាល័យដែលមានឈ្មោះវែង ${i + 1}`,
  short_name: i % 2 ? `DV${i}` : null,
  sort_order: i,
  ...stamps,
}))
const POSITIONS = Array.from({ length: 20 }, (_, i) => ({
  id: 4 + i,
  name_en: `Position with a fairly long English name ${i + 1}`,
  name_kh: `តួនាទីដែលមានឈ្មោះវែង ${i + 1}`,
  sort_order: i,
  ...stamps,
}))
const LISTS: Record<string, unknown[]> = {
  '/api/v1/locations': OFFICES,
  '/api/v1/departments': DEPARTMENTS,
  '/api/v1/divisions': DIVISIONS,
  '/api/v1/positions': POSITIONS,
}

async function signedIn(page: Page, path: string) {
  await page.addInitScript(() => sessionStorage.setItem('nbc.admin.refresh', 'R0'))
  await page.route('**/api/v1/**', (route) => {
    const url = new URL(route.request().url())
    if (url.pathname === '/api/v1/auth/refresh') {
      return route.fulfill({ json: { access_token: 'A1', refresh_token: 'R1', token_type: 'bearer' } })
    }
    if (url.pathname === '/api/v1/me') return route.fulfill({ json: ME })
    const items = LISTS[url.pathname]
    if (items) {
      // The page lists ask for 20 (57 in all); the select lists ask for 100 and get them all.
      const total = url.searchParams.get('size') === '100' ? items.length : 57
      return route.fulfill({ json: { items, page: 1, size: Number(url.searchParams.get('size')), total } })
    }
    return route.fulfill({ json: { items: [], page: 1, size: 20, total: 0 } })
  })
  await page.goto(path)
}

for (const path of ['/departments', '/divisions', '/positions']) {
  for (const width of [1366, 900, 390]) {
    test(`${path} at ${width}px: no sideways page scroll, paging visible`, async ({ page }) => {
      await page.setViewportSize({ width, height: 800 })
      await signedIn(page, path)

      await expect(page.locator('tbody tr')).toHaveCount(20)
      const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth)
      expect(overflow).toBe(0)
      await page.locator('nav[aria-label="Pages"]').scrollIntoViewIfNeeded()
      await expect(page.locator('nav[aria-label="Pages"]')).toBeVisible()
    })
  }
}
