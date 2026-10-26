import { expect, test, type Page } from '@playwright/test'

// Runs without the real API: every /api/v1 call gets a fake answer.
const ME = {
  id: 1,
  staff_id: 'EMP-00002',
  title: null,
  name_en: 'Sok Dara',
  name_kh: 'សុខ ដារា',
  email: 'dara@company.com',
  secondary_email: null,
  phone: null,
  avatar_url: null,
  signature_url: null,
  email_notifications: true,
  division: null,
  department: null,
  position: { id: 9, name_en: 'IT Lead', name_kh: 'ប្រធានព័ត៌មានវិទ្យា' },
  province: null,
  roles: [{ code: 'ADMIN', name_en: 'Admin', name_kh: 'អ្នកគ្រប់គ្រង' }],
  owned_room_ids: [],
  is_active: true,
  must_change_password: false,
  last_login_at: null,
  created_at: '2026-10-01T00:00:00Z',
  updated_at: '2026-10-01T00:00:00Z',
}

const PP = { code: 'PP', name_en: 'Phnom Penh', name_kh: 'ភ្នំពេញ' }
const stamps = { created_at: '2026-10-01T00:00:00Z', updated_at: '2026-10-01T00:00:00Z' }
const OFFICES = Array.from({ length: 20 }, (_, i) => ({
  id: 3 + i,
  name_en: `Office with a fairly long English name ${i + 1}`,
  name_kh: `ការិយាល័យដែលមានឈ្មោះវែង ${i + 1}`,
  description: null,
  address: i % 4 ? `No. ${i + 10}, Preah Norodom Boulevard, Sangkat Wat Phnom, Khan Daun Penh` : null,
  province: PP,
  map_query: null,
  is_active: i % 5 !== 0,
  ...stamps,
}))
const BUILDINGS = Array.from({ length: 20 }, (_, i) => ({
  id: 5 + i,
  location_id: 3 + (i % 4),
  name_en: `Building with a long name ${i + 1}`,
  name_kh: `អគារដែលមានឈ្មោះវែង ${i + 1}`,
  short_name: i % 2 ? `B${i}` : null,
  sort_order: i,
  is_active: true,
  ...stamps,
}))
const FLOORS = Array.from({ length: 20 }, (_, i) => ({
  id: 7 + i,
  building_id: 5 + (i % 6),
  floor_label: `Floor number ${i + 1}`,
  sort_order: i,
  is_active: true,
  ...stamps,
}))
const LISTS: Record<string, unknown[]> = {
  '/api/v1/locations': OFFICES,
  '/api/v1/buildings': BUILDINGS,
  '/api/v1/floors': FLOORS,
}

async function signedIn(page: Page, path: string) {
  await page.addInitScript(() => sessionStorage.setItem('nbc.admin.refresh', 'R0'))
  await page.route('**/api/v1/**', (route) => {
    const url = new URL(route.request().url())
    if (url.pathname === '/api/v1/auth/refresh') {
      return route.fulfill({ json: { access_token: 'A1', refresh_token: 'R1', token_type: 'bearer' } })
    }
    if (url.pathname === '/api/v1/me') return route.fulfill({ json: ME })
    if (url.pathname === '/api/v1/provinces') return route.fulfill({ json: { items: [PP], total: 1 } })
    const items = LISTS[url.pathname]
    if (items) {
      // The page lists ask for 20 (57 in all); the select lists ask for 100 and get them all.
      const total = url.searchParams.get('size') === '100' ? items.length : 57
      return route.fulfill({ json: { items, page: 1, size: Number(url.searchParams.get('size')), total } })
    }
    return route.fulfill({ json: { items: [], page: 1, size: 100, total: 0 } })
  })
  await page.goto(path)
}

for (const path of ['/offices', '/buildings', '/floors']) {
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
