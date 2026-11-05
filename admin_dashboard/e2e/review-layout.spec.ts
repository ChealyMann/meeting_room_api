import { expect, test, type Page } from '@playwright/test'

// The Pitika's To review page, with every /api/v1 call answered here (no real API).
const ME = {
  id: 9,
  name_en: 'Chan Sophea',
  email: 'chan.sophea@nbc.gov.kh',
  roles: [
    { code: 'PITIKA', name_en: 'Pitika', name_kh: 'បិដក' },
    { code: 'STAFF', name_en: 'Staff', name_kh: 'បុគ្គលិក' },
  ],
  must_change_password: false,
  avatar_url: null,
  updated_at: '2026-10-01T00:00:00Z',
}
const ROOM = {
  id: 12,
  name_en: 'Mekong Room with a fairly long English name',
  name_kh: 'បន្ទប់មេគង្គដែលមានឈ្មោះវែង',
  is_private: false,
  location: { id: 3, name_en: 'Head Office', name_kh: 'ការិយាល័យកណ្តាល' },
  province: { code: 'PP', name_en: 'Phnom Penh', name_kh: 'ភ្នំពេញ' },
}
const day = (offset: number) => {
  const d = new Date(Date.now() + 7 * 3600_000)
  d.setUTCDate(d.getUTCDate() + offset)
  return d.toISOString().slice(0, 10)
}
const ITEMS = [0, 1, 9].map((offset, i) => ({
  id: 100 + i,
  reference_code: `NBC-26-${10000 + i}`,
  room: ROOM,
  meeting_title: `Quarterly budget and planning review with a long title ${i + 1}`,
  meeting_type: 'INTERNAL',
  route: i === 1 ? 'R2' : 'R1',
  status: 'PENDING_PITIKA',
  display_status: 'PENDING_PITIKA',
  requester: { id: 4, name_en: 'Sokunthea Chanthavong', name_kh: 'សុគន្ធា' },
  first_session: { id: 1, date: day(offset), start_time: '23:00', end_time: '23:30' },
  session_count: 2,
  attendees: 25,
  has_catering: true,
  has_it: true,
  created_at: '2026-11-03T02:00:00Z',
  version: 1,
}))
const detail = (item: (typeof ITEMS)[number]) => ({
  ...item,
  requester_info: { name_en: 'Sokunthea Chanthavong', division: 'Payment Systems Department' },
  meeting_purpose: 'Plan the budget',
  private_justification: item.route === 'R2' ? 'Board members attend' : null,
  participant_emails: [],
  sessions: [item.first_session],
  last_end: { date: item.first_session.date, time: '23:30' },
  catering: { packages: [{ id: 1, name: 'Coffee break' }, { id: 2, name: 'Lunch box with a long name' }], servings: 25, delivery_date: item.first_session.date, delivery_time: '12:00', remarks: null, approver_notes: null, decided_by: null, decided_at: null },
  it: { ticket_id: 1, items: [{ id: 3, name: 'Projector setup' }, { id: 4, name: 'Microphones' }], special_requirements: null, status: 'RECEIVED', technician_notes: null, staff: [], setup_date: item.first_session.date, setup_time: '07:30', forwarded_at: null, assigned_at: null, ready_at: null },
  reviews: [],
  rejection: null,
  cancelled_at: null,
  cancel_reason: null,
  cancelled_by: null,
  updated_at: '2026-11-03T02:00:00Z',
})

async function signedIn(page: Page, path: string) {
  await page.addInitScript(() => sessionStorage.setItem('nbc.admin.refresh', 'R0'))
  await page.route('**/api/v1/**', (route) => {
    const url = new URL(route.request().url())
    if (url.pathname === '/api/v1/auth/refresh') {
      return route.fulfill({ json: { access_token: 'A1', refresh_token: 'R1', token_type: 'bearer' } })
    }
    if (url.pathname === '/api/v1/me') return route.fulfill({ json: ME })
    if (url.pathname === '/api/v1/pitika/bookings') return route.fulfill({ json: { items: ITEMS, page: 1, size: 100, total: ITEMS.length } })
    const one = /^\/api\/v1\/bookings\/(\d+)$/.exec(url.pathname)
    if (one) return route.fulfill({ json: detail(ITEMS.find((i) => i.id === Number(one[1]))!) })
    return route.fulfill({ json: { items: [], page: 1, size: 100, total: 0 } })
  })
  await page.goto(path)
}

const sideways = (page: Page) => page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth)

test('a Pitika lands on To review and sees only their menu', async ({ page }) => {
  await page.setViewportSize({ width: 1366, height: 800 })
  await signedIn(page, '/')

  await expect(page).toHaveURL(/\/review$/)
  const links = page.locator('nav a')
  await expect(links).toHaveText(['To review', 'Bookings', 'Food list'])
})

for (const width of [1366, 900, 390]) {
  test(`the To review queue fits at ${width}px, every button inside its row`, async ({ page }) => {
    await page.setViewportSize({ width, height: 800 })
    await signedIn(page, '/review')

    await expect(page.locator('.row')).toHaveCount(3)
    await expect(page.locator('.group-head h2')).toHaveText(['Today', 'Tomorrow', 'Later'])
    expect(await sideways(page)).toBe(0)
    for (const row of await page.locator('.row').all()) {
      const r = (await row.boundingBox())!
      for (const name of ['Reject', 'Approve']) {
        const b = (await row.getByRole('button', { name }).boundingBox())!
        expect(b.x).toBeGreaterThanOrEqual(r.x)
        expect(b.x + b.width).toBeLessThanOrEqual(r.x + r.width + 0.5)
      }
    }
  })

  test(`the review panel and the reject pop-up fit at ${width}px`, async ({ page }) => {
    await page.setViewportSize({ width, height: 800 })
    await signedIn(page, '/review?id=101')

    const panel = page.getByRole('dialog')
    await expect(panel).toContainText('Board members attend')
    expect(await panel.evaluate((el) => el.scrollWidth - el.clientWidth)).toBe(0)

    await panel.locator('.panel-foot').getByRole('button', { name: 'Reject' }).click()
    const dialog = page.getByRole('alertdialog')
    await expect(dialog).toContainText('Reject this booking?')
    const confirm = dialog.locator('button.confirm')
    await expect(confirm).toBeDisabled()
    await dialog.locator('textarea').fill('Room')
    await expect(confirm).toBeDisabled()
    await dialog.locator('textarea').fill('Room closed')
    await expect(confirm).toBeEnabled()
    const d = (await dialog.boundingBox())!
    expect(d.x).toBeGreaterThanOrEqual(0)
    expect(d.x + d.width).toBeLessThanOrEqual(width)
    expect(await sideways(page)).toBe(0)
  })
}
