import { enableAutoUnmount, flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createMemoryHistory, createRouter } from 'vue-router'

import { useToast } from '../../composables/useToast'
import { useSessionStore } from '../../stores/session'
import { listItem } from '../../test-utils/bookings'
import { clearDate, pickDate } from '../../test-utils/datePicker'
import { choosePicker, pickerOptions } from '../../test-utils/picker'
import ReviewView from '../ReviewView.vue'

enableAutoUnmount(afterEach)

const session = (date: string, start = '14:00') => ({ id: 1, date, start_time: start, end_time: '15:30' })
const room = (id: number, name_en: string, name_kh: string) => ({ ...listItem(1).room, id, name_en, name_kh })

// Waiting bookings, as the Pitika list sends them (now: Thu 5 Nov 2026, 09:20 in Phnom Penh).
const ITEMS = [
  listItem(21, { title: 'x', meeting_title: 'Payment systems workshop', reference_code: 'NBC-26-87467', room: room(12, 'Mekong Room', 'បន្ទប់មេគង្គ'), first_session: session('2026-11-05'), has_it: true }),
  listItem(22, { meeting_title: 'Board briefing', reference_code: 'NBC-26-55102', route: 'R2', room: room(13, 'Governor Room', 'បន្ទប់ទេសាភិបាល'), first_session: session('2026-11-06', '09:00') }),
  listItem(23, { meeting_title: 'Audit prep', reference_code: 'NBC-26-44120', room: room(12, 'Mekong Room', 'បន្ទប់មេគង្គ'), first_session: session('2026-11-12', '15:00') }),
]
const DETAILS: Record<number, Record<string, unknown>> = {
  21: {
    catering: { packages: [{ id: 1, name: 'Lunch box' }], delivery_date: '2026-11-05', delivery_time: '14:00' },
    it: { items: [{ id: 2, name: 'Projector setup' }], status: 'RECEIVED', staff: [] },
    sessions: [
      { id: 1, date: '2026-11-05', start_time: '14:00', end_time: '15:30' },
      { id: 2, date: '2026-11-06', start_time: '09:00', end_time: '10:30' },
      { id: 3, date: '2026-11-07', start_time: '09:00', end_time: '10:30' },
    ],
  },
  22: { private_justification: "The Governor's team asked." },
  23: {},
}
const PP = { code: 'PHNOM_PENH', name_en: 'Phnom Penh', name_kh: 'ភ្នំពេញ' }
const SR = { code: 'SIEM_REAP', name_en: 'Siem Reap', name_kh: 'សៀមរាប' }
const ROOMS = [
  { id: 12, name_en: 'Mekong Room', name_kh: 'បន្ទប់មេគង្គ', location: { name_en: 'Head Office' }, province: PP, cover_photo: { url: '/uploads/rooms/12/a.jpg', thumbnail_url: '/uploads/rooms/12/a_t.jpg' } },
  { id: 13, name_en: 'Governor Room', name_kh: 'បន្ទប់ទេសាភិបាល', location: { name_en: 'Head Office' }, province: PP, cover_photo: null },
  { id: 40, name_en: 'Angkor Room', name_kh: 'បន្ទប់អង្គរ', location: { name_en: 'Siem Reap Branch' }, province: SR, cover_photo: null },
]

const calls: string[] = []
const bodies: string[] = []
let items: Array<ReturnType<typeof listItem>>
let decision: () => Response
let decidedItems: unknown[] = []
let holdRejected = false

function json(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } })
}

