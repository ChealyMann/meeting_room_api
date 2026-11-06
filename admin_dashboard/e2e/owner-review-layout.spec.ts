import { expect, test, type Page } from '@playwright/test'

// The room owner's To review page, with every /api/v1 call answered here (no real API).
const ME = {
  id: 7,
  name_en: 'Keo Vanna',
  email: 'keo.vanna@nbc.gov.kh',
  roles: [
    { code: 'ROOM_OWNER', name_en: 'Room owner', name_kh: 'ម្ចាស់បន្ទប់' },
    { code: 'STAFF', name_en: 'Staff', name_kh: 'បុគ្គលិក' },
  ],
  must_change_password: false,
  avatar_url: null,
  updated_at: '2026-10-01T00:00:00Z',
}
const ROOM = {
  id: 13,
  name_en: 'Governor Room with a fairly long English name',
  name_kh: 'បន្ទប់ទេសាភិបាលដែលមានឈ្មោះវែង',
  is_private: true,
  location: { id: 3, name_en: 'Head Office', name_kh: 'ការិយាល័យកណ្តាល' },
  province: { code: 'PP', name_en: 'Phnom Penh', name_kh: 'ភ្នំពេញ' },
}
const ROOMS = [{ ...ROOM, capacity: 20, owner: { id: 7, name_en: 'Keo Vanna', name_kh: 'x' }, cover_photo: null }]
const day = (offset: number) => {
  const d = new Date(Date.now() + 7 * 3600_000)
  d.setUTCDate(d.getUTCDate() + offset)
  return d.toISOString().slice(0, 10)
}
const ITEMS = [0, 1, 9].map((offset, i) => ({
  id: 200 + i,
  reference_code: `NBC-26-${20000 + i}`,
  room: ROOM,
  meeting_title: `Board risk and planning review with a long title ${i + 1}`,
  meeting_type: 'INTERNAL_WITH_GOVERNOR',
  route: 'R2',
  status: 'PENDING_OWNER',
  display_status: 'PENDING_OWNER',
  requester: { id: 4, name_en: 'Sokunthea Chanthavong', name_kh: 'សុគន្ធា' },
  first_session: { id: 1, date: day(offset), start_time: '23:00', end_time: '23:30' },
  session_count: 1,
  attendees: 25,
  has_catering: false,
  has_it: i !== 1,
  created_at: '2026-11-03T02:00:00Z',
  version: 1,
}))
const detail = (item: (typeof ITEMS)[number]) => ({
  ...item,
  requester_info: { name_en: 'Sokunthea Chanthavong', division: 'Payment Systems Department' },
  meeting_purpose: 'Quarterly risk review',
  private_justification: 'The Governor attends and the topic is confidential',
  participant_emails: [],
  sessions: [item.first_session],
  last_end: { date: item.first_session.date, time: '23:30' },
  catering: null,
  it: item.has_it ? { ticket_id: 1, items: [{ id: 3, name: 'Video call' }], special_requirements: null, status: 'RECEIVED', technician_notes: null, staff: [], setup_date: item.first_session.date, setup_time: '07:30', forwarded_at: null, assigned_at: null, ready_at: null } : null,
  reviews: [{ stage: 'PITIKA', decision: 'APPROVED', reviewer: { id: 9, name_en: 'Chan Sophea' }, notes: 'Please check the projector before the Governor arrives', reviewed_at: '2026-11-03T03:00:00Z', by_admin: false }],
  rejection: null,
  cancelled_at: null,
  cancel_reason: null,
  cancelled_by: null,
  updated_at: '2026-11-03T02:00:00Z',
})
const DECIDED = ITEMS.map((item, i) => ({
  ...item,
  status: ['SETUP_IN_PROGRESS', 'CONFIRMED', 'CONFIRMED'][i],
  display_status: ['SETUP_IN_PROGRESS', 'CONFIRMED', 'COMPLETED'][i],
  decided_at: new Date(Date.now() - i * 20 * 3600_000).toISOString(),
  decision_note: i === 0 ? 'Fine, the room is ready for the Governor and the board members' : null,
}))

async function signedIn(page: Page, path: string) {
  await page.addInitScript(() => sessionStorage.setItem('nbc.admin.refresh', 'R0'))
  await page.route('**/api/v1/**', (route) => {
    const url = new URL(route.request().url())
    if (url.pathname === '/api/v1/auth/refresh') {
      return route.fulfill({ json: { access_token: 'A1', refresh_token: 'R1', token_type: 'bearer' } })
    }
    if (url.pathname === '/api/v1/me') return route.fulfill({ json: ME })
    if (url.pathname === '/api/v1/rooms') return route.fulfill({ json: { items: ROOMS, page: 1, size: 100, total: 1 } })
    if (url.pathname === '/api/v1/owner/bookings') return route.fulfill({ json: { items: ITEMS, page: 1, size: 100, total: ITEMS.length } })
    if (url.pathname === '/api/v1/owner/bookings/summary') return route.fulfill({ json: { waiting: 3, approved_today: 2, rejected_today: 1 } })
    if (url.pathname === '/api/v1/owner/bookings/decided') return route.fulfill({ json: { items: DECIDED, page: 1, size: 20, total: DECIDED.length } })
    const one = /^\/api\/v1\/bookings\/(\d+)$/.exec(url.pathname)
    if (one) return route.fulfill({ json: detail(ITEMS.find((i) => i.id === Number(one[1]))!) })
    return route.fulfill({ json: { items: [], page: 1, size: 100, total: 0 } })
  })
  await page.goto(path)
}

