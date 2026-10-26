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

const ROOMS = Array.from({ length: 20 }, (_, i) => ({
  id: 12 + i,
  name_en: `Room with a fairly long English name ${i + 1}`,
  name_kh: `បន្ទប់ប្រជុំវែង ${i + 1}`,
  short_desc: null,
  capacity: 10 + i,
  size_sqm: null,
  start_time: '08:00',
  end_time: '17:00',
  category: { id: 1, name_en: 'Meeting room', name_kh: 'បន្ទប់ប្រជុំ' },
  floor: { id: 7, floor_label: '3rd floor' },
  building: { id: 5, name_en: 'Building A', name_kh: 'អគារ A', short_name: null },
  location: { id: 3, name_en: 'Head Office', name_kh: 'ការិយាល័យកណ្តាល' },
  province: { code: 'PP', name_en: 'Phnom Penh', name_kh: 'ភ្នំពេញ' },
  owner: null,
  cover_photo: null,
  is_active: true,
  is_bookable: true,
  is_private: i % 3 === 0,
}))

async function signedIn(page: Page) {
  await page.addInitScript(() => sessionStorage.setItem('nbc.admin.refresh', 'R0'))
  await page.route('**/api/v1/**', (route) => {
    const path = new URL(route.request().url()).pathname
    if (path === '/api/v1/auth/refresh') {
      return route.fulfill({ json: { access_token: 'A1', refresh_token: 'R1', token_type: 'bearer' } })
    }
    if (path === '/api/v1/me') return route.fulfill({ json: ME })
    if (path === '/api/v1/rooms') return route.fulfill({ json: { items: ROOMS, page: 1, size: 20, total: 57 } })
    return route.fulfill({ json: { items: [], page: 1, size: 100, total: 0 } })
  })
  await page.goto('/')
}

for (const width of [1366, 900, 390]) {
  test(`rooms list at ${width}px: no sideways page scroll, paging visible`, async ({ page }) => {
    await page.setViewportSize({ width, height: 800 })
    await signedIn(page)

    await expect(page.locator('tbody tr')).toHaveCount(20)
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth)
    expect(overflow).toBe(0)
    await page.locator('nav[aria-label="Pages"]').scrollIntoViewIfNeeded()
    await expect(page.locator('nav[aria-label="Pages"]')).toBeVisible()
  })
}
