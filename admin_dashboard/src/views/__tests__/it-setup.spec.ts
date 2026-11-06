import { enableAutoUnmount, flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createMemoryHistory, createRouter } from 'vue-router'

import { useToast } from '../../composables/useToast'
import { useSessionStore } from '../../stores/session'
import { listItem } from '../../test-utils/bookings'
import ITSetupView from '../ITSetupView.vue'

enableAutoUnmount(afterEach)

// Now: Thu 5 Nov 2026, 06:00 in Phnom Penh.
const PP = { code: 'PHNOM_PENH', name_en: 'Phnom Penh', name_kh: 'ភ្នំពេញ' }
const ROOMS = [
  {
    ...listItem(1).room,
    id: 12,
    capacity: 40,
    location: { id: 3, name_en: 'Head Office', name_kh: 'x' },
    building: { id: 2, name_en: 'Building A', name_kh: 'x' },
    floor: { id: 4, floor_label: 'Floor 2' },
    cover_photo: null,
    province: PP,
  },
]
const STAFF = [
  { id: 31, name_en: 'Chan Bopha', name_kh: 'x', is_active: true, avatar_url: null },
  { id: 32, name_en: 'Sok Pisey', name_kh: 'x', is_active: true, avatar_url: null },
]
// The picker's answer: how many setups each one already has on the asked day.
const LOAD = [0, 2]
const ticket = (id: number, setup_date: string, changes: Record<string, unknown> = {}) => ({
  id,
  status: 'RECEIVED',
  items: [
    { id: 1, name: 'Projector setup' },
    { id: 2, name: 'Microphones' },
  ],
  special_requirements: 'Two wireless microphones',
  technician_notes: null,
  staff: [],
  setup_date,
  setup_time: '07:30',
  forwarded_at: '2026-11-04T02:00:00Z',
  assigned_at: null,
  ready_at: null,
  missed: false,
  review_notes: [],
  booking: listItem(100 + id, {
    reference_code: `NBC-26-1000${id}`,
    meeting_title: `Training ${id}`,
    status: 'SETUP_IN_PROGRESS',
    display_status: 'SETUP_IN_PROGRESS',
    first_session: { id: 1, date: setup_date, start_time: '08:00', end_time: '11:00' },
    has_it: true,
  }),
  ...changes,
})
const TO_ASSIGN = [ticket(5, '2026-11-05'), ticket(6, '2026-11-06')]
const IN_PROGRESS = [ticket(7, '2026-11-06', { status: 'ASSIGNED', staff: [STAFF[1]] })]
const DONE = [
  ticket(8, '2026-11-05', { status: 'READY', staff: [STAFF[0]], ready_at: '2026-11-05T01:00:00Z' }),
  ticket(9, '2026-11-04', { missed: true, status: 'ASSIGNED', staff: [STAFF[0]] }),
]
const SUMMARY = { to_assign: 2, in_progress: 1, ready_today: 1, due_today: 6, due_today_ready: 4 }

const calls: string[] = []
const bodies: string[] = []
let summary: Record<string, number>
let action: () => Response

function json(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } })
}