const sideways = (page: Page) => page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth)

test('a Room owner lands on To review, sees only their menu, with the waiting count', async ({ page }) => {
  await page.setViewportSize({ width: 1366, height: 800 })
  await signedIn(page, '/')

  await expect(page).toHaveURL(/\/owner-review$/)
  await expect(page.locator('nav a .label')).toHaveText(['To review', 'Bookings'])
  await expect(page.locator('nav a[href="/owner-review"] .wait')).toHaveText('3')
  await expect(page.locator('.rail .brand-text span')).toHaveText('Room owner')
})

test('on the folded rail the waiting count is a small crimson dot on the icon', async ({ page }) => {
  await page.setViewportSize({ width: 1024, height: 800 }) // a tablet: the rail shows icons only
  await signedIn(page, '/owner-review')

  const link = page.locator('nav a[href="/owner-review"]')
  const dot = link.locator('.wait')
  await expect(dot).toHaveAttribute('aria-label', '3 waiting')
  await expect(link.locator('.label')).toHaveCSS('opacity', '0')
  expect(Math.round((await page.locator('aside.rail').boundingBox())!.width)).toBe(64)
  const box = (await dot.boundingBox())!
  expect([Math.round(box.width), Math.round(box.height)]).toEqual([8, 8])
  expect(await dot.evaluate((el) => getComputedStyle(el).color)).toBe('rgba(0, 0, 0, 0)') // no number

  // On the icon's top right, inside the link (not clipped, not on the next link).
  const icon = (await link.locator('svg').boundingBox())!
  const a = (await link.boundingBox())!
  expect(box.x).toBeGreaterThan(icon.x + icon.width / 2)
  expect(box.y).toBeLessThan(icon.y + icon.height / 2)
  expect(box.x + box.width).toBeLessThanOrEqual(a.x + a.width)
  expect(box.y).toBeGreaterThanOrEqual(a.y)
  expect(await dot.evaluate((el) => getComputedStyle(el).backgroundColor)).toBe(
    await page.evaluate(() => {
      const probe = document.createElement('i')
      probe.style.color = 'var(--color-crimson)'
      document.body.append(probe)
      const color = getComputedStyle(probe).color
      probe.remove()
      return color
    }),
  )
})

for (const width of [1366, 900, 390]) {
  test(`the owner queue fits at ${width}px, with what to check and every button inside its row`, async ({ page }) => {
    await page.setViewportSize({ width, height: 800 })
    await signedIn(page, '/owner-review')

    await expect(page.locator('.soft-row')).toHaveCount(3)
    await expect(page.locator('.soft-row').first().locator('.soft-tag')).toHaveText(['Private · reason given', 'With Governor', '25 people · 20 seats', 'Pitika notes'])
    expect(await sideways(page)).toBe(0)
    const ring = page.locator('.today-ring')
    await expect(ring).toHaveText('3/6')
    expect(await ring.evaluate((el) => getComputedStyle(el).boxShadow)).toBe('none')
    expect((await page.getByRole('tablist').boundingBox())!.width).toBeGreaterThan(200)
    for (const row of await page.locator('.soft-row').all()) {
      const r = (await row.boundingBox())!
      for (const name of ['Reject', 'Approve']) {
        const b = (await row.getByRole('button', { name }).boundingBox())!
        expect(b.x).toBeGreaterThanOrEqual(r.x)
        expect(b.x + b.width).toBeLessThanOrEqual(r.x + r.width + 0.5)
      }
    }
  })

  test(`the owner panel, the reject pop-up and the Approved tab fit at ${width}px`, async ({ page }) => {
    await page.setViewportSize({ width, height: 800 })
    await signedIn(page, '/owner-review?id=200')

    const panel = page.getByRole('dialog')
    await expect(panel).toContainText('Waiting for room owner')
    await expect(panel).toContainText('The Pitika wrote: “Please check the projector before the Governor arrives”')
    expect(await panel.evaluate((el) => el.scrollWidth - el.clientWidth)).toBe(0)

    await panel.locator('.panel-foot').getByRole('button', { name: 'Reject' }).click()
    const dialog = page.getByRole('alertdialog')
    const confirm = dialog.locator('button.confirm')
    await expect(confirm).toBeDisabled()
    await dialog.locator('textarea').fill('Room closed')
    await expect(confirm).toBeEnabled()
    const d = (await dialog.boundingBox())!
    expect(d.x + d.width).toBeLessThanOrEqual(width)

    await page.goto('/owner-review?tab=approved')
    await expect(page.locator('.soft-row')).toHaveCount(3)
    expect(await sideways(page)).toBe(0)
  })
}
