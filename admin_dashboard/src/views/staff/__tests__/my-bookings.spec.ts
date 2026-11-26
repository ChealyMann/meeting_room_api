import { enableAutoUnmount, flushPromises, mount, type VueWrapper } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createMemoryHistory, createRouter, type Router } from 'vue-router'

import { useConfirm } from '../../../composables/useConfirm'
import { useSessionStore } from '../../../stores/session'
import { bookingDetail, bookingItem } from '../../../test-utils/staff'
import MyBookingsView from '../MyBookingsView.vue'

enableAutoUnmount(afterEach)

const SOON = bookingItem(7, 'Budget review', 'CONFIRMED', '2026-11-13')
const WAITING = bookingItem(8, 'Team sync', 'PENDING_PITIKA', '2026-11-16')
const GONE = bookingItem(9, 'Old plan', 'CANCELLED', '2026-11-03')
const DONE = bookingItem(10, 'Kick-off', 'COMPLETED', '2026-11-02')

let router: Router
let calls: string[]
let bodies: Record<string, unknown>
let cancelAnswer: () => [unknown, number]
let mine: unknown[]
let detail8: unknown
let mineFails = false
let mineLimited = false
let rooms: unknown[] = []
let slipFails = false

function stub() {
  calls = []
  bodies = {}
  const json = (body: unknown, status = 200) => new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } })
  return async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = new URL(String(input))
    const key = `${init?.method ?? 'GET'} ${url.pathname}`
    calls.push(key)
    if (typeof init?.body === 'string') bodies[key] = JSON.parse(init.body)
    if (key === 'POST /api/v1/bookings/8/attachments')
      return json({ id: 9, file_name: 'notes.pdf', content_type: 'application/pdf', size_bytes: 6, created_at: '2026-11-12T03:00:00Z', url: '/api/v1/bookings/8/attachments/9' }, 201)
    if (key === 'DELETE /api/v1/bookings/8/attachments/1') return new Response(null, { status: 204 })
    if (key === 'GET /api/v1/bookings/mine' && mineLimited)
      return new Response(JSON.stringify({ error: { code: 'RATE_LIMITED', message: 'Too many requests.' } }), {
        status: 429,
        headers: { 'Content-Type': 'application/json', 'Retry-After': '20' },
      })
    if (key === 'GET /api/v1/bookings/mine')
      return mineFails ? json({ error: { code: 'X', message: 'Down.' } }, 503) : json({ items: mine, page: 1, size: 100, total: mine.length })
    if (key === 'GET /api/v1/rooms') return json({ items: rooms, page: 1, size: 100, total: rooms.length })
    if (key === 'GET /api/v1/bookings/7') return json(bookingDetail(SOON))
    if (key === 'GET /api/v1/bookings/8') return json(detail8)
    if (key === 'GET /api/v1/bookings/7/request-slip')
      return slipFails
        ? json({ error: { code: 'NOT_FOUND', message: 'This booking is not confirmed yet.' } }, 404)
        : new Response('docx', { headers: { 'Content-Type': 'application/octet-stream' } })
    if (key === 'GET /api/v1/bookings/7/door-pass') return json({ passcode: '482913', expires_at: '2026-11-13T03:00:00Z', expired: false })
    if (key === 'POST /api/v1/bookings/7/cancel') {
      const [body, status] = cancelAnswer()
      return json(body, status)
    }
    return json({}, 404)
  }
}

beforeEach(() => {
  vi.useFakeTimers({ toFake: ['Date'] })
  vi.setSystemTime(new Date('2026-11-12T03:00:00Z'))
  setActivePinia(createPinia())
  useSessionStore().accessToken = 'A1'
  mine = [SOON, WAITING, GONE, DONE]
  mineFails = false
  mineLimited = false
  rooms = []
  slipFails = false
  detail8 = bookingDetail(WAITING)
  cancelAnswer = () => [bookingDetail({ ...SOON, status: 'CANCELLED', display_status: 'CANCELLED', version: 4 }), 200]
  vi.stubGlobal('fetch', stub())
  router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/my-bookings', name: 'my-bookings', component: MyBookingsView },
      { path: '/find-room', name: 'find-room', component: { template: '<div />' } },
    ],
  })
})
afterEach(() => {
  vi.useRealTimers()
  vi.unstubAllGlobals()
  document.body.innerHTML = ''
})

