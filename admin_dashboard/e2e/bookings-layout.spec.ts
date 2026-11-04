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
const ROOM = {
  id: 12,
  name_en: 'Mekong Room with a fairly long English name',
  name_kh: 'បន្ទប់មេគង្គដែលមានឈ្មោះវែង',
  is_private: false,
  location: { id: 3, name_en: 'Head Office', name_kh: 'ការិយាល័យកណ្តាល' },
  province: { code: 'PP', name_en: 'Phnom Penh', name_kh: 'ភ្នំពេញ' },
}
const PACKAGES = Array.from({ length: 20 }, (_, i) => ({
  id: 3 + i,
  name: `Catering package with a long name number ${i + 1}`,
  description: 'Coffee, tea, water and a small cake for every person in the meeting room',
  sort_order: i,
  is_active: i % 4 !== 0,
  version: 1,
  ...stamps,
}))
const BOOKINGS = Array.from({ length: 20 }, (_, i) => ({
  id: 100 + i,
  reference_code: `NBC-26-${String(10000 + i)}`,
  room: ROOM,
  meeting_title: `Quarterly budget and planning review number ${i + 1}`,
  meeting_type: 'EXTERNAL_WITH_GOVERNOR',
  route: 'R1',
  status: 'PENDING_PITIKA',
  display_status: 'PENDING_PITIKA',
  requester: { id: 4, name_en: 'Sokunthea Chanthavong', name_kh: 'សុគន្ធា' },
  first_session: { id: 1, date: '2026-11-10', start_time: '09:00', end_time: '10:30' },
  session_count: 3,
  attendees: 10,
  has_catering: true,
  has_it: true,
  created_at: '2026-11-03T02:00:00Z',
  version: 1,
}))
const DETAIL = {
  ...BOOKINGS[0],
  status: 'CONFIRMED',
  display_status: 'CONFIRMED',
  requester_info: { name_en: 'Sokunthea Chanthavong', staff_id: 'NBC0042', email: 'sokunthea.chanthavong@nbc.gov.kh' },
  meeting_purpose: 'A long purpose that explains the meeting in more than one line of text for the panel',
  private_justification: null,
  participant_emails: ['a.very.long.email.address.for.a.participant@nbc.gov.kh'],
  sessions: [{ id: 1, date: '2026-11-10', start_time: '09:00', end_time: '10:30' }],
  last_end: { date: '2026-11-10', time: '10:30' },
  catering: null,
  it: null,
  reviews: [],
  rejection: null,
  cancelled_at: null,
  cancel_reason: null,
  updated_at: '2026-11-03T02:00:00Z',
}
const ORDERS = Array.from({ length: 12 }, (_, i) => ({
  booking_id: 100 + i,
  reference_code: `NBC-26-${String(10000 + i)}`,
  booking_status: 'CONFIRMED',
  room: ROOM,
  meeting_title: `Quarterly budget and planning review number ${i + 1}`,
  delivery_date: '2026-11-04',
  delivery_time: '12:00',
  servings: 25,
  packages: [
    { id: 1, name: 'Coffee break' },
    { id: 2, name: 'Lunch box with a long name' },
  ],
  remarks: 'No pork, two vegetarian meals, and please bring extra water bottles',
  approver_notes: 'Approved for the governor visit',
}))

async function signedIn(page: Page, path: string) {
  await page.addInitScript(() => sessionStorage.setItem('nbc.admin.refresh', 'R0'))
  await page.route('**/api/v1/**', (route) => {
    const url = new URL(route.request().url())
    if (url.pathname === '/api/v1/auth/refresh') {
      return route.fulfill({ json: { access_token: 'A1', refresh_token: 'R1', token_type: 'bearer' } })
    }
    if (url.pathname === '/api/v1/me') return route.fulfill({ json: ME })
    if (url.pathname === '/api/v1/catering-packages') return route.fulfill({ json: { items: PACKAGES, page: 1, size: 20, total: 57 } })
    if (url.pathname === '/api/v1/bookings') return route.fulfill({ json: { items: BOOKINGS, page: 1, size: 20, total: 57 } })
    if (url.pathname === '/api/v1/admin/bookings/100/actions') {
      return route.fulfill({ json: { cancel: true, approve: true, reject: true, stage: 'OWNER' } })
    }
    if (url.pathname === '/api/v1/bookings/100/door-pass') {
      return route.fulfill({ json: { passcode: 'NBC-54248', expires_at: '2026-11-02T04:00:00Z', expired: true } })
    }
    if (url.pathname === '/api/v1/bookings/100') return route.fulfill({ json: DETAIL })
    if (url.pathname === '/api/v1/pitika/catering') return route.fulfill({ json: { items: ORDERS, total: ORDERS.length } })
    if (url.pathname === '/api/v1/provinces') return route.fulfill({ json: { items: [ROOM.province], total: 1 } })
    return route.fulfill({ json: { items: [], page: 1, size: 20, total: 0 } })
  })
  await page.goto(path)
}

const sideways = (page: Page) => page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth)

for (const [path, rows] of [
  ['/catering-packages', 20],
  ['/bookings', 20],
  ['/food-list?date=2026-11-04', 12],
] as const) {
  for (const width of [1366, 900, 390]) {
    test(`${path} at ${width}px: no sideways page scroll`, async ({ page }) => {
      await page.setViewportSize({ width, height: 800 })
      await signedIn(page, path)

      await expect(page.locator('tbody tr')).toHaveCount(rows)
      expect(await sideways(page)).toBe(0)
    })
  }
}

test('the booking panel fits a phone without sideways scroll', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 800 })
  await signedIn(page, '/bookings?id=100')

  const panel = page.getByRole('dialog')
  await expect(panel).toContainText('NBC0042')
  expect(await panel.evaluate((el) => el.scrollWidth - el.clientWidth)).toBe(0)
  expect(await sideways(page)).toBe(0)
})

for (const width of [1366, 390]) {
  test(`the door pass shows in full on one row at ${width}px`, async ({ page }) => {
    await page.setViewportSize({ width, height: 800 })
    await signedIn(page, '/bookings?id=100')
    const row = page.locator('.door-pass .secret')
    await expect(row).toBeVisible()
    const hiddenHeight = (await row.boundingBox())!.height

    await page.getByRole('button', { name: 'Show door pass' }).click()
    await expect(page.locator('.door-pass .secret-code')).toHaveText('NBC-54248')
    await expect(page.locator('.door-pass')).toContainText('Expired')

    expect((await row.boundingBox())!.height).toBe(hiddenHeight)
    expect(await row.evaluate((el) => el.scrollWidth - el.clientWidth)).toBe(0)
    const code = page.locator('.door-pass .secret-code')
    expect(await code.evaluate((el) => el.scrollWidth - el.clientWidth)).toBe(0)
  })
}

for (const width of [1366, 390]) {
  test(`the Admin action buttons and confirm step fit at ${width}px`, async ({ page }) => {
    await page.setViewportSize({ width, height: 800 })
    await signedIn(page, '/bookings?id=100')
    const panel = page.getByRole('dialog')
    for (const name of ['Cancel booking', 'Reject', 'Approve']) {
      await expect(panel.locator('.panel-foot').getByRole('button', { name })).toBeVisible()
    }

    await panel.locator('.panel-foot').getByRole('button', { name: 'Cancel booking' }).click()
    await expect(panel.locator('.action-step')).toBeVisible()
    await expect(panel.locator('.action-step textarea')).toBeVisible()

    expect(await panel.evaluate((el) => el.scrollWidth - el.clientWidth)).toBe(0)
    expect(await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth)).toBe(0)
  })
}
