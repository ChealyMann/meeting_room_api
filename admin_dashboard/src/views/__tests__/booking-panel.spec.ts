import { enableAutoUnmount, flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createMemoryHistory, createRouter, type Router } from 'vue-router'

import { useSessionStore } from '../../stores/session'
import { listItem } from '../../test-utils/bookings'
import BookingsView from '../BookingsView.vue'

enableAutoUnmount(afterEach)

const session = (id: number, date: string) => ({ id, date, start_time: '09:00', end_time: '10:30' })

const detail = (changes: Record<string, unknown> = {}) => ({
  ...listItem(12, { status: 'CONFIRMED', display_status: 'CONFIRMED', route: 'R2' }),
  requester_info: {
    name_en: 'Sok Dara',
    name_kh: 'សុខ ដារា',
    staff_id: 'NBC0042',
    position: 'Officer',
    division: 'Payments',
    department: 'Operations',
    office: 'Head Office',
    email: 'dara@nbc.gov.kh',
    phone: null,
  },
  meeting_purpose: 'Plan the 2027 budget',
  private_justification: 'Board members attend',
  participant_emails: ['a@nbc.gov.kh'],
  sessions: [session(1, '2026-11-10'), session(2, '2026-11-11'), session(3, '2026-11-12')],
  last_end: { date: '2026-11-12', time: '10:30' },
  catering: null,
  it: null,
  reviews: [
    { stage: 'PITIKA', decision: 'APPROVED', reviewer: { id: 9, name_en: 'Chan Pitika' }, notes: 'Fine', reviewed_at: '2026-11-04T02:00:00Z' },
  ],
  rejection: null,
  cancelled_at: null,
  cancel_reason: null,
  updated_at: '2026-11-04T02:00:00Z',
  ...changes,
})

const calls: string[] = []
let current: ReturnType<typeof detail>
let doorPass: Record<string, unknown>

function json(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } })
}

beforeEach(() => {
  setActivePinia(createPinia())
  useSessionStore().accessToken = 'A1'
  calls.length = 0
  current = detail()
  doorPass = { passcode: 'NBC-48213', expires_at: '2026-11-12T03:30:00Z', expired: false }
  URL.createObjectURL = vi.fn<typeof URL.createObjectURL>(() => 'blob:1')
  URL.revokeObjectURL = vi.fn<typeof URL.revokeObjectURL>()
  vi.stubGlobal(
    'fetch',
    vi.fn<typeof fetch>(async (input, init) => {
      const url = new URL(String(input))
      calls.push(`${init?.method ?? 'GET'} ${url.pathname}`)
      if (url.pathname === '/api/v1/bookings/12/door-pass') return json(doorPass)
      if (url.pathname === '/api/v1/bookings/12/ics') return new Response('BEGIN:VCALENDAR', { headers: { 'Content-Type': 'text/calendar' } })
      if (url.pathname === '/api/v1/bookings/12') return json(current)
      if (url.pathname === '/api/v1/bookings') return json({ items: [listItem(12)], page: 1, size: 20, total: 1 })
      return json({ items: [], page: 1, size: 100, total: 0 })
    }),
  )
})
afterEach(() => vi.unstubAllGlobals())

async function mountAt(path: string) {
  const router: Router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/bookings', name: 'bookings', component: BookingsView },
      { path: '/', name: 'home', component: BookingsView },
    ],
  })
  await router.push(path)
  const wrapper = mount(BookingsView, { global: { plugins: [router] }, attachTo: document.body })
  await flushPromises()
  return { wrapper, router }
}

const panel = () => document.body.querySelector('[role="dialog"]') as HTMLElement | null
const panelButton = (text: string) => [...(panel()?.querySelectorAll('button') ?? [])].find((b) => b.textContent?.trim() === text)
async function click(el: HTMLElement | undefined) {
  el!.click()
  await flushPromises()
}

describe('BookingPanel', () => {
  it('opens the booking from the address', async () => {
    await mountAt('/bookings?id=12')

    expect(calls).toContain('GET /api/v1/bookings/12')
    expect(panel()?.textContent).toContain('Budget review')
    expect(panel()?.textContent).toContain('NBC-26-48213')
    expect(panel()?.textContent).toContain('Private room, owner approves')
    expect(panel()?.textContent).toContain('NBC0042')
  })

  it('lists every session', async () => {
    await mountAt('/bookings?id=12')

    await click(panel()!.querySelector<HTMLElement>('#tab-sessions')!)

    expect(panel()!.querySelectorAll('#tabpanel-sessions li')).toHaveLength(3)
    expect(panel()!.querySelector('#tabpanel-sessions')!.textContent).toContain('Ends Thu 12 Nov 2026 10:30')
  })

  it('says when no food or IT help was asked', async () => {
    await mountAt('/bookings?id=12')

    const services = panel()!.querySelector('#tabpanel-services')!.textContent
    expect(services).toContain('No food ordered.')
    expect(services).toContain('No IT help asked.')
  })

  it('shows the reviews and the rejection in History', async () => {
    current = detail({
      status: 'REJECTED',
      display_status: 'REJECTED',
      rejection: { rejected_by: 'OWNER', actor: { id: 5, name_en: 'Keo Owner' }, reason: 'Room is closed that day.', decided_at: '2026-11-04T03:00:00Z' },
    })
    await mountAt('/bookings?id=12')

    const history = panel()!.querySelector('#tabpanel-history')!.textContent
    expect(history).toContain('Pitika approved')
    expect(history).toContain('Chan Pitika')
    expect(history).toContain('Rejected by the room owner')
    expect(history).toContain('Room is closed that day.')
  })

  it('shows the door pass only when asked', async () => {
    await mountAt('/bookings?id=12')
    expect(panel()?.textContent).not.toContain('NBC-48213')
    expect(calls).not.toContain('GET /api/v1/bookings/12/door-pass')

    await click(panelButton('Show door pass'))

    expect(calls).toContain('GET /api/v1/bookings/12/door-pass')
    expect(panel()?.querySelector('.door-pass')?.textContent).toContain('NBC-48213')
    expect(panel()?.querySelector('.door-pass')?.textContent).not.toContain('Expired')
  })

  it('marks an expired door pass', async () => {
    doorPass = { ...doorPass, expired: true }
    await mountAt('/bookings?id=12')

    await click(panelButton('Show door pass'))

    expect(panel()?.querySelector('.door-pass')?.textContent).toContain('Expired')
  })

  it('has no door pass button before the booking is confirmed', async () => {
    current = detail({ status: 'PENDING_PITIKA', display_status: 'PENDING_PITIKA' })
    await mountAt('/bookings?id=12')

    expect(panelButton('Show door pass')).toBeUndefined()
  })

  it('downloads the calendar file', async () => {
    await mountAt('/bookings?id=12')

    await click(panelButton('Calendar file'))

    expect(calls).toContain('GET /api/v1/bookings/12/ics')
    expect(URL.createObjectURL).toHaveBeenCalled()
  })

  it('is read only', async () => {
    await mountAt('/bookings?id=12')

    const labels = [...panel()!.querySelectorAll('button')].map((b) => b.textContent?.trim())
    for (const word of ['Save changes', 'Approve', 'Reject', 'Cancel booking', 'Edit']) {
      expect(labels).not.toContain(word)
    }
  })
})