async function open(query = '') {
  await router.push(`/my-bookings${query}`)
  const w = mount(MyBookingsView, { global: { plugins: [router] }, attachTo: document.body })
  await flushPromises()
  return w
}
// Layout 2 "Folders on the left" (owner pick, 20 Nov 2026): soft rows (look E) grouped by day,
// and folders (Coming up, Waiting, Confirmed, Past & cancelled) instead of tabs and chips.
const rowsOf = (w: VueWrapper) => w.findAll('.soft-row')
const titles = (w: VueWrapper) => rowsOf(w).map((r) => r.get('h3').text())
const rowOf = (w: VueWrapper, title: string) => rowsOf(w).find((r) => r.get('h3').text() === title)!
const folders = (w: VueWrapper) => w.findAll('.folder').map((f) => `${f.get('.label').text()} ${f.get('.n').text()}`)
async function openFolder(w: VueWrapper, label: string) {
  await w
    .findAll('.folder')
    .find((f) => f.get('.label').text() === label)!
    .trigger('click')
}
const panel = () => document.body.querySelector('.side-panel, [role="dialog"]')
async function openCard(w: VueWrapper, title: string) {
  await rowOf(w, title).trigger('click')
  await flushPromises()
}
function buttonIn(root: Element, text: string) {
  return [...root.querySelectorAll('button')].find((b) => b.textContent?.trim() === text) as HTMLButtonElement | undefined
}
// Cancel booking sits in the ⋯ menu of the panel foot.
async function more() {
  panel()!.querySelector<HTMLButtonElement>('button[aria-label="More actions"]')!.click()
  await flushPromises()
}

