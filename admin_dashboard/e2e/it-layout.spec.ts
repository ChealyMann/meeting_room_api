import { expect, test, type Page } from '@playwright/test'

// The IT pages, with every /api/v1 call answered here (no real API).
const meWith = (roles: string[]) => ({
  id: 40,
  name_en: 'Lim Dara',
  email: 'lim.dara@nbc.gov.kh',
  roles: roles.map((code) => ({ code, name_en: code, name_kh: code })),
  must_change_password: false,
  avatar_url: null,
  updated_at: '2026-10-01T00:00:00Z',
})
const ROOM = {
  id: 12,
  name_en: 'Mekong Room with a fairly long English name',
  name_kh: 'បន្ទប់មេគង្គដែលមានឈ្មោះវែង',
  is_private: false,
  location: { id: 3, name_en: 'Head Office', name_kh: 'ការិយាល័យកណ្តាល' },
  province: { code: 'PP', name_en: 'Phnom Penh', name_kh: 'ភ្នំពេញ' },
}
const ROOMS = [{ ...ROOM, capacity: 40, building: { id: 2, name_en: 'Building A', name_kh: 'x' }, floor: { id: 4, floor_label: 'Floor 2' }, cover_photo: null }]
const STAFF = [
  { id: 31, name_en: 'Chan Bopha', name_kh: 'ចាន់ បុប្ផា', is_active: true, avatar_url: null },
  { id: 32, name_en: 'Sok Pisey', name_kh: 'សុខ ពិសី', is_active: true, avatar_url: null },
]
const day = (offset: number) => {
  const d = new Date(Date.now() + 7 * 3600_000)
  d.setUTCDate(d.getUTCDate() + offset)
  return d.toISOString().slice(0, 10)
}
const ticket = (id: number, offset: number, changes: Record<string, unknown> = {}) => ({
  id,
  status: 'RECEIVED',
  items: [
    { id: 1, name: 'Projector setup' },
    { id: 2, name: 'Wireless microphones' },
    { id: 3, name: 'Video call' },
  ],
  special_requirements: 'Two wireless microphones and a video call with the Siem Reap branch office',
  technician_notes: null,
  staff: [],
  setup_date: day(offset),
  setup_time: '23:00',
  forwarded_at: '2026-11-04T02:00:00Z',
  assigned_at: null,
  ready_at: null,
  missed: false,
  review_notes: [],
  booking: {
    id: 300 + id,
    reference_code: `NBC-26-3000${id}`,
    room: ROOM,
    meeting_title: `Training on the new reporting system with a long title ${id}`,
    meeting_type: 'EXTERNAL',
    route: 'R1',
    status: 'SETUP_IN_PROGRESS',
    display_status: 'SETUP_IN_PROGRESS',
    requester: { id: 4, name_en: 'Sokunthea Chanthavong', name_kh: 'សុគន្ធា' },
    first_session: { id: 1, date: day(offset), start_time: '23:30', end_time: '23:59' },
    session_count: 1,
    attendees: 45,
    has_catering: false,
    has_it: true,
    created_at: '2026-11-03T02:00:00Z',
    version: 1,
  },
  ...changes,
})
const TO_ASSIGN = [ticket(1, 0), ticket(2, 1), ticket(3, 9)]
const IN_PROGRESS = [ticket(4, 0, { status: 'ASSIGNED', staff: STAFF }), ticket(5, 2, { status: 'ASSIGNED', staff: [STAFF[1]] })]
const DONE = [
  ticket(6, 0, { status: 'READY', staff: [STAFF[0]], ready_at: new Date().toISOString() }),
  ticket(7, -1, { status: 'ASSIGNED', staff: [STAFF[0]], missed: true }),
]
const detail = (t: ReturnType<typeof ticket>) => ({
  ...t.booking,
  requester_info: { name_en: 'Sokunthea Chanthavong', division: 'Payment Systems Department' },
  meeting_purpose: 'Training',
  private_justification: null,
  participant_emails: [],
  sessions: [t.booking.first_session],
  last_end: { date: t.booking.first_session.date, time: '23:59' },
  catering: null,
  it: { ticket_id: t.id, items: t.items, special_requirements: t.special_requirements, status: t.status, technician_notes: null, staff: t.staff, setup_date: t.setup_date, setup_time: t.setup_time, forwarded_at: t.forwarded_at, assigned_at: null, ready_at: null },
  reviews: [],
  rejection: null,
  cancelled_at: null,
  cancel_reason: null,
  cancelled_by: null,
  updated_at: '2026-11-03T02:00:00Z',
})

async function signedIn(page: Page, path: string, roles = ['IT_LEAD']) {
  await page.addInitScript(() => sessionStorage.setItem('nbc.admin.refresh', 'R0'))
  await page.route('**/api/v1/**', (route) => {
    const url = new URL(route.request().url())
    if (url.pathname === '/api/v1/auth/refresh') {
      return route.fulfill({ json: { access_token: 'A1', refresh_token: 'R1', token_type: 'bearer' } })
    }
    if (url.pathname === '/api/v1/me') return route.fulfill({ json: meWith(roles) })
    if (url.pathname === '/api/v1/rooms') return route.fulfill({ json: { items: ROOMS, page: 1, size: 100, total: 1 } })
    if (url.pathname === '/api/v1/it/staff') {
      const asked = url.searchParams.get('ticket_id')
      const busy = [[], [{ ticket_id: 5, room_name_en: 'Mekong Room with a fairly long English name', setup_time: '23:00', meeting_start: '23:30' }]]
      const items = STAFF.map((x, i) => ({ ...x, setups_that_day: asked ? [0, 3][i] : null, busy: asked ? busy[i] : null }))
      return route.fulfill({ json: { items, total: items.length } })
    }
    if (url.pathname === '/api/v1/it/tickets/summary') {
      return route.fulfill({ json: { to_assign: 3, in_progress: 2, ready_today: 1, due_today: 3, due_today_ready: 1 } })
    }
    if (url.pathname === '/api/v1/it/tickets') {
      const state = url.searchParams.get('state')
      const items = state === 'in_progress' ? IN_PROGRESS : state === 'done' ? DONE : TO_ASSIGN
      return route.fulfill({ json: { items, page: 1, size: 100, total: items.length } })
    }
    const one = /^\/api\/v1\/bookings\/(\d+)$/.exec(url.pathname)
    if (one) return route.fulfill({ json: detail([...TO_ASSIGN, ...IN_PROGRESS, ...DONE].find((t) => t.booking.id === Number(one[1]))!) })
    return route.fulfill({ json: { items: [], page: 1, size: 100, total: 0 } })
  })
  await page.goto(path)
}

