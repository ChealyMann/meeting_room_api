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
const ROLES = [
  ['ADMIN', 'Admin', 'អ្នកគ្រប់គ្រង'],
  ['ROOM_OWNER', 'Room owner', 'ម្ចាស់បន្ទប់'],
  ['STAFF', 'Staff', 'បុគ្គលិក'],
  ['PITIKA', 'Pitika', 'ពិធីការ'],
  ['IT_LEAD', 'IT Lead', 'ប្រធានផ្នែកព័ត៌មានវិទ្យា'],
  ['IT_STAFF', 'IT Staff', 'បុគ្គលិកផ្នែកព័ត៌មានវិទ្យា'],
].map(([code, name_en, name_kh], i) => ({ id: i + 1, code, name_en, name_kh, is_active: true }))
// Long names, long emails and many roles: the worst a row can get.
const USERS = Array.from({ length: 20 }, (_, i) => ({
  id: 7 + i,
  staff_id: `EMP-${String(1000 + i)}-LONG`,
  title: i % 2 ? 'Mrs.' : null,
  name_en: `Someone with a very long English name number ${i + 1}`,
  name_kh: `អ្នកប្រើដែលមានឈ្មោះវែងណាស់ ${i + 1}`,
  email: `someone.with.a.very.long.email.address.${i + 1}@department.company.com`,
  division: i % 3 ? { id: 12, name_en: 'Division with a fairly long English name', name_kh: 'ការិយាល័យ' } : null,
  position: { id: 4, name_en: 'Position with a fairly long English name', name_kh: 'តួនាទី' },
  province: PP,
  role_codes: ROLES.slice(0, 1 + (i % 6)).map((r) => r.code),
  is_active: i % 5 !== 0,
  last_login_at: i % 4 ? '2026-10-20T03:15:00Z' : null,
}))

async function signedIn(page: Page, path: string) {
  await page.addInitScript(() => sessionStorage.setItem('nbc.admin.refresh', 'R0'))
  await page.route('**/api/v1/**', (route) => {
    const url = new URL(route.request().url())
    if (url.pathname === '/api/v1/auth/refresh') {
      return route.fulfill({ json: { access_token: 'A1', refresh_token: 'R1', token_type: 'bearer' } })
    }
    if (url.pathname === '/api/v1/me') return route.fulfill({ json: ME })
    if (url.pathname === '/api/v1/roles') return route.fulfill({ json: { items: ROLES, total: 6 } })
    if (url.pathname === '/api/v1/users') {
      // The page asks for 20 (57 in all); the role counts ask for 1.
      const size = Number(url.searchParams.get('size'))
      return route.fulfill({ json: { items: USERS.slice(0, size), page: 1, size, total: 57 } })
    }
    return route.fulfill({ json: { items: [], page: 1, size: 20, total: 0 } })
  })
  await page.goto(path)
}

for (const width of [1366, 900, 390]) {
  test(`/users at ${width}px: no sideways page scroll, paging visible`, async ({ page }) => {
    await page.setViewportSize({ width, height: 800 })
    await signedIn(page, '/users')

    await expect(page.locator('tbody tr')).toHaveCount(20)
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth)
    expect(overflow).toBe(0)
    await page.locator('nav[aria-label="Pages"]').scrollIntoViewIfNeeded()
    await expect(page.locator('nav[aria-label="Pages"]')).toBeVisible()
  })

  test(`/roles at ${width}px: no sideways page scroll`, async ({ page }) => {
    await page.setViewportSize({ width, height: 800 })
    await signedIn(page, '/roles')

    await expect(page.locator('tbody tr')).toHaveCount(6)
    await expect(page.locator('tbody tr .users').first()).toHaveText('57')
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth)
    expect(overflow).toBe(0)
  })
}