describe('My bookings', () => {
  it('lists what is coming up, with counts on the folders', async () => {
    const w = await open()
    expect(titles(w)).toEqual(['Budget review', 'Team sync'])
    expect(folders(w)).toEqual(['Coming up 2', 'Waiting 1', 'Confirmed 1', 'Past & cancelled 2'])
    expect(w.get('.folder[aria-current="page"] .label').text()).toBe('Coming up')
  })

  it('has no buttons on the rows: the door pass is in the pop-up (owner pick, 13 Nov 2026)', async () => {
    const w = await open()
    expect(w.findAll('.soft-row button')).toHaveLength(0)
  })

  it('lists cancelled and completed under Past & cancelled, newest first', async () => {
    const w = await open()
    await openFolder(w, 'Past & cancelled')
    expect(titles(w)).toEqual(['Old plan', 'Kick-off'])
    expect(w.get('.folder[aria-current="page"] .label').text()).toBe('Past & cancelled')
  })

  it("says in the row's footer where the booking is and what happens next, with an icon", async () => {
    mine = [
      SOON,
      WAITING,
      bookingItem(30, 'Owner check', 'PENDING_OWNER', '2026-11-17'),
      bookingItem(31, 'Private sync', 'PENDING_PITIKA', '2026-11-18', { room: { ...SOON.room, is_private: true } }),
      bookingItem(32, 'With IT', 'CONFIRMED', '2026-11-19', { has_it: true }),
    ]
    const w = await open()
    const foot = (title: string) => {
      const row = rowOf(w, title)
      return [row.get('.stt').text(), row.get('.nx').text(), row.find('.stt svg').exists()]
    }
    expect(foot('Budget review')).toEqual(['Confirmed', 'Door pass ready', true])
    expect(foot('Team sync')).toEqual(['Waiting for Pitika', 'Pitika checks it next', true])
    expect(foot('Owner check')).toEqual(['Waiting for the room owner', 'Private room · the owner decides', true])
    expect(foot('Private sync')).toEqual(['Waiting for Pitika', 'Pitika checks it next, then the room owner', true])
    expect(foot('With IT')).toEqual(['Confirmed', 'Door pass ready · IT sets up the room', true])
    // Never a coloured dot for a status (owner rule).
    expect(w.findAll('.soft-row .dot')).toHaveLength(0)
  })

  it('shows the room line and the tags: Private, Food, IT help', async () => {
    mine = [bookingItem(33, 'Full', 'PENDING_PITIKA', '2026-11-16', { room: { ...SOON.room, is_private: true }, has_catering: true, has_it: true })]
    const w = await open()
    const row = rowOf(w, 'Full')
    expect(row.findAll('.line .bit').map((b) => b.text())).toEqual(['x', 'Mekong Room', '2nd floor · A', '8'])
    expect(row.findAll('.soft-tag').map((t) => t.text())).toEqual(['Private', 'Food', 'IT help'])
    expect(row.get('.ref').text()).toBe('NBC-26-33')
    expect(row.get('.sent').text()).toBe('Sent Tue 10 Nov, 09:00')
  })

  it('opens the details from ?booking=', async () => {
    await open('?booking=7')
    expect(calls).toContain('GET /api/v1/bookings/7')
    expect(panel()?.textContent).toContain('Budget review')
    expect(panel()?.textContent).toContain('NBC-26-7')
  })

  it('cancels with the version it read, and the card moves to Past', async () => {
    const w = await open()
    await openCard(w, 'Budget review')
    expect(panel()!.querySelector('textarea')).toBeNull()
    await more()
    buttonIn(panel()!, 'Cancel booking')!.click()
    await flushPromises()
    expect(panel()!.textContent).toContain('Cancel this booking?')
    buttonIn(panel()!, 'Yes, cancel booking')!.click()
    await flushPromises()
    expect(useConfirm().current.value).toBeNull()
    expect(bodies['POST /api/v1/bookings/7/cancel']).toEqual({ version: 3 })
    expect(titles(w)).toEqual(['Team sync'])
    await openFolder(w, 'Past & cancelled')
    expect(titles(w)).toContain('Budget review')
  })

  it('says the booking changed when someone saved first', async () => {
    cancelAnswer = () => [{ error: { code: 'STALE_VERSION', message: 'Stale.' } }, 409]
    const w = await open()
    await openCard(w, 'Budget review')
    await more()
    buttonIn(panel()!, 'Cancel booking')!.click()
    await flushPromises()
    buttonIn(panel()!, 'Yes, cancel booking')!.click()
    await flushPromises()
    expect(panel()?.textContent).toContain('This item changed. Reload it.')
  })

  it('asks for the cancel reason only after Cancel booking, and Keep it closes the question', async () => {
    const w = await open()
    await openCard(w, 'Budget review')
    await more()
    buttonIn(panel()!, 'Cancel booking')!.click()
    await flushPromises()
    const reason = panel()!.querySelector('textarea')!
    reason.value = 'The date moved.'
    reason.dispatchEvent(new Event('input'))
    buttonIn(panel()!, 'Keep it')!.click()
    await flushPromises()
    expect(panel()!.querySelector('textarea')).toBeNull()
    expect(buttonIn(panel()!, 'Add to calendar')).toBeTruthy()
    expect(calls).not.toContain('POST /api/v1/bookings/7/cancel')
  })

  it('sends the cancel reason when one is written', async () => {
    const w = await open()
    await openCard(w, 'Budget review')
    await more()
    buttonIn(panel()!, 'Cancel booking')!.click()
    await flushPromises()
    const reason = panel()!.querySelector('textarea')!
    reason.value = 'The date moved.'
    reason.dispatchEvent(new Event('input'))
    buttonIn(panel()!, 'Yes, cancel booking')!.click()
    await flushPromises()
    expect(bodies['POST /api/v1/bookings/7/cancel']).toEqual({
      version: 3,
      reason: 'The date moved.',
    })
  })

  it('puts a small room photo by the title, the status band, and a thin step bar', async () => {
    rooms = [
      {
        id: 12,
        cover_photo: { url: '/uploads/rooms/12/a.jpg', thumbnail_url: '/uploads/rooms/12/a_t.jpg' },
      },
    ]
    const w = await open()
    await openCard(w, 'Budget review')
    expect(panel()!.querySelector('.panel-head .room-thumb img')?.getAttribute('src')).toContain('/uploads/rooms/12/a.jpg')
    expect(panel()!.querySelector('.panel-cover')).toBeNull()
    expect(panel()!.querySelector('.band.ok .say-status')?.textContent?.trim()).toBe('Confirmed · the room is yours')
    expect(panel()!.querySelector('.band small')?.textContent?.trim()).toBe('Fri 13 Nov')
    // The top is the title and the code only; the room is in the Room section (17 Nov 2026).
    expect(panel()!.querySelector('.subtitle')?.textContent?.trim()).toBe('NBC-26-7')
    expect(panel()!.querySelector('.step-progress .line')?.textContent?.trim()).toBe('Step 3 of 3')
  })

  it('shows the door tile by the title, and the status band, when the room has no photo', async () => {
    const w = await open()
    await openCard(w, 'Team sync')
    expect(panel()!.querySelector('.panel-head .room-thumb.none')).not.toBeNull()
    expect(panel()!.querySelector('.band.wait .say-status')?.textContent?.trim()).toBe('Waiting for Pitika')
  })

  it('keeps the door pass in the ⋯ menu: it shows the code above the buttons, with Copy and Hide', async () => {
    const w = await open()
    await openCard(w, 'Budget review')
    expect(panel()!.querySelector('.bd')?.textContent).not.toContain('Door pass')
    await more()
    const item = buttonIn(panel()!.querySelector('[role="menu"]')!, 'Show door pass')!
    expect(item.getAttribute('role')).toBe('menuitem')
    item.click()
    await flushPromises()
    expect(calls).toContain('GET /api/v1/bookings/7/door-pass')
    expect(panel()!.querySelector('[role="menu"]')).toBeNull()
    const pass = panel()!.querySelector('.panel-foot .pass')!
    expect(pass.querySelector('.pass-code')?.textContent).toBe('482913')
    expect(pass.querySelector('[aria-label="Copy door pass"]')).not.toBeNull()
    pass.querySelector<HTMLButtonElement>('[aria-label="Hide door pass"]')!.click()
    await flushPromises()
    expect(panel()!.querySelector('.panel-foot .pass')).toBeNull()
  })

  it('offers no door pass while the booking waits, or after the meeting', async () => {
    const w = await open()
    await openCard(w, 'Team sync')
    await more()
    expect(buttonIn(panel()!, 'Show door pass')).toBeUndefined()
  })

  it('keeps Add to calendar as the main button and closes the menu with Escape, not the panel', async () => {
    const w = await open()
    await openCard(w, 'Budget review')
    expect(panel()!.querySelector('.panel-foot .main')?.textContent?.trim()).toBe('Add to calendar')
    expect(panel()!.querySelector('[role="menu"]')).toBeNull()
    await more()
    const menu = panel()!.querySelector('[role="menu"]')!
    expect(document.activeElement?.textContent?.trim()).toBe('Show door pass')
    menu.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true, cancelable: true }))
    await flushPromises()
    expect(panel()!.querySelector('[role="menu"]')).toBeNull()
    expect(panel()?.textContent).toContain('Budget review')
  })

  describe('request slip', () => {
    const SLIP = 'ប័ណ្ណស្នើ (Word)'
    let saved: string[]
    beforeEach(() => {
      saved = []
      URL.createObjectURL = vi.fn<typeof URL.createObjectURL>(() => 'blob:1')
      URL.revokeObjectURL = vi.fn<typeof URL.revokeObjectURL>()
      vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(function (this: HTMLAnchorElement) {
        saved.push(this.download)
      })
    })
    afterEach(() => vi.restoreAllMocks())

    it('downloads the Word slip of a confirmed booking', async () => {
      const w = await open()
      await openCard(w, 'Budget review')
      buttonIn(panel()!, SLIP)!.click()
      await flushPromises()
      expect(calls).toContain('GET /api/v1/bookings/7/request-slip')
      expect(saved).toEqual(['request-slip-NBC-26-7.docx'])
    })

    it('is not offered while the booking waits', async () => {
      const w = await open()
      await openCard(w, 'Team sync')
      expect(buttonIn(panel()!, SLIP)).toBeUndefined()
      expect(buttonIn(panel()!, 'Add to calendar')).toBeTruthy()
    })

    it('is still offered when the meeting is over', async () => {
      detail8 = bookingDetail({ ...WAITING, status: 'CONFIRMED', display_status: 'COMPLETED' })
      const w = await open()
      await openCard(w, 'Team sync')
      expect(buttonIn(panel()!, SLIP)).toBeTruthy()
      await more()
      expect(panel()!.textContent).toContain('Copy reference')
      expect(buttonIn(panel()!, 'Cancel booking')).toBeUndefined()
    })

    it('says so when the slip cannot load', async () => {
      slipFails = true
      const w = await open()
      await openCard(w, 'Budget review')
      buttonIn(panel()!, SLIP)!.click()
      await flushPromises()
      expect(panel()!.textContent).toContain('This booking is not confirmed yet.')
      expect(saved).toEqual([])
    })
  })

  it('shows why a booking was not approved, who said so and when', async () => {
    detail8 = bookingDetail(
      { ...WAITING, status: 'REJECTED', display_status: 'REJECTED' },
      {
        rejection: {
          rejected_by: 'PITIKA',
          actor: { id: 3, name_en: 'Chan Rath' },
          reason: 'The hall is kept for a visit.',
          decided_at: '2026-11-11T03:42:00Z',
          by_admin: false,
        },
      },
    )
    const w = await open()
    await openCard(w, 'Team sync')
    const note = panel()!.querySelector('.callout')!
    expect(note.textContent).toContain('Not approved by Pitika')
    expect(note.textContent).toContain('The hall is kept for a visit.')
    expect(note.textContent).toContain('Chan Rath')
    expect(buttonIn(panel()!, 'Cancel booking')).toBeUndefined()
  })

  it('shows the same Details as Pitika: every session, the meeting, and the booker', async () => {
    detail8 = bookingDetail(WAITING, {
      sessions: [
        { id: 1, date: '2026-11-16', start_time: '12:30', end_time: '18:00' },
        { id: 2, date: '2026-11-17', start_time: '07:30', end_time: '18:00' },
      ],
      requester_info: { name_en: 'Sok Dara', staff_id: 'NBC0042', position: 'Officer', department: 'Operations', division: 'Payments' },
      participant_emails: ['a@nbc.gov.kh'],
    })
    const w = await open()
    await openCard(w, 'Team sync')
    const details = panel()!.querySelector('#tabpanel-details')!
    const rows = [...details.querySelectorAll('.sessions li')].map((li) => [...li.children].map((c) => c.textContent?.trim()).join(' '))
    expect(rows).toEqual(['Mon 16 Nov 2026 12:30–18:00', 'Tue 17 Nov 2026 07:30–18:00'])
    expect(details.querySelector('.sessions-head')?.textContent).toContain('2 sessions')
    expect([...details.querySelectorAll('.panel-section > h3')].map((h) => h.textContent?.replace(/\s+/g, ' ').trim())).toEqual(['When · 2 sessions', 'Room', 'Meeting', 'Booker'])
    const facts = [...details.querySelectorAll('.details dt')].map((d) => d.textContent?.trim())
    expect(facts).toEqual(['Room', 'Where', 'Office', 'Seats', 'Meeting type', 'Attendees', 'Purpose', 'Route', 'Invited', 'Sent', 'Staff ID', 'Name', 'Position', 'Department', 'Phone', 'Email'])
    expect(details.textContent).toContain('1 by email')
    expect(details.textContent).toContain('NBC0042')
  })

  describe('quiet refresh', () => {
    beforeEach(() => {
      vi.useFakeTimers({ toFake: ['Date', 'setInterval', 'clearInterval'] })
      vi.setSystemTime(new Date('2026-11-12T03:00:00Z'))
    })

    it('shows a new booking with no click', async () => {
      const w = await open()
      mine = [...mine, bookingItem(11, 'New plan', 'PENDING_PITIKA', '2026-11-17')]
      vi.advanceTimersByTime(15_000)
      await flushPromises()
      expect(titles(w)).toEqual(['Budget review', 'Team sync', 'New plan'])
    })

    it('updates an open booking when someone decides it', async () => {
      await open('?booking=8')
      expect(panel()?.textContent).toContain('Waiting for Pitika')
      detail8 = bookingDetail({
        ...WAITING,
        status: 'CONFIRMED',
        display_status: 'CONFIRMED',
        version: 4,
      })
      vi.advanceTimersByTime(15_000)
      await flushPromises()
      expect(panel()?.textContent).toContain('Confirmed')
      expect(panel()?.textContent).not.toContain('Waiting for Pitika')
    })
  })

  describe('refresh button', () => {
    it('refreshes at once', async () => {
      const w = await open()
      mine = [...mine, bookingItem(12, 'Fresh plan', 'PENDING_PITIKA', '2026-11-18')]
      await w.get('button[aria-label="Refresh"]').trigger('click')
      await flushPromises()
      expect(titles(w)).toContain('Fresh plan')
    })

    it('says when the server cannot be reached, keeps the list, and Try again works', async () => {
      const w = await open()
      mineFails = true
      await w.get('button[aria-label="Refresh"]').trigger('click')
      await flushPromises()
      expect(w.get('[role="status"]').text()).toContain("Can't reach the server.")
      expect(titles(w)).toEqual(['Budget review', 'Team sync'])
      mineFails = false
      vi.setSystemTime(Date.now() + 3_000) // a moment later (clicks within 2 s send nothing)
      await w.get('[role="status"] button').trigger('click')
      await flushPromises()
      expect(w.find('[role="status"]').exists()).toBe(false)
    })
  })

  it('waits as the server asks after "too many requests", and says so', async () => {
    const w = await open()
    mineLimited = true
    await w.get('button[aria-label="Refresh"]').trigger('click')
    await flushPromises()
    expect(w.get('.offline-note').text()).toContain('Too many requests. Trying again in 20 s.')
    const asked = calls.filter((c) => c === 'GET /api/v1/bookings/mine').length
    vi.setSystemTime(Date.now() + 5_000)
    await w.get('button[aria-label="Refresh"]').trigger('click')
    await flushPromises()
    expect(calls.filter((c) => c === 'GET /api/v1/bookings/mine').length).toBe(asked)
  })
})