beforeEach(() => {
  vi.useFakeTimers({ toFake: ['Date'] })
  vi.setSystemTime(new Date('2026-11-05T02:20:00Z'))
  setActivePinia(createPinia())
  useSessionStore().accessToken = 'A1'
  useSessionStore().user = { roles: [{ code: 'PITIKA' }], province: PP } as never
  calls.length = 0
  bodies.length = 0
  decidedItems = []
  holdRejected = false
  items = ITEMS
  decision = () => json({ ...ITEMS[0], status: 'SETUP_IN_PROGRESS' })
  vi.stubGlobal(
    'fetch',
    vi.fn<typeof fetch>(async (input, init) => {
      const url = new URL(String(input))
      calls.push(`${init?.method ?? 'GET'} ${url.pathname}${url.search}`)
      if (/^\/api\/v1\/pitika\/bookings\/\d+\/(approve|reject)$/.test(url.pathname)) {
        bodies.push(String(init?.body))
        const answer = decision()
        if (answer.ok) items = items.filter((i) => !url.pathname.includes(`/${i.id}/`))
        return answer
      }
      if (url.pathname === '/api/v1/pitika/bookings') return json({ items, page: 1, size: 100, total: items.length })
      if (url.pathname === '/api/v1/pitika/bookings/summary') return json({ waiting: items.length, approved_today: 5, rejected_today: 1 })
      if (url.pathname === '/api/v1/pitika/bookings/decided') {
        if (url.searchParams.get('decision') === 'REJECTED' && holdRejected) return new Promise<Response>(() => {})
        return json({ items: decidedItems, page: 1, size: 20, total: decidedItems.length })
      }
      const detail = /^\/api\/v1\/bookings\/(\d+)$/.exec(url.pathname)
      if (detail) {
        const id = Number(detail[1])
        const base = items.find((i) => i.id === id) ?? ITEMS.find((i) => i.id === id)!
        // A full detail, as GET /bookings/{id} sends it.
        const extra = DETAILS[id] ?? {}
        const catering = extra.catering ? { delivery_date: base.first_session.date, delivery_time: '12:00', remarks: null, ...(extra.catering as object) } : null
        const it = extra.it ? { special_requirements: null, staff: [], status: 'RECEIVED', forwarded_at: null, assigned_at: null, ready_at: null, ...(extra.it as object) } : null
        return json({
          ...base,
          requester_info: { name_en: 'Sok Dara', division: 'Payments' },
          meeting_purpose: null,
          private_justification: null,
          participant_emails: [],
          sessions: [base.first_session],
          last_end: { date: base.first_session.date, time: base.first_session.end_time },
          reviews: [],
          rejection: null,
          cancelled_at: null,
          cancel_reason: null,
          cancelled_by: null,
          ...extra,
          catering,
          it,
        })
      }
      if (url.pathname === '/api/v1/rooms') return json({ items: ROOMS, page: 1, size: 100, total: ROOMS.length })
      return json({ items: [], page: 1, size: 100, total: 0 })
    }),
  )
})
afterEach(() => {
  vi.useRealTimers()
  vi.unstubAllGlobals()
})

async function mountReview(path = '/review') {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/review', name: 'review', component: ReviewView },
      { path: '/bookings', name: 'bookings', component: ReviewView },
    ],
  })
  await router.push(path)
  const wrapper = mount(ReviewView, { global: { plugins: [router] }, attachTo: document.body })
  await flushPromises()
  return { wrapper, router }
}

const row = (wrapper: Awaited<ReturnType<typeof mountReview>>['wrapper'], id: number) => wrapper.get(`[data-booking="${id}"]`)

describe('ReviewView', () => {
  it('asks for the bookings waiting for Pitika, all on one page', async () => {
    await mountReview()
    expect(calls).toContain('GET /api/v1/pitika/bookings?status=PENDING_PITIKA&page=1&size=100')
  })

  it('groups the queue by urgency, with counts, and counts what is waiting', async () => {
    const { wrapper } = await mountReview()

    const heads = wrapper.findAll('.group-head').map((h) => [h.get('h2').text(), h.get('.n').text()])
    expect(heads).toEqual([
      ['Today', '1'],
      ['Tomorrow', '1'],
      ['Later', '1'],
    ])
    expect(wrapper.get('.group-head.today').text()).toContain('Decide before they start, or they expire')
    expect(wrapper.get('[role="tab"]').text()).toBe('Waiting3')
  })

  it('shows the booking, its room, its time, and what to check in each row', async () => {
    const { wrapper } = await mountReview()

    const first = row(wrapper, 21).text()
    for (const text of ['Payment systems workshop', 'បន្ទប់មេគង្គ', 'Mekong Room', 'Sok Dara', '10 people']) {
      expect(first).toContain(text)
    }
    // The time leads the row; the reference sits on the photo; what to check is in soft tags.
    expect([row(wrapper, 21).get('.start').text(), row(wrapper, 21).get('.end').text()]).toEqual(['14:00', '15:30'])
    expect(row(wrapper, 21).get('.photo .ref').text()).toBe('NBC-26-87467')
    expect(row(wrapper, 21).findAll('.soft-tag').map((t) => t.text())).toEqual(['Food · Lunch box', 'IT · Projector setup'])
    expect(row(wrapper, 22).text()).toContain('Private · reason given')
  })

  it('marks only today’s booking with how soon it starts', async () => {
    const { wrapper } = await mountReview()

    expect(row(wrapper, 21).get('.soon').text()).toBe('Starts in 4 h 40 min')
    expect(wrapper.findAll('.soon')).toHaveLength(1)
  })

  it('says the step after the decision instead of a row bar', async () => {
    const { wrapper } = await mountReview()

    expect(row(wrapper, 22).get('.next').text()).toBe('Next: Room owner')
    expect(row(wrapper, 22).find('.process-bar').exists()).toBe(false)
  })

  it('shows the room photo, or a plain tile when the room has none', async () => {
    const { wrapper } = await mountReview()

    expect(row(wrapper, 21).get('.room-photo img').attributes('src')).toBe('http://localhost:8000/uploads/rooms/12/a_t.jpg')
    expect(row(wrapper, 22).get('.room-photo').classes()).toContain('none')
    expect(row(wrapper, 22).find('.room-photo img').exists()).toBe(false)
  })

  it('says when nothing is waiting (also a Pitika with no province)', async () => {
    items = []
    const { wrapper } = await mountReview()

    expect(wrapper.text()).toContain('Nothing to review')
    expect(wrapper.text()).toContain('New bookings in your province show here.')
    expect(wrapper.get('[role="tab"]').text()).toBe('Waiting0')
  })
})