beforeEach(() => {
  vi.useFakeTimers({ toFake: ['Date'] })
  vi.setSystemTime(new Date('2026-11-04T23:00:00Z'))
  setActivePinia(createPinia())
  useSessionStore().accessToken = 'A1'
  useSessionStore().user = { id: 40, roles: [{ code: 'IT_LEAD' }], province: PP } as never
  localStorage.clear()
  calls.length = 0
  bodies.length = 0
  summary = SUMMARY
  action = () => json(TO_ASSIGN[0])
  vi.stubGlobal(
    'fetch',
    vi.fn<typeof fetch>(async (input, init) => {
      const url = new URL(String(input))
      calls.push(`${init?.method ?? 'GET'} ${url.pathname}${url.search}`)
      if (/^\/api\/v1\/it\/tickets\/\d+\/(staff|ready)$/.test(url.pathname)) {
        bodies.push(String(init?.body))
        return action()
      }
      if (url.pathname === '/api/v1/it/tickets') {
        const state = url.searchParams.get('state')
        const items = state === 'in_progress' ? IN_PROGRESS : state === 'done' ? DONE : TO_ASSIGN
        return json({ items, page: 1, size: Number(url.searchParams.get('size')), total: items.length })
      }
      if (url.pathname === '/api/v1/it/tickets/summary') return json(summary)
      if (url.pathname === '/api/v1/it/staff') {
        const day = url.searchParams.get('day')
        return json({ items: STAFF.map((x, i) => ({ ...x, setups_that_day: day ? LOAD[i] : null })), total: STAFF.length })
      }
      if (url.pathname === '/api/v1/rooms') return json({ items: ROOMS, page: 1, size: 100, total: 1 })
      const one = /^\/api\/v1\/bookings\/(\d+)$/.exec(url.pathname)
      if (one) {
        const t = [...TO_ASSIGN, ...IN_PROGRESS, ...DONE].find((x) => x.booking.id === Number(one[1]))!
        return json({
          ...t.booking,
          requester_info: { name_en: 'Sok Dara', division: 'Payments' },
          meeting_purpose: null,
          private_justification: null,
          participant_emails: [],
          sessions: [t.booking.first_session],
          last_end: { date: t.booking.first_session.date, time: '11:00' },
          catering: null,
          it: { items: t.items, special_requirements: t.special_requirements, status: t.status, staff: t.staff, forwarded_at: t.forwarded_at, assigned_at: null, ready_at: null },
          reviews: [],
          rejection: null,
          cancelled_at: null,
          cancel_reason: null,
          cancelled_by: null,
        })
      }
      return json({ items: [], page: 1, size: 100, total: 0 })
    }),
  )
})
afterEach(() => {
  vi.useRealTimers()
  vi.unstubAllGlobals()
})

async function mountAt(path = '/it-setup') {
  const router = createRouter({ history: createMemoryHistory(), routes: [{ path: '/it-setup', name: 'it-setup', component: ITSetupView }] })
  await router.push(path)
  const wrapper = mount(ITSetupView, { global: { plugins: [router] }, attachTo: document.body })
  await flushPromises()
  return { wrapper, router }
}
const row = (wrapper: Awaited<ReturnType<typeof mountAt>>['wrapper'], id: number) => wrapper.get(`[data-ticket="${id}"]`)
const buttons = (root: { findAll: (s: string) => Array<{ text: () => string }> }) => root.findAll('button').map((b) => b.text())
const dialog = () => document.body.querySelector('.action-dialog') as HTMLElement | null
const panel = () => document.body.querySelector('.it-panel')?.closest('[role="dialog"]') as HTMLElement | null