describe('Files on my booking', () => {
  const AGENDA = { id: 1, file_name: 'agenda.pdf', content_type: 'application/pdf', size_bytes: 2048, created_at: '2026-11-10T02:00:00Z', url: '/api/v1/bookings/8/attachments/1' }
  const names = () => [...panel()!.querySelectorAll('.att-name')].map((n) => n.textContent)

  it('adds and removes files while the booking is waiting', async () => {
    detail8 = bookingDetail(WAITING, { attachments: [AGENDA] })
    const w = await open()
    await openCard(w, 'Team sync')
    expect(names()).toEqual(['agenda.pdf'])
    const input = panel()!.querySelector<HTMLInputElement>('input[type="file"]')!
    Object.defineProperty(input, 'files', { value: [new File(['%PDF-1'], 'notes.pdf')], configurable: true })
    input.dispatchEvent(new Event('change'))
    await flushPromises()
    expect(calls).toContain('POST /api/v1/bookings/8/attachments')
    expect(names()).toEqual(['agenda.pdf', 'notes.pdf'])
    panel()!.querySelector<HTMLButtonElement>('[aria-label="Remove agenda.pdf"]')!.click()
    await flushPromises()
    expect(calls).toContain('DELETE /api/v1/bookings/8/attachments/1')
    expect(names()).toEqual(['notes.pdf'])
  })

  it('shows files read only once confirmed', async () => {
    detail8 = bookingDetail({ ...WAITING, status: 'CONFIRMED', display_status: 'CONFIRMED' }, { attachments: [AGENDA] })
    const w = await open()
    await openCard(w, 'Team sync')
    expect(names()).toEqual(['agenda.pdf'])
    expect(panel()!.textContent).not.toContain('Add file')
    expect(panel()!.querySelector('[aria-label="Remove agenda.pdf"]')).toBeNull()
  })

  it('shows no Files block on a confirmed booking with no file', async () => {
    detail8 = bookingDetail({ ...WAITING, status: 'CONFIRMED', display_status: 'CONFIRMED' })
    const w = await open()
    await openCard(w, 'Team sync')
    expect(panel()!.querySelector('.att')).toBeNull()
  })
})