describe('Review panel and decisions', () => {
  const dialog = () => document.body.querySelector('.action-dialog') as HTMLElement | null
  const panel = () => (document.body.querySelector('.review-panel')?.closest('[role="dialog"]') ?? null) as HTMLElement | null
  const button = (root: ParentNode | null, text: string) =>
    [...(root?.querySelectorAll<HTMLButtonElement>('button') ?? [])].find((b) => b.textContent?.trim() === text)
  async function click(el: HTMLElement | undefined) {
    el!.click()
    await flushPromises()
  }
  async function type(text: string) {
    const box = dialog()!.querySelector('textarea')!
    box.value = text
    box.dispatchEvent(new Event('input'))
    await flushPromises()
  }

  it('opens a booking with a small photo by the title, a thin step bar, a one-line warning, and what to check', async () => {
    const { wrapper } = await mountReview()
    await row(wrapper, 21).trigger('click')
    await flushPromises()

    const p = panel()!
    expect(p.querySelector('.panel-head .room-thumb img')?.getAttribute('src')).toBe('http://localhost:8000/uploads/rooms/12/a.jpg')
    expect(p.querySelector('.panel-cover')).toBeNull()
    expect(p.textContent).toContain('Payment systems workshop')
    expect(p.textContent).toContain('Waiting for Pitika')
    expect(p.querySelector('.step-progress .line span')?.textContent).toBe('Step 2 of 4')
    expect(p.querySelector('.step-progress .line b')?.textContent).toBe('Waiting for Pitika')
    expect(p.querySelectorAll('.step-progress .seg.done')).toHaveLength(1)
    expect(p.querySelector('.step-progress .seg.now')).not.toBeNull()
    const warn = p.querySelector('.warn')!
    expect(warn.textContent?.replace(/\s+/g, ' ').trim()).toBe('Starts in 4 h 40 min · decide before, or it is rejected')
    expect(warn.getAttribute('title')).toBe('If nobody decides before it starts, the system rejects it.')
    expect(p.textContent).toContain('Lunch box')
    expect(p.textContent).toContain('Projector setup')
  })

  it("shows the booker's staff ID, name, position and department", async () => {
    DETAILS[22] = {
      requester_info: { name_en: 'Sok Dara', name_kh: 'សុខ ដារា', staff_id: 'NBC0042', position: 'Officer', division: 'Payments', department: 'Operations' },
    }
    const { wrapper } = await mountReview()
    await row(wrapper, 22).trigger('click')
    await flushPromises()

    const rows = [...panel()!.querySelectorAll('.booker div')].map((d) => [d.querySelector('dt')?.textContent, d.querySelector('dd')?.textContent?.trim()])
    expect(rows).toEqual([
      ['Staff ID', 'NBC0042'],
      ['Name', 'Sok Dara សុខ ដារា'],
      ['Position', 'Officer'],
      ['Department', 'Operations Payments'],
    ])
    delete DETAILS[22]
  })

  describe('Tabs', () => {
    const tabs = () => [...panel()!.querySelectorAll('[role="tab"]')].map((t) => t.textContent?.trim())
    const shown = () => [...panel()!.querySelectorAll<HTMLElement>('[role="tabpanel"]')].filter((p) => p.style.display !== 'none').map((p) => p.id)

    it('splits the panel into Details, Food & IT with a count, and History; photo, steps and buttons stay', async () => {
      const { wrapper } = await mountReview()
      await row(wrapper, 21).trigger('click')
      await flushPromises()

      expect(tabs()).toEqual(['Details', 'Food & IT 2', 'History'])
      expect(shown()).toEqual(['tabpanel-details'])
      expect(panel()!.querySelector('.room-photo')).not.toBeNull()
      expect(panel()!.querySelector('.step-progress')).not.toBeNull()

      await click(panel()!.querySelector<HTMLButtonElement>('#tab-services')!)
      expect(shown()).toEqual(['tabpanel-services'])
      expect(panel()!.querySelector('#tab-services')!.getAttribute('aria-selected')).toBe('true')
      expect(button(panel(), 'Approve')).toBeTruthy()

      await click(panel()!.querySelector<HTMLButtonElement>('#tab-history')!)
      expect(panel()!.querySelector('#tabpanel-history')!.textContent).toContain('Waiting for Pitika')
    })

    it('shows Food & IT with the same cards as the booker: items with the amount, the booker’s notes', async () => {
      DETAILS[22] = {
        catering: { packages: [{ id: 1, name: 'Coffee break' }], remarks: 'Less sugar.', delivery_date: '2026-11-05', delivery_time: '14:00' },
        it: { items: [{ id: 2, name: 'Video call' }], special_requirements: 'Two microphones.', status: 'RECEIVED', staff: [] },
      }
      const { wrapper } = await mountReview()
      await row(wrapper, 22).trigger('click')
      await flushPromises()
      const food = panel()!.querySelector('#tabpanel-services .svc-card[data-kind="food"]')!
      expect([...food.querySelectorAll('.svc-items li')].map((li) => li.textContent?.replace(/\s+/g, ' ').trim())).toEqual(['Coffee break'])
      expect(food.textContent).toContain('Booker’s note')
      expect(food.textContent).toContain('“Less sugar.”')
      const it = panel()!.querySelector('#tabpanel-services .svc-card[data-kind="it"]')!
      expect([...it.querySelectorAll('.svc-items li')].map((li) => li.textContent?.trim())).toEqual(['Video call'])
      expect(it.textContent).toContain('“Two microphones.”')
      expect(food.classList).toContain('lead')
      expect(it.classList).not.toContain('lead')
      delete DETAILS[22]
    })

    it('adds a Files tab with a count only when the booking has files', async () => {
      DETAILS[22] = {
        attachments: [{ id: 4, file_name: 'agenda.pdf', content_type: 'application/pdf', size_bytes: 100, created_at: '2026-11-04T02:00:00Z', url: '/api/v1/bookings/22/attachments/4' }],
        reviews: [{ stage: 'PITIKA', decision: 'APPROVED', reviewer: { id: 3, name_en: 'Chan Sophea' }, notes: null, reviewed_at: '2026-11-12T07:05:00Z', by_admin: false }],
      }
      const { wrapper } = await mountReview()
      await row(wrapper, 22).trigger('click')
      await flushPromises()
      expect(tabs()).toEqual(['Details', 'Food & IT', 'Files 1', 'History'])
      delete DETAILS[22]
    })
  })

  describe('History', () => {
    const rows = () =>
      [...panel()!.querySelectorAll('#tabpanel-history .timeline li')].map((li) => ({
        label: li.querySelector('.label')?.textContent?.trim(),
        who: li.querySelector('.name')?.textContent?.trim() ?? null,
        role: [...li.querySelectorAll('.role')].map((r) => r.textContent?.trim()).join(' for '),
        at: li.querySelector('.time')?.textContent?.trim() ?? null,
        note: li.querySelector('.note')?.textContent?.trim() ?? null,
      }))
    async function openWith(extra: Record<string, unknown>) {
      DETAILS[22] = extra
      const { wrapper } = await mountReview()
      await row(wrapper, 22).trigger('click')
      await flushPromises()
    }
    afterEach(() => {
      delete DETAILS[22]
    })

    it('shows the timeline like the Admin’s History: who did what, their role, when, and the note', async () => {
      await openWith({
        status: 'PENDING_OWNER',
        reviews: [
          { stage: 'PITIKA', decision: 'APPROVED', reviewer: { id: 3, name_en: 'Chan Sophea' }, notes: 'Food is fine for 24 people.', reviewed_at: '2026-11-12T07:05:00Z', by_admin: false },
        ],
      })
      const r = rows()
      expect(r.map((x) => x.label)).toEqual(['Sent', 'Approved', 'Waiting for the room owner'])
      expect(r[0]).toMatchObject({ role: 'Booker' })
      expect(r[1]).toEqual({ label: 'Approved', who: 'Chan Sophea', role: 'Pitika', at: '12 Nov 2026, 14:05', note: 'Food is fine for 24 people.' })
      expect(r[2]).toMatchObject({ role: 'Room owner', at: null })
    })

    it('shows the Admin standing in, and a step that was not needed', async () => {
      await openWith({
        status: 'SETUP_IN_PROGRESS',
        reviews: [
          { stage: 'PITIKA', decision: 'APPROVED', reviewer: { id: 9, name_en: 'Pich Visal' }, notes: null, reviewed_at: '2026-11-14T01:15:00Z', by_admin: true },
          { stage: 'OWNER', decision: 'NOT_REQUIRED', reviewer: null, notes: null, reviewed_at: '2026-11-14T01:15:00Z', by_admin: false },
        ],
      })
      const r = rows()
      expect(r.find((x) => x.label === 'Approved')).toMatchObject({ who: 'Pich Visal', role: 'Admin for Pitika', at: '14 Nov 2026, 08:15' })
      expect(r.map((x) => x.label)).toContain('Room owner not needed')
    })

    it('has no second step bar inside the tab: the one on top is enough', async () => {
      await openWith({ reviews: [] })
      expect(panel()!.querySelector('#tabpanel-history .timeline')).not.toBeNull()
      expect(panel()!.querySelector('#tabpanel-history .steps')).toBeNull()
    })
  })

  it('says None for booker details the booking does not have', async () => {
    const { wrapper } = await mountReview()
    await row(wrapper, 22).trigger('click')
    await flushPromises()

    const values = [...panel()!.querySelectorAll('.booker dd')].map((d) => d.textContent?.trim())
    expect(values).toEqual(['None', 'Sok Dara', 'None', 'Payments'])
  })

  it('lists every session in the panel, and says the food comes at each of them', async () => {
    const { wrapper } = await mountReview()
    await row(wrapper, 21).trigger('click')
    await flushPromises()

    const p = panel()!
    const sessions = [...p.querySelectorAll('.sessions li')].map((li) => [...li.children].map((c) => c.textContent).join(' '))
    expect(sessions).toEqual(['Thu 5 Nov 2026 14:00–15:30', 'Fri 6 Nov 2026 09:00–10:30', 'Sat 7 Nov 2026 09:00–10:30'])
    expect(p.querySelector('.sessions-head')?.textContent).toContain('3 sessions')
    expect(p.querySelector('.delivery')?.textContent?.trim()).toBe('The start of every session (3 times)')
    const facts = [...p.querySelectorAll('#tabpanel-details .details dt')].map((d) => d.textContent?.trim())
    expect(facts).toEqual(['Room', 'Where', 'Office', 'Seats', 'Meeting type', 'Attendees', 'Purpose', 'Route', 'Invited', 'Sent', 'Staff ID', 'Name', 'Position', 'Department'])
  })

  it('tells the Pitika on an owner’s own room that only the food and IT are theirs to check', async () => {
    items = [listItem(23, { ...ITEMS[2], route: 'R4' })]
    const { wrapper } = await mountReview()
    await row(wrapper, 23).trigger('click')
    await flushPromises()

    expect(panel()!.textContent).toContain('The owner books their own room: you check the food and IT only.')
  })

  it('lists the booking files read only, and downloads one', async () => {
    DETAILS[21] = {
      ...DETAILS[21],
      attachments: [{ id: 4, file_name: 'guest-list.xlsx', content_type: 'x', size_bytes: 4096, created_at: '2026-11-04T02:00:00Z', url: '/api/v1/bookings/21/attachments/4' }],
    }
    URL.createObjectURL = vi.fn<typeof URL.createObjectURL>(() => 'blob:1')
    URL.revokeObjectURL = vi.fn<typeof URL.revokeObjectURL>()
    const clickSpy = vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => undefined)
    const { wrapper } = await mountReview()
    await row(wrapper, 21).trigger('click')
    await flushPromises()

    const name = panel()!.querySelector<HTMLButtonElement>('.att-name')!
    expect(name.textContent).toBe('guest-list.xlsx')
    expect(panel()!.textContent).not.toContain('Add file')
    name.click()
    await flushPromises()
    expect(calls).toContain('GET /api/v1/bookings/21/attachments/4')
    await new Promise((done) => setTimeout(done, 0)) // the download frees its URL on a timer
    clickSpy.mockRestore()
    delete DETAILS[21]!.attachments
  })

  it('approves from the row with optional notes, then the row leaves', async () => {
    const { wrapper } = await mountReview()
    await click(button(row(wrapper, 21).element, 'Approve'))

    expect(dialog()?.textContent).toContain('Approve this booking?')
    expect(dialog()?.textContent).toContain('It goes to IT setup next. The food is approved with it.')
    await click(dialog()!.querySelector<HTMLElement>('button.confirm')!)

    expect(calls).toContain('POST /api/v1/pitika/bookings/21/approve')
    expect(bodies).toEqual([JSON.stringify({ notes: null, version: 1 })])
    expect(useToast().toasts.value.map((t) => t.title)).toContain('NBC-26-87467 approved')
    expect(wrapper.find('[data-booking="21"]').exists()).toBe(false)
    expect(dialog()).toBeNull()
  })

  it('needs a reason of at least 5 characters to reject', async () => {
    decision = () => json({ ...ITEMS[1], status: 'REJECTED' })
    const { wrapper } = await mountReview()
    await click(button(row(wrapper, 22).element, 'Reject'))

    const confirm = () => dialog()!.querySelector<HTMLButtonElement>('button.confirm')!
    expect(dialog()?.textContent).toContain('The booking stops and the room is free again. The booker sees your reason.')
    expect(confirm().disabled).toBe(true)
    expect(dialog()?.textContent).toContain('At least 5 characters.')
    await type('Room')
    expect(confirm().disabled).toBe(true)
    await type('Room closed')
    expect(confirm().disabled).toBe(false)
    expect(dialog()?.textContent).not.toContain('At least 5 characters.')
    await click(confirm())

    expect(bodies).toEqual([JSON.stringify({ reason: 'Room closed', version: 1 })])
    expect(useToast().toasts.value.map((t) => t.title)).toContain('NBC-26-55102 rejected')
  })

  it('shows a refusal in the pop-up and reloads the queue', async () => {
    decision = () => json({ error: { code: 'INVALID_TRANSITION', message: 'This booking is not waiting for Pitika.', fields: {} } }, 409)
    const { wrapper } = await mountReview()
    const lists = () => calls.filter((c) => c.startsWith('GET /api/v1/pitika/bookings?')).length
    const before = lists()
    await click(button(row(wrapper, 21).element, 'Approve'))
    await click(dialog()!.querySelector<HTMLElement>('button.confirm')!)

    expect(dialog()?.textContent).toContain('This booking is not waiting for Pitika.')
    expect(lists()).toBe(before + 1)
  })

  it('says when the meeting already started and cannot be approved', async () => {
    decision = () => json({ error: { code: 'TIME_PASSED', message: 'The meeting has started. It cannot be approved.', fields: {} } }, 409)
    const { wrapper } = await mountReview()
    await click(button(row(wrapper, 21).element, 'Approve'))
    await click(dialog()!.querySelector<HTMLElement>('button.confirm')!)

    expect(dialog()?.textContent).toContain('The meeting has started. It cannot be approved.')
  })

  it('decides from the panel too, and closes it', async () => {
    const { wrapper, router } = await mountReview()
    await row(wrapper, 21).trigger('click')
    await flushPromises()
    await click(button(panel(), 'Approve'))
    await click(dialog()!.querySelector<HTMLElement>('button.confirm')!)

    expect(bodies).toHaveLength(1)
    expect(router.currentRoute.value.query.id).toBeUndefined()
  })
})