const sideways = (page: Page) => page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth)

test('an IT Lead lands on IT setup with the count in the menu', async ({ page }) => {
  await page.setViewportSize({ width: 1366, height: 800 })
  await signedIn(page, '/')

  await expect(page).toHaveURL(/\/it-setup$/)
  await expect(page.locator('nav a .label')).toHaveText(['IT setup'])
  await expect(page.locator('nav a[href="/it-setup"] .wait')).toHaveText('3')
  await expect(page.locator('.rail .brand-text span')).toHaveText('IT Lead')
})

for (const width of [1366, 900, 390]) {
  test(`the IT setup tabs fit at ${width}px, every button inside its row`, async ({ page }) => {
    await page.setViewportSize({ width, height: 800 })
    for (const [tab, count] of [['', 3], ['?tab=in_progress', 2], ['?tab=ready', 2]] as const) {
      await page.unrouteAll()
      await signedIn(page, `/it-setup${tab}`)
      await expect(page.locator('.soft-row')).toHaveCount(count)
      expect(await sideways(page)).toBe(0)
      const ring = page.locator('.today-ring')
      await expect(ring).toHaveText('1/3')
      expect(await ring.evaluate((el) => getComputedStyle(el).boxShadow)).toBe('none')
      expect((await page.getByRole('tablist').boundingBox())!.width).toBeGreaterThan(200)
      for (const row of await page.locator('.soft-row').all()) {
        const r = (await row.boundingBox())!
        for (const b of await row.locator('button').all()) {
          const box = (await b.boundingBox())!
          expect(box.x).toBeGreaterThanOrEqual(r.x)
          expect(box.x + box.width).toBeLessThanOrEqual(r.x + r.width + 0.5)
        }
      }
    }
    await expect(page.locator('[data-ticket="7"] .state-word')).toHaveText('Missed · not marked ready')
  })

  test(`the assign pop-up and the panel fit at ${width}px`, async ({ page }) => {
    await page.setViewportSize({ width, height: 800 })
    await signedIn(page, '/it-setup?tab=in_progress')

    await page.locator('[data-ticket="4"]').getByRole('button', { name: 'Change staff' }).first().click()
    const dialog = page.getByRole('alertdialog')
    await expect(dialog).toContainText('Assign IT Staff')
    await expect(dialog.locator('input[type="checkbox"]')).toHaveCount(2)
    await expect(dialog.locator('.load')).toHaveText(['Free that day', '2 other setups that day'])
    await expect(dialog.locator('.busy')).toHaveText(['Busy 23:00–23:30 · Mekong Room with a fairly long English name'])
    await expect(dialog.locator('.picked')).toHaveText('2 picked')
    await expect(dialog.locator('button.confirm')).toHaveText('Assign 2 staff')
    const d = (await dialog.boundingBox())!
    expect(d.x).toBeGreaterThanOrEqual(0)
    expect(d.x + d.width).toBeLessThanOrEqual(width)
    for (const part of await dialog.locator('.staff-row, .busy, .room-box, .foot button').all()) {
      const box = (await part.boundingBox())!
      expect(box.x).toBeGreaterThanOrEqual(d.x)
      expect(box.x + box.width).toBeLessThanOrEqual(d.x + d.width + 0.5)
    }
    await page.keyboard.press('Escape')

    await page.locator('[data-ticket="4"]').click()
    const panel = page.getByRole('dialog')
    await expect(panel).toContainText('Two wireless microphones')
    await expect(panel.locator('.panel-foot').getByRole('button')).toHaveText(['Close', 'Change staff', 'Mark ready'])
    expect(await panel.evaluate((el) => el.scrollWidth - el.clientWidth)).toBe(0)
  })
}

test('only the list scrolls, never the page, when the setups do not fit', async ({ page }) => {
  // A short window (the shell's 640px minimum is still met): the list overflows. Hidden text in a
  // row (the note, read out) must stay in its row, or the page itself grows and scrolls away the
  // top bar.
  await page.setViewportSize({ width: 1366, height: 660 })
  await signedIn(page, '/it-setup')
  await expect(page.locator('.soft-row')).toHaveCount(3)
  expect(await page.locator('.queue').evaluate((el) => el.scrollHeight > el.clientHeight)).toBe(true)
  expect(await page.evaluate(() => document.documentElement.scrollHeight - window.innerHeight)).toBe(0)
})

test('IT Staff land on My tasks with no buttons on the rows', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 800 })
  await signedIn(page, '/', ['IT_STAFF'])

  await expect(page).toHaveURL(/\/my-tasks$/)
  await expect(page.locator('.soft-row')).toHaveCount(2)
  await expect(page.locator('.soft-row button')).toHaveCount(0)
  expect(await sideways(page)).toBe(0)
})
