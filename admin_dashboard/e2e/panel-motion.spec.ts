import { expect, test, type Page } from '@playwright/test'

// The side panel's motion, frame by frame, without the real API. Opening a record shows a
// loading panel first, then swaps it for the form: the slide must carry on, not start again.
// The CPU is slowed down 6x, because on a slow or busy computer that swap takes longer.
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
const OFFICE = { id: 3, name_en: 'Head Office', name_kh: 'ការិយាល័យកណ្តាល', description: null, address: 'Norodom Blvd', province: PP, map_query: null, ...stamps }
const BUILDING = { id: 5, location_id: 3, name_en: 'Tower A', name_kh: 'អគារ ក', short_name: 'A', sort_order: 1, ...stamps }
const FLOOR = { id: 7, building_id: 5, floor_label: '3rd floor', sort_order: 3, ...stamps }
const ROOM_TYPE = { id: 2, name_en: 'Meeting room', name_kh: 'បន្ទប់ប្រជុំ', sort_order: 1, ...stamps }
const ITEM = { id: 4, name: 'Projector', icon: 'projector', sort_order: 1, ...stamps }
const DEPARTMENT = { id: 3, location_id: 3, name_en: 'IT Department', name_kh: 'ព័ត៌មានវិទ្យា', sort_order: 1, ...stamps }
const DIVISION = { id: 12, department_id: 3, name_en: 'Software', name_kh: 'កម្មវិធី', short_name: 'SW', sort_order: 1, ...stamps }
const POSITION = { id: 4, name_en: 'IT Lead', name_kh: 'ប្រធាន', sort_order: 1, ...stamps }
const ROLE = { id: 3, code: 'STAFF', name_en: 'Staff', name_kh: 'បុគ្គលិក', is_active: true }
const USER_ITEM = {
  id: 9,
  staff_id: 'EMP-009',
  title: 'Ms.',
  name_en: 'Chan Sophea',
  name_kh: 'ចាន់ សុភា',
  email: 'sophea@company.com',
  division: { id: 12, name_en: 'Software', name_kh: 'កម្មវិធី' },
  position: { id: 4, name_en: 'IT Lead', name_kh: 'ប្រធាន' },
  province: PP,
  role_codes: ['STAFF'],
  is_active: true,
  last_login_at: null,
}
const USER = {
  ...USER_ITEM,
  ...stamps,
  secondary_email: null,
  phone: null,
  avatar_url: null,
  signature_url: null,
  email_notifications: true,
  department: { id: 3, name_en: 'IT Department', name_kh: 'ព័ត៌មានវិទ្យា' },
  roles: [{ code: 'STAFF', name_en: 'Staff', name_kh: 'បុគ្គលិក' }],
  owned_room_ids: [],
  must_change_password: false,
}
const NAMED = { location: { id: 3, name_en: 'Head Office', name_kh: 'ការិយាល័យកណ្តាល' }, province: PP }
const SERVICE = { id: 3, name: 'Coffee break', description: null, sort_order: 1, version: 1, ...stamps }
const SESSION = { id: 1, date: '2026-11-10', start_time: '09:00', end_time: '10:30' }
const BOOKING_ITEM = {
  id: 100,
  reference_code: 'NBC-26-10000',
  room: { id: 12, name_en: 'Mekong Room', name_kh: 'បន្ទប់មេគង្គ', is_private: false, ...NAMED },
  meeting_title: 'Budget review',
  meeting_type: 'INTERNAL',
  route: 'R1',
  status: 'CONFIRMED',
  display_status: 'CONFIRMED',
  requester: { id: 4, name_en: 'Sok Dara', name_kh: 'សុខ ដារា' },
  first_session: SESSION,
  session_count: 1,
  attendees: 10,
  has_catering: false,
  has_it: false,
  created_at: '2026-11-03T02:00:00Z',
  version: 1,
}
const BOOKING = {
  ...BOOKING_ITEM,
  requester_info: { name_en: 'Sok Dara' },
  meeting_purpose: null,
  private_justification: null,
  participant_emails: [],
  sessions: [SESSION],
  last_end: { date: '2026-11-10', time: '10:30' },
  catering: null,
  it: null,
  reviews: [],
  rejection: null,
  cancelled_at: null,
  cancel_reason: null,
  updated_at: '2026-11-03T02:00:00Z',
}

const RECORDS: Record<string, unknown> = {
  '/api/v1/users/9': USER,
  '/api/v1/departments/3': DEPARTMENT,
  '/api/v1/divisions/12': DIVISION,
  '/api/v1/positions/4': POSITION,
  '/api/v1/categories/2': ROOM_TYPE,
  '/api/v1/equipment/4': ITEM,
  '/api/v1/bookings/100': BOOKING,
  '/api/v1/locations/3': OFFICE,
  '/api/v1/buildings/5': { ...BUILDING, ...NAMED },
  '/api/v1/floors/7': { ...FLOOR, building: { id: 5, name_en: 'Tower A', name_kh: 'អគារ ក' }, ...NAMED },
}
const LISTS: Record<string, unknown[]> = {
  '/api/v1/users': [USER_ITEM],
  '/api/v1/roles': [ROLE],
  '/api/v1/departments': [DEPARTMENT],
  '/api/v1/divisions': [DIVISION],
  '/api/v1/positions': [POSITION],
  '/api/v1/categories': [ROOM_TYPE],
  '/api/v1/equipment': [ITEM],
  '/api/v1/catering-packages': [SERVICE],
  '/api/v1/it-services': [SERVICE],
  '/api/v1/bookings': [BOOKING_ITEM],
  '/api/v1/locations': [OFFICE],
  '/api/v1/buildings': [BUILDING],
  '/api/v1/floors': [FLOOR],
}