describe('To review filters', () => {
  const lists = () => calls.filter((c) => c.startsWith('GET /api/v1/pitika/bookings?'))

  it('says what today looks like in one short line', async () => {
    const { wrapper } = await mountReview()
    expect(wrapper.get('.sub').text()).toBe('Today you decided 6 · 3 still waiting')
    expect(wrapper.find('.page-head .count').exists()).toBe(false)
  })

  it('filters by a room of the Pitika province only', async () => {
    await mountReview()

    expect(await pickerOptions('filter-room')).toEqual(['All rooms', 'Mekong Room', 'Governor Room'])
    await choosePicker('filter-room', 'Mekong Room')
    expect(lists().at(-1)).toBe('GET /api/v1/pitika/bookings?status=PENDING_PITIKA&room_id=12&page=1&size=100')
  })

  it('lets you search the rooms, however few there are', async () => {
    await mountReview()
    const searchBoxes = () => document.querySelectorAll('input[type="search"]').length
    const before = searchBoxes()
    document.querySelector<HTMLButtonElement>('#filter-room')!.click()
    await flushPromises()

    expect(searchBoxes()).toBe(before + 1)
  })

  it('filters by a day range, and Clear filters empties every filter', async () => {
    const { wrapper } = await mountReview()
    expect(wrapper.find('.clear-filters').exists()).toBe(false)

    await pickDate('filter-from', '2026-11-06')
    await pickDate('filter-to', '2026-11-12')
    expect(lists().at(-1)).toBe('GET /api/v1/pitika/bookings?status=PENDING_PITIKA&from=2026-11-06&to=2026-11-12&page=1&size=100')

    await clearDate('filter-to')
    expect(lists().at(-1)).toBe('GET /api/v1/pitika/bookings?status=PENDING_PITIKA&from=2026-11-06&page=1&size=100')

    await wrapper.get('.clear-filters').trigger('click')
    await flushPromises()
    expect(lists().at(-1)).toBe('GET /api/v1/pitika/bookings?status=PENDING_PITIKA&page=1&size=100')
  })
})