describe('Tabs on my booking', () => {
  const FOOD = {
    packages: [
      { id: 1, name: 'Coffee break' },
      { id: 2, name: 'តែ' },
    ],
    remarks: 'Less sugar, please.',
    delivery_date: '2026-11-16',
    delivery_time: '09:00',
    approver_notes: 'Food is fine for 8.',
    decided_by: { id: 3, name_en: 'Chan Sophea' },
    decided_at: '2026-11-12T07:05:00Z',
  }
  const IT = {
    ticket_id: 1,
    items: [
      { id: 10, name: 'Video call' },
      { id: 11, name: 'Projector setup' },
    ],
    special_requirements: 'Two microphones.',
    status: 'READY',
    technician_notes: 'Sound tested.',
    staff: [{ id: 20, name_en: 'Keo Rithy', name_kh: 'x' }],
    setup_date: '2026-11-16',
    setup_time: '08:30',
    forwarded_at: '2026-11-12T07:05:00Z',
    assigned_at: '2026-11-13T02:00:00Z',
    ready_at: '2026-11-16T01:40:00Z',
  }
  const PITIKA_YES = {
    stage: 'PITIKA',
    decision: 'APPROVED',
    reviewer: { id: 3, name_en: 'Chan Sophea' },
    notes: 'Food is fine for 8.',
    reviewed_at: '2026-11-12T07:05:00Z',
    by_admin: false,
  }
  const DONE_FULL = () =>
    bookingDetail({ ...WAITING, status: 'CONFIRMED', display_status: 'COMPLETED', has_catering: true, has_it: true }, { catering: FOOD, it: IT, reviews: [PITIKA_YES] })
  const tabNames = () => [...panel()!.querySelectorAll('[role="tab"]')].map((t) => t.textContent?.trim())
  const tabPanel = (id: string) => panel()!.querySelector<HTMLElement>(`#tabpanel-${id}`)!
  async function pickTab(id: string) {
    panel()!.querySelector<HTMLButtonElement>(`#tab-${id}`)!.click()
    await flushPromises()
  }

  it('splits the pop-up into Details, Food & IT and History; status, steps and the slip stay', async () => {
    detail8 = DONE_FULL()
    const w = await open()
    await openCard(w, 'Team sync')
    expect(tabNames()).toEqual(['Details', 'Food & IT 4', 'History'])
    expect(panel()!.querySelector('[role="tab"][aria-selected="true"]')?.textContent?.trim()).toBe('Details')
    expect(panel()!.querySelector('[role="tabpanel"] .band')).toBeNull()
    expect(panel()!.querySelector('[role="tabpanel"] .step-progress')).toBeNull()
    expect(tabPanel('details').textContent).toContain('Sent')
    expect(tabPanel('details').textContent).toContain('10 Nov 2026, 09:00')
    expect(tabPanel('services').style.display).toBe('none')
    await pickTab('services')
    expect(tabPanel('details').style.display).toBe('none')
    expect(tabPanel('services').style.display).toBe('')
    expect(buttonIn(panel()!, 'ប័ណ្ណស្នើ (Word)')).toBeTruthy()
  })

  // IT is an add-on (owner pick F, 19 Nov 2026): a fourth step after Confirmed, and its words on
  // the right of the step line; a click there opens Food & IT.
  const withIt = (it: Record<string, unknown>, first = '2026-11-16') =>
    bookingDetail(
      { ...WAITING, status: 'CONFIRMED', display_status: 'CONFIRMED', has_it: true, first_session: { id: 80, date: first, start_time: '09:00', end_time: '10:00' } },
      { it: { ...IT, ...it }, reviews: [PITIKA_YES], confirmed_at: '2026-11-12T07:05:00Z' },
    )
  const segs = () => [...panel()!.querySelectorAll('.step-progress .seg')].map((s) => s.className.replace('seg', '').trim())
  const itLine = () => panel()!.querySelector<HTMLButtonElement>('.step-progress button.it-line')

  it('shows IT setup after Confirmed on the step line, and opens Food & IT from it', async () => {
    detail8 = withIt({ status: 'ASSIGNED', ready_at: null })
    const w = await open()
    await openCard(w, 'Team sync')
    expect(panel()!.querySelector('.band')?.textContent).toContain('Confirmed')
    expect(segs()).toEqual(['done', 'done', 'done', 'now'])
    expect(panel()!.querySelector('.step-progress .line span')?.textContent).toBe('Step 4 of 4')
    expect(itLine()?.textContent?.trim()).toBe('IT setup · Setting up')
    expect(itLine()?.classList).toContain('wait')
    itLine()!.click()
    await flushPromises()
    expect(tabPanel('services').style.display).toBe('')
  })

  it('says Room ready in green, and Not marked ready in crimson when IT missed it', async () => {
    detail8 = withIt({})
    let w = await open()
    await openCard(w, 'Team sync')
    expect(segs()).toEqual(['done', 'done', 'done', 'done'])
    expect(itLine()?.textContent?.trim()).toBe('Room ready')
    expect(itLine()?.classList).toContain('ok')
    w.unmount()

    detail8 = withIt({ status: 'ASSIGNED', ready_at: null }, '2026-11-12') // started 09:00, now 10:00
    w = await open()
    await openCard(w, 'Team sync')
    expect(segs()).toEqual(['done', 'done', 'done', 'stop'])
    expect(itLine()?.textContent?.trim()).toBe('IT setup · Not marked ready')
    expect(itLine()?.classList).toContain('stop')
  })

  it('shows no IT words on a booking without IT help', async () => {
    detail8 = bookingDetail({ ...WAITING, status: 'CONFIRMED', display_status: 'CONFIRMED' }, { reviews: [PITIKA_YES] })
    const w = await open()
    await openCard(w, 'Team sync')
    expect(segs()).toEqual(['done', 'done', 'done'])
    expect(itLine()).toBeNull()
  })

  it('shows each food item with the amount, the note, and who checked it', async () => {
    detail8 = DONE_FULL()
    const w = await open()
    await openCard(w, 'Team sync')
    const food = panel()!.querySelector('.svc-card[data-kind="food"]')!
    expect([...food.querySelectorAll('.svc-items li')].map((li) => li.textContent?.replace(/\s+/g, ' ').trim())).toEqual(['Coffee break', 'តែ'])
    expect(food.querySelector('.pill')?.textContent?.trim()).toBe('Approved')
    expect(food.textContent).toContain('Mon 16 Nov 2026 · 09:00')
    expect(food.textContent).toContain('“Less sugar, please.”')
    expect(food.textContent).toContain('Chan Sophea')
    expect(food.textContent).toContain('12 Nov 2026, 14:05')
    expect(food.textContent).toContain('“Food is fine for 8.”')
  })

  it('shows the IT items, the note, the IT staff and when the room was ready', async () => {
    detail8 = DONE_FULL()
    const w = await open()
    await openCard(w, 'Team sync')
    const it = panel()!.querySelector('.svc-card[data-kind="it"]')!
    expect([...it.querySelectorAll('.svc-items li')].map((li) => li.textContent?.trim())).toEqual(['Video call', 'Projector setup'])
    expect(it.querySelector('.pill')?.textContent?.trim()).toBe('Room ready')
    expect(it.textContent).toContain('“Two microphones.”')
    expect(it.textContent).toContain('Keo Rithy')
    expect(it.textContent).toContain('16 Nov 2026, 08:40')
    expect(it.textContent).toContain('IT note')
    expect(it.textContent).toContain('“Sound tested.”')
  })

  it('says when no food or IT help was asked, and that food waits for a check', async () => {
    detail8 = bookingDetail(WAITING, { catering: { ...FOOD, approver_notes: null, decided_by: null, decided_at: null } })
    const w = await open()
    await openCard(w, 'Team sync')
    expect(tabNames()).toContain('Food & IT 2')
    expect(panel()!.querySelector('.svc-card[data-kind="food"] .pill')?.textContent?.trim()).toBe('Waiting')
    expect(tabPanel('services').textContent).toContain('No IT help asked.')
  })

  it('shows the History timeline: who did what, their role, when, and what it waits for', async () => {
    detail8 = bookingDetail({ ...WAITING, status: 'SETUP_IN_PROGRESS', display_status: 'SETUP_IN_PROGRESS' }, { reviews: [PITIKA_YES] })
    const w = await open()
    await openCard(w, 'Team sync')
    const h = tabPanel('history')
    const labels = [...h.querySelectorAll('.timeline .label')].map((l) => l.textContent?.trim())
    expect(labels).toEqual(['Sent', 'Approved', 'Waiting for IT to be ready'])
    const approved = [...h.querySelectorAll('.timeline li')][1]!
    expect(approved.querySelector('.name')?.textContent?.trim()).toBe('Chan Sophea')
    expect(approved.querySelector('.role')?.textContent?.trim()).toBe('Pitika')
    expect(approved.querySelector('.time')?.textContent?.trim()).toBe('12 Nov 2026, 14:05')
    // The label has its line to itself, so a long one never wraps (owner,
    // 19 Nov 2026: "one line only"); the time sits on the who line, at its end.
    expect(approved.querySelector('.line1 .time')).toBeNull()
    expect(approved.querySelector('.who .time')).not.toBeNull()
    expect(approved.querySelector('.note')?.textContent?.trim()).toBe('Food is fine for 8.')
    expect(h.querySelector('.steps')).toBeNull()
  })

  it('shows Sent and Waiting for Pitika on a new booking', async () => {
    const w = await open()
    await openCard(w, 'Team sync')
    expect(tabNames()).toContain('History')
    const labels = [...tabPanel('history').querySelectorAll('.timeline .label')].map((l) => l.textContent?.trim())
    expect(labels).toEqual(['Sent', 'Waiting for Pitika'])
  })

  it('has a Files tab while files can still be added, and none on a confirmed booking with no file', async () => {
    const w = await open()
    await openCard(w, 'Team sync')
    expect(tabNames()).toEqual(['Details', 'Food & IT', 'Files', 'History'])
    expect(tabPanel('files').querySelector('input[type="file"]')).not.toBeNull()
    w.unmount()
    detail8 = bookingDetail({ ...WAITING, status: 'CONFIRMED', display_status: 'CONFIRMED' })
    const w2 = await open()
    await openCard(w2, 'Team sync')
    expect(tabNames()).toEqual(['Details', 'Food & IT', 'History'])
  })
})