describe('IT setup', () => {
  it('shows the day in the head: ring, line and the three tabs', async () => {
    const { wrapper } = await mountAt()
    expect(wrapper.get('h1').text()).toBe('IT setup')
    expect(wrapper.get('.today-ring').text()).toBe('4/6')
    expect(wrapper.get('.sub').text()).toBe('Today 4 of 6 setups ready · 2 to assign')
    expect(wrapper.findAll('[role="tab"]').map((t) => t.text())).toEqual(['To assign2', 'In progress1', 'Ready1'])
  })

  it('shows 0/0 light when nothing is due today', async () => {
    summary = { to_assign: 2, in_progress: 0, ready_today: 0, due_today: 0, due_today_ready: 0 }
    const { wrapper } = await mountAt()
    expect(wrapper.get('.today-ring').classes()).toContain('empty')
    expect(wrapper.get('.sub').text()).toBe('No setups today · 2 to assign')
  })

  it('lists To assign on one page, grouped by setup day', async () => {
    const { wrapper } = await mountAt()
    expect(calls).toContain('GET /api/v1/it/tickets?state=to_assign&page=1&size=100')
    expect(wrapper.findAll('.group-head h2').map((h) => h.text())).toEqual(['Today', 'Tomorrow'])
  })

  it('shows what to set up, where and when, and Assign staff', async () => {
    const { wrapper } = await mountAt()
    const r = row(wrapper, 5)
    expect(r.text()).toContain('Training 5')
    expect(r.get('.place').text()).toBe('Head Office · Building A · Floor 2')
    expect(r.get('.time').text()).toBe('07:30')
    expect(r.get('.time-label').text()).toBe('Set up by')
    expect(r.findAll('.chk').map((c) => c.text())).toEqual(['Projector setup', 'Microphones'])
    expect(r.get('.note').attributes('title')).toBe('Two wireless microphones')
    expect(r.get('.state-word').text()).toBe('Needs staff')
    expect(r.get('.staff').text()).toBe('No staff yet')
    expect(r.get('.soon').text()).toContain('Starts in')
    expect(buttons(r)).toEqual(['Assign staff'])
    expect(row(wrapper, 6).find('.soon').exists()).toBe(false)
  })

  it('shows Change staff and Mark ready In progress', async () => {
    const { wrapper } = await mountAt('/it-setup?tab=in_progress')
    expect(calls).toContain('GET /api/v1/it/tickets?state=in_progress&page=1&size=100')
    expect(row(wrapper, 7).get('.staff').text()).toBe('Sok Pisey')
    expect(row(wrapper, 7).get('.state-word').text()).toBe('Staff set · not ready')
    expect(buttons(row(wrapper, 7))).toEqual(['Change', 'Mark ready'])
  })

  it('shows Ready 20 a page, newest first, with missed ones and no buttons', async () => {
    const { wrapper } = await mountAt('/it-setup?tab=ready')
    expect(calls).toContain('GET /api/v1/it/tickets?state=done&page=1&size=20')
    expect(wrapper.findAll('.group-head h2').map((h) => h.text())).toEqual(['Today · Thu 5 Nov', 'Yesterday · Wed 4 Nov'])
    expect(row(wrapper, 9).get('.state-word').text()).toBe('Missed · not marked ready')
    expect(row(wrapper, 8).get('.state-word').text()).toBe('Ready · 08:00')
    expect(buttons(row(wrapper, 8))).toEqual([])
    expect(buttons(row(wrapper, 9))).toEqual([])
  })

  it('assigns staff in the pop-up, with the current staff checked', async () => {
    const { wrapper } = await mountAt('/it-setup?tab=in_progress')
    await row(wrapper, 7).findAll('button').find((b) => b.text() === 'Change')!.trigger('click')
    await flushPromises()

    expect(dialog()?.textContent).toContain('Assign IT Staff')
    const boxes = [...dialog()!.querySelectorAll<HTMLInputElement>('input[type="checkbox"]')]
    expect(boxes.map((b) => b.checked)).toEqual([false, true])
    boxes[0]!.click()
    await flushPromises()
    dialog()!.querySelector<HTMLElement>('button.confirm')!.click()
    await flushPromises()

    expect(calls).toContain('PUT /api/v1/it/tickets/7/staff')
    expect(bodies).toEqual([JSON.stringify({ user_ids: [31, 32], technician_notes: null, version: 1 })])
    expect(useToast().toasts.value.map((t) => t.title)).toContain('NBC-26-10007 staff assigned')
  })

  it('keeps Save off until someone is checked', async () => {
    const { wrapper } = await mountAt()
    await row(wrapper, 5).findAll('button').find((b) => b.text() === 'Assign staff')!.trigger('click')
    await flushPromises()
    expect(dialog()!.querySelector<HTMLButtonElement>('button.confirm')!.disabled).toBe(true)
  })

  it('shows a refusal in the pop-up and reloads', async () => {
    action = () => json({ error: { code: 'INACTIVE_REFERENCE', message: 'This user is not active IT Staff.', fields: {} } }, 409)
    const { wrapper } = await mountAt()
    const before = calls.filter((c) => c.startsWith('GET /api/v1/it/tickets?')).length
    await row(wrapper, 5).findAll('button').find((b) => b.text() === 'Assign staff')!.trigger('click')
    await flushPromises()
    dialog()!.querySelector<HTMLInputElement>('input[type="checkbox"]')!.click()
    await flushPromises()
    dialog()!.querySelector<HTMLElement>('button.confirm')!.click()
    await flushPromises()

    expect(dialog()?.textContent).toContain('This user is not active IT Staff.')
    expect(calls.filter((c) => c.startsWith('GET /api/v1/it/tickets?')).length).toBe(before + 1)
  })

  it('marks ready after a confirm with no text box', async () => {
    const { wrapper } = await mountAt('/it-setup?tab=in_progress')
    await row(wrapper, 7).findAll('button').find((b) => b.text() === 'Mark ready')!.trigger('click')
    await flushPromises()

    expect(dialog()?.textContent).toContain('Mark this setup ready?')
    expect(dialog()?.textContent).toContain('The booking is confirmed and the booker gets the door pass.')
    expect(dialog()!.querySelector('textarea')).toBeNull()
    dialog()!.querySelector<HTMLElement>('button.confirm')!.click()
    await flushPromises()

    expect(calls).toContain('POST /api/v1/it/tickets/7/ready')
    expect(bodies).toEqual([JSON.stringify({ version: 1 })])
  })

  it('opens a setup in the panel with Setup and Meeting, and the row buttons', async () => {
    const { wrapper } = await mountAt('/it-setup?tab=in_progress')
    await row(wrapper, 7).trigger('click')
    await flushPromises()

    expect(calls).toContain('GET /api/v1/bookings/107')
    expect(panel()?.textContent).toContain('Setup')
    expect(panel()?.textContent).toContain('Two wireless microphones')
    expect(panel()?.textContent).toContain('Meeting')
    const foot = [...(panel()?.querySelectorAll('.panel-foot button') ?? [])].map((b) => b.textContent?.trim())
    expect(foot).toEqual(['Close', 'Change staff', 'Mark ready'])
  })

  it('marks each row with a state stripe: needs staff, staff set, ready, missed', async () => {
    const { wrapper } = await mountAt()
    expect(wrapper.find('.timeline').exists()).toBe(true)
    expect(row(wrapper, 5).classes()).toContain('state-waiting')
    const progress = await mountAt('/it-setup?tab=in_progress')
    expect(row(progress.wrapper, 7).classes()).toContain('state-staffed')
    const done = await mountAt('/it-setup?tab=ready')
    expect(row(done.wrapper, 8).classes()).toContain('state-ready')
    expect(row(done.wrapper, 9).classes()).toContain('state-missed')
  })

  it('switches to cards and remembers the choice in this browser', async () => {
    const { wrapper } = await mountAt()
    const cardsButton = wrapper.findAll('.view-switch button').find((b) => b.text() === 'Cards')!
    expect(cardsButton.attributes('aria-pressed')).toBe('false')
    await cardsButton.trigger('click')
    await flushPromises()

    expect(wrapper.find('.timeline').exists()).toBe(false)
    expect(wrapper.findAll('.cards [data-ticket]').length).toBe(2)
    expect(localStorage.getItem('nbc.admin.itView')).toBe('cards')
    const again = await mountAt()
    expect(again.wrapper.find('.cards').exists()).toBe(true)
  })

  it('shows a card with the setup day and time on the photo, the needs as icons, and the buttons', async () => {
    localStorage.setItem('nbc.admin.itView', 'cards')
    const { wrapper } = await mountAt()
    const card = row(wrapper, 5)
    expect(card.get('.when').text()).toBe('Today · by 07:30')
    expect(card.get('.soon').text()).toContain('Starts in')
    expect(card.findAll('.need').map((n) => n.attributes('aria-label'))).toEqual(['Projector setup', 'Microphones', 'Note: Two wireless microphones'])
    expect(card.get('.staff').text()).toBe('No staff yet')
    expect(buttons(card)).toEqual(['Assign staff'])
    expect(row(wrapper, 6).get('.when').text()).toBe('Fri 6 Nov · by 07:30')
  })

  it("asks for the staff with the setup day and shows each one's other setups that day", async () => {
    const { wrapper } = await mountAt('/it-setup?tab=in_progress')
    await row(wrapper, 7).findAll('button').find((b) => b.text() === 'Change')!.trigger('click')
    await flushPromises()

    expect(calls).toContain('GET /api/v1/it/staff?day=2026-11-06')
    const load = [...dialog()!.querySelectorAll('.staff-row .load')].map((n) => n.textContent?.trim())
    // Sok Pisey has 2 that day, and one of them is this setup.
    expect(load).toEqual(['Free that day', '1 other setup that day'])
    expect(dialog()!.querySelector('.room-box')?.textContent).toContain('Training 7')
    expect(dialog()!.querySelector('.picked')?.textContent?.trim()).toBe('1 picked')
    expect(dialog()!.querySelector('button.confirm')?.textContent?.trim()).toBe('Assign 1 staff')
  })

  it('hides the note box until asked', async () => {
    const { wrapper } = await mountAt()
    await row(wrapper, 5).findAll('button').find((b) => b.text() === 'Assign staff')!.trigger('click')
    await flushPromises()
    expect(dialog()!.querySelector('textarea')).toBeNull()
    expect(dialog()!.querySelector('button.confirm')?.textContent?.trim()).toBe('Assign staff')
    dialog()!.querySelector<HTMLElement>('button.add-note')!.click()
    await flushPromises()
    expect(dialog()!.querySelector('textarea')).not.toBeNull()
  })
})