describe('To review tabs', () => {
  const summaries = () => calls.filter((c) => c === 'GET /api/v1/pitika/bookings/summary')

  it('loads today’s summary once on open, and again after a decision', async () => {
    const { wrapper } = await mountReview()
    expect(summaries()).toHaveLength(1)

    ;[...row(wrapper, 21).element.querySelectorAll<HTMLButtonElement>('button')].find((b) => b.textContent?.trim() === 'Approve')!.click()
    await flushPromises()
    document.body.querySelector<HTMLElement>('.action-dialog button.confirm')!.click()
    await flushPromises()

    expect(summaries()).toHaveLength(2)
  })

  it('switching tab keeps the filters and drops the page and the open booking', async () => {
    const { wrapper, router } = await mountReview('/review?page=3&id=21&q=board')

    await wrapper.findAll('[role="tab"]')[1]!.trigger('click')
    await flushPromises()
    expect(router.currentRoute.value.fullPath).toBe('/review?q=board&tab=approved')

    await wrapper.findAll('[role="tab"]')[0]!.trigger('click')
    await flushPromises()
    expect(router.currentRoute.value.fullPath).toBe('/review?q=board')
  })

  it('does not show the approved cards as rejections while the Rejected tab loads', async () => {
    decidedItems = [{ ...listItem(51, { display_status: 'CONFIRMED' }), decided_at: '2026-11-05T02:00:00Z', decision_note: 'Fine' }]
    holdRejected = true
    const { wrapper } = await mountReview('/review?tab=approved')
    expect(wrapper.find('[data-booking="51"] .mark.ok').exists()).toBe(true)

    await wrapper.findAll('[role="tab"]')[2]!.trigger('click')
    await flushPromises()

    expect(wrapper.find('[data-booking="51"]').exists()).toBe(false)
    expect(wrapper.text()).not.toContain('Reason: “Fine”')
  })

  it('turning a page on the Approved tab does not reload the waiting list', async () => {
    const { router } = await mountReview('/review?tab=approved')
    const waitingCalls = () => calls.filter((c) => c.startsWith('GET /api/v1/pitika/bookings?')).length
    const before = waitingCalls()

    await router.replace('/review?tab=approved&page=2')
    await flushPromises()

    expect(waitingCalls()).toBe(before)
  })

  it('shows the decided list, not the queue, on the Approved tab, with the filters kept', async () => {
    const { wrapper } = await mountReview('/review?tab=approved')

    expect(wrapper.find('.queue').exists()).toBe(false)
    expect(wrapper.find('.filters').exists()).toBe(true)
    expect(wrapper.findAll('[role="tab"]')[1]!.attributes('aria-selected')).toBe('true')
  })
})