describe('Finding a booking (owner pick, 20 Nov 2026: layout 2, folders on the left)', () => {
  // Now: Thu 12 Nov 2026, 10:00 in Phnom Penh.
  const at = (date: string, start = '09:00', end = '10:00') => ({ id: 1, date, start_time: start, end_time: end })
  const NOW_ON = bookingItem(21, 'Board talk', 'CONFIRMED', '2026-11-12', { next_session: at('2026-11-12', '09:30', '11:00') })
  const TOMORROW = bookingItem(22, 'Budget review', 'CONFIRMED', '2026-11-13')
  const WEEK = bookingItem(23, 'Team sync', 'PENDING_PITIKA', '2026-11-16', { room: { ...SOON.room, name_en: 'Bassac Room' } })
  const LATER = bookingItem(24, 'Year plan', 'PENDING_OWNER', '2026-11-30')
  const STARTED = bookingItem(25, 'Long training', 'CONFIRMED', '2026-11-09', { session_count: 5, next_session: at('2026-11-13', '14:00', '16:00') })
  const groups = (w: VueWrapper) =>
    w.findAll('section.day').map((g) => {
      const head = g.get('h2')
      const day = head.text().replace(head.get('.n').text(), '').trim()
      return [day, head.get('.n').text(), g.findAll('.soft-row h3').map((h) => h.text())]
    })
  beforeEach(() => {
    mine = [NOW_ON, TOMORROW, WEEK, LATER, STARTED, GONE, DONE]
  })

  it('groups Coming up by the day of the next session, with a count on each day', async () => {
    const w = await open()
    expect(groups(w)).toEqual([
      ['Today · Thu 12 Nov', '01', ['Board talk']],
      ['Fri 13 Nov', '02', ['Budget review', 'Long training']],
      ['Mon 16 Nov', '01', ['Team sync']],
      ['Mon 30 Nov', '01', ['Year plan']],
    ])
    expect(w.get('.day-head.today').text()).toContain('Today')
    expect(w.findAll('.day-head.today')).toHaveLength(1)
  })

  it('shows the next session on the row, not the first one, and says when one is under way', async () => {
    const w = await open()
    const long = rowOf(w, 'Long training')
    expect([long.get('.start').text(), long.get('.end').text()]).toEqual(['14:00', '16:00'])
    expect(long.get('.more').text()).toBe('5 days')
    expect(long.get('.time .day').text()).toBe('Fri 13')
    const now = rowOf(w, 'Board talk')
    expect(now.classes()).toContain('is-live')
    expect(now.get('.stt').text()).toBe('Happening now')
    expect(now.get('.nx').text()).toBe('Until 11:00 · your door pass works until then')
    expect(now.get('.time .day').text()).toBe('Today')
    expect(now.find('.soon-pill').exists()).toBe(false)
    expect(w.findAll('.soft-row.is-live')).toHaveLength(1)
  })

  it('says how soon a meeting later today starts', async () => {
    mine = [bookingItem(26, 'Lunch talk', 'CONFIRMED', '2026-11-12', { first_session: at('2026-11-12', '14:30', '15:00'), next_session: at('2026-11-12', '14:30', '15:00') })]
    const w = await open()
    expect(rowOf(w, 'Lunch talk').get('.soon-pill').text()).toBe('Starts in 4 h 30 min')
  })

  it('filters Coming up by the Waiting and Confirmed folders, with counts', async () => {
    const w = await open()
    expect(folders(w)).toEqual(['Coming up 5', 'Waiting 2', 'Confirmed 3', 'Past & cancelled 2'])
    await openFolder(w, 'Waiting')
    expect(titles(w)).toEqual(['Team sync', 'Year plan'])
    expect(w.get('.folder[aria-current="page"] .label').text()).toBe('Waiting')
    await openFolder(w, 'Confirmed')
    expect(titles(w)).toEqual(['Board talk', 'Budget review', 'Long training'])
    await openFolder(w, 'Coming up')
    expect(titles(w)).toHaveLength(5)
  })

  it('says when a folder is empty, and Show all brings every booking back', async () => {
    mine = [TOMORROW]
    const w = await open()
    await openFolder(w, 'Waiting')
    expect(w.text()).toContain('No booking is waiting for approval.')
    await w
      .findAll('button')
      .find((b) => b.text() === 'Show all')!
      .trigger('click')
    expect(titles(w)).toEqual(['Budget review'])
  })

  it('says when nothing is coming up', async () => {
    mine = [GONE]
    const w = await open()
    expect(w.text()).toContain('Nothing coming up')
    expect(titles(w)).toEqual([])
  })

  it('searches by title, room or reference, in every folder', async () => {
    const w = await open()
    const search = w.get('input[type="search"]')
    await search.setValue('bassac')
    expect(titles(w)).toEqual(['Team sync'])
    await search.setValue('NBC-26-24')
    expect(titles(w)).toEqual(['Year plan'])
    await search.setValue('old')
    await openFolder(w, 'Past & cancelled')
    expect(titles(w)).toEqual(['Old plan'])
    expect(folders(w)).toEqual(['Coming up 0', 'Waiting 0', 'Confirmed 0', 'Past & cancelled 1'])
  })

  it('says when nothing matches, and Clear search brings the list back', async () => {
    const w = await open()
    await w.get('input[type="search"]').setValue('zzz')
    expect(w.text()).toContain('No bookings match “zzz”.')
    await w
      .findAll('button')
      .find((b) => b.text() === 'Clear search')!
      .trigger('click')
    expect(titles(w)).toHaveLength(5)
  })
})