async function listPage(page: Page, path: string, recordMs: number) {
  await page.addInitScript(() => sessionStorage.setItem('nbc.admin.refresh', 'R0'))
  await page.route('**/api/v1/**', async (route) => {
    const url = new URL(route.request().url())
    if (url.pathname === '/api/v1/auth/refresh') {
      return route.fulfill({ json: { access_token: 'A1', refresh_token: 'R1', token_type: 'bearer' } })
    }
    if (url.pathname === '/api/v1/me') return route.fulfill({ json: ME })
    if (url.pathname === '/api/v1/provinces') return route.fulfill({ json: { items: [PP], total: 1 } })
    if (RECORDS[url.pathname]) {
      await new Promise((ok) => setTimeout(ok, recordMs))
      return route.fulfill({ json: RECORDS[url.pathname] })
    }
    const items = LISTS[url.pathname] ?? []
    return route.fulfill({ json: { items, page: 1, size: 20, total: items.length } })
  })
  await page.setViewportSize({ width: 1366, height: 800 })
  await page.goto(path)
  await expect(page.locator('tbody tr')).toHaveCount(1)
  const cdp = await page.context().newCDPSession(page)
  await cdp.send('Emulation.setCPUThrottlingRate', { rate: 6 })
}

/** Every frame for `ms`: the left edge of each panel on screen and the scrim's opacity.
 * `t` counts from the start of the recording, `at` is the page's own clock (performance.now). */
function frames(page: Page, ms: number) {
  return page.evaluate(
    (ms) =>
      new Promise<Array<{ t: number; at: number; x: number[]; scrim: number[] }>>((done) => {
        const out: Array<{ t: number; at: number; x: number[]; scrim: number[] }> = []
        const start = performance.now()
        const tick = () => {
          out.push({
            t: performance.now() - start,
            at: performance.now(),
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

for (const path of [
  '/offices',
  '/buildings',
  '/floors',
  '/room-types',
  '/equipment',
  '/catering-packages',
  '/it-services',
  '/bookings',
  '/departments',
  '/divisions',
  '/positions',
  '/users',
  '/roles',
]) {
  for (const recordMs of [60, 800]) {
    test(`${path}: a record (answer after ${recordMs}ms) slides in once`, async ({ page }) => {
      await listPage(page, path, recordMs)

      const recording = frames(page, recordMs + 1200)
      await page.locator('tbody tr').first().click()
      const seen = (await recording).filter((f) => f.x.length)

      // One panel at a time; it only ever moves left, and the scrim only ever gets darker.
      for (let i = 1; i < seen.length; i++) {
        expect(seen[i]!.x).toHaveLength(1)
        expect(seen[i]!.x[0]!).toBeLessThanOrEqual(seen[i - 1]!.x[0]! + 1)
        expect(Math.max(...seen[i]!.scrim, 0)).toBeGreaterThanOrEqual(Math.max(...seen[i - 1]!.scrim, 0) - 0.01)
      }
      expect(Math.round(seen[seen.length - 1]!.x[0]!)).toBe(1366 - 440)
    })
  }
}

test('a record slides in as smoothly as a new one: no form built while it moves', async ({ page }) => {
  await listPage(page, '/offices', 60)
  // Frames that took long, with the scripts that ran in them (Long Animation Frames API).
  await page.evaluate(() => {
    const w = window as unknown as { longFrames: Array<{ start: number; end: number; scriptMs: number }> }
    w.longFrames = []
    new PerformanceObserver((list) => {
      for (const e of list.getEntries() as unknown as Array<PerformanceEntry & { scripts: PerformanceEntry[] }>) {
        const scriptMs = e.scripts.reduce((sum, s) => sum + s.duration, 0)
        w.longFrames.push({ start: e.startTime, end: e.startTime + e.duration, scriptMs })
      }
    }).observe({ type: 'long-animation-frame' })
  })

  const recording = frames(page, 1200)
  await page.locator('tbody tr').first().click()
  const seen = await recording
  const firstMove = seen.findIndex((f) => f.x.length && f.x[0]! < 1366 - 1)
  const moving = seen.slice(firstMove).filter((f) => f.x.length && f.x[0]! > 1366 - 440 + 1)
  const slideStart = moving[0]!.at
  const slideEnd = moving[moving.length - 1]!.at
  const longFrames = await page.evaluate(
    () => (window as unknown as { longFrames: Array<{ start: number; end: number; scriptMs: number }> }).longFrames,
  )

  // The form is built (lots of script) before the slide starts, never while the panel moves.
  // Frame length alone is not checked: under the 6x slow-down the browser itself sometimes
  // pauses for 50ms+ (no script in it), on a "New office" panel just as much.
  const before = longFrames.filter((f) => f.end <= slideStart)
  const during = longFrames.filter((f) => f.end > slideStart && f.start < slideEnd)
  expect(Math.max(0, ...before.map((f) => f.scriptMs))).toBeGreaterThan(50)
  expect(Math.max(0, ...during.map((f) => f.scriptMs))).toBeLessThan(20)
})

test('the panel slides out when it closes', async ({ page }) => {
  await listPage(page, '/offices', 60)
  await page.locator('tbody tr').first().click()
  await expect(page.getByRole('dialog')).toContainText('Head Office')
  await expect.poll(async () => Math.round((await page.getByRole('dialog').boundingBox())!.x)).toBe(1366 - 440)

  const recording = frames(page, 900)
  await page.getByRole('dialog').getByRole('button', { name: 'Close' }).click()
  const seen = await recording

  // Part way out at some frame, and gone at the end.
  expect(seen.some((f) => f.x.some((x) => x > 1366 - 440 + 20 && x < 1366 - 20))).toBe(true)
  expect(seen[seen.length - 1]!.x).toEqual([])
})
