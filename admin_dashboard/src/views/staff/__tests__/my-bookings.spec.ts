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
const titles = (w: VueWrapper) => w.findAll('.bk-card h2').map((h) => h.text())
const panel = () => document.body.querySelector('.side-panel, [role="dialog"]')
async function openCard(w: VueWrapper, title: string) {
  await w
    .findAll('.bk-card')
    .find((c) => c.get('h2').text() === title)!
    .trigger('click')
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
  it('lists what is coming up, with counts on the tabs', async () => {
    const w = await open()
    expect(titles(w)).toEqual(['Budget review', 'Team sync'])
    const tabs = w.findAll('[role="tab"]').map((t) => t.text().replace(/\s+/g, ' '))
    expect(tabs).toEqual(['Coming up 2', 'Past & cancelled 2'])
  })

  it('has no Door pass button on the cards (owner pick, 13 Nov 2026)', async () => {
    const w = await open()
    for (const card of w.findAll('.bk-card')) expect(card.text()).not.toContain('Door pass')
    expect(w.findAll('.bk-card button')).toHaveLength(0)
  })

  it('lists cancelled and completed under Past & cancelled', async () => {
    const w = await open()
    await w.findAll('[role="tab"]')[1]!.trigger('click')
    expect(titles(w)).toEqual(['Old plan', 'Kick-off'])
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
    await w.findAll('[role="tab"]')[1]!.trigger('click')
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

  it('puts the room photo on top with the title and the room on it, and the status band under it', async () => {
    rooms = [
      {
        id: 12,
        cover_photo: { url: '/uploads/rooms/12/a.jpg', thumbnail_url: '/uploads/rooms/12/a_t.jpg' },
      },
    ]
    const w = await open()
    await openCard(w, 'Budget review')
    expect(panel()!.querySelector('.panel-cover img')?.getAttribute('src')).toContain('/uploads/rooms/12/a.jpg')
    expect(panel()!.querySelector('.panel-head.on-cover')).not.toBeNull()
    expect(panel()!.querySelector('.band.ok .say-status')?.textContent?.trim()).toBe('Confirmed · the room is yours')
    expect(panel()!.querySelector('.band small')?.textContent?.trim()).toBe('Fri 13 Nov')
    expect(panel()!.querySelector('.subtitle')?.textContent).toContain('Mekong Room · NBC')
  })

  it('keeps the plain head and the status band when the room has no photo', async () => {
    const w = await open()
    await openCard(w, 'Team sync')
    expect(panel()!.querySelector('.panel-cover')).toBeNull()
    expect(panel()!.querySelector('.band.wait .say-status')?.textContent?.trim()).toBe('Waiting for Pitika')
  })

  it('keeps Add to calendar as the main button and closes the menu with Escape, not the panel', async () => {
    const w = await open()
    await openCard(w, 'Budget review')
    expect(panel()!.querySelector('.panel-foot .main')?.textContent?.trim()).toBe('Add to calendar')
    expect(panel()!.querySelector('[role="menu"]')).toBeNull()
    await more()
    const menu = panel()!.querySelector('[role="menu"]')!
    expect(document.activeElement?.textContent?.trim()).toBe('Copy reference')
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

  it('lists each session with its length and the total', async () => {
    detail8 = bookingDetail(WAITING, {
      sessions: [
        { id: 1, date: '2026-11-16', start_time: '12:30', end_time: '18:00' },
        { id: 2, date: '2026-11-17', start_time: '07:30', end_time: '18:00' },
      ],
    })
    const w = await open()
    await openCard(w, 'Team sync')
    const rows = [...panel()!.querySelectorAll('.sessions tr')].map((r) => [...r.querySelectorAll('td')].map((td) => td.textContent?.trim()))
    expect(rows).toEqual([
      ['Mon 16 Nov', '12:30–18:00', '5 h 30 min'],
      ['Tue 17 Nov', '07:30–18:00', '10 h 30 min'],
    ])
    expect(panel()!.textContent).toContain('16 h in all')
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
    servings: 8,
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

  it('splits the pop-up into Details, Food & IT and Approvals; status, steps and the slip stay', async () => {
    detail8 = DONE_FULL()
    const w = await open()
    await openCard(w, 'Team sync')
    expect(tabNames()).toEqual(['Details', 'Food & IT 4', 'Approvals 1'])
    expect(panel()!.querySelector('[role="tab"][aria-selected="true"]')?.textContent?.trim()).toBe('Details')
    expect(panel()!.querySelector('[role="tabpanel"] .band')).toBeNull()
    expect(panel()!.querySelector('[role="tabpanel"] .process-bar')).toBeNull()
    expect(tabPanel('details').textContent).toContain('Sent')
    expect(tabPanel('details').textContent).toContain('10 Nov 2026, 09:00')
    expect(tabPanel('services').style.display).toBe('none')
    await pickTab('services')
    expect(tabPanel('details').style.display).toBe('none')
    expect(tabPanel('services').style.display).toBe('')
    expect(buttonIn(panel()!, 'ប័ណ្ណស្នើ (Word)')).toBeTruthy()
  })

  it('shows each food item with the amount, the note, and who checked it', async () => {
    detail8 = DONE_FULL()
    const w = await open()
    await openCard(w, 'Team sync')
    const food = panel()!.querySelector('.svc-card[data-kind="food"]')!
    expect([...food.querySelectorAll('.svc-items li')].map((li) => li.textContent?.replace(/\s+/g, ' ').trim())).toEqual(['Coffee break × 8', 'តែ × 8'])
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

  it('lists who approved, and what it still waits for', async () => {
    detail8 = bookingDetail({ ...WAITING, status: 'SETUP_IN_PROGRESS', display_status: 'SETUP_IN_PROGRESS' }, { reviews: [PITIKA_YES] })
    const w = await open()
    await openCard(w, 'Team sync')
    const ap = tabPanel('approvals')
    expect(ap.querySelector('.ap-who')?.textContent?.trim()).toBe('Chan Sophea')
    expect(ap.querySelector('.ap-role')?.textContent?.trim()).toBe('Pitika')
    expect(ap.querySelector('.ap-when')?.textContent?.trim()).toBe('12 Nov 2026, 14:05')
    expect(ap.querySelector('.ap-note')?.textContent?.trim()).toBe('“Food is fine for 8.”')
    expect(ap.querySelector('.ap-wait')?.textContent?.trim()).toBe('IT is setting up the room')
  })

  it('says no one has approved yet while it waits for Pitika', async () => {
    const w = await open()
    await openCard(w, 'Team sync')
    expect(tabNames()).toContain('Approvals')
    expect(tabPanel('approvals').textContent).toContain('No one has approved yet.')
  })

  it('has a Files tab while files can still be added, and none on a confirmed booking with no file', async () => {
    const w = await open()
    await openCard(w, 'Team sync')
    expect(tabNames()).toEqual(['Details', 'Food & IT', 'Files', 'Approvals'])
    expect(tabPanel('files').querySelector('input[type="file"]')).not.toBeNull()
    w.unmount()
    detail8 = bookingDetail({ ...WAITING, status: 'CONFIRMED', display_status: 'CONFIRMED' })
    const w2 = await open()
    await openCard(w2, 'Team sync')
    expect(tabNames()).toEqual(['Details', 'Food & IT', 'Approvals'])
  })
})
