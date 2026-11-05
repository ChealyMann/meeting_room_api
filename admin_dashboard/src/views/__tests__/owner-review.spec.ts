import { enableAutoUnmount, flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createMemoryHistory, createRouter } from 'vue-router'

import { useToast } from '../../composables/useToast'
import { useSessionStore } from '../../stores/session'
import { listItem } from '../../test-utils/bookings'
import { pickerOptions } from '../../test-utils/picker'
import ReviewView from '../ReviewView.vue'

enableAutoUnmount(afterEach)

// Now: Thu 5 Nov 2026, 09:20 in Phnom Penh. I am user 7, the owner of rooms 13 and 14.
const PP = { code: 'PHNOM_PENH', name_en: 'Phnom Penh', name_kh: 'ភ្នំពេញ' }
const ME = { id: 7, name_en: 'Keo Vanna', name_kh: 'កែវ វណ្ណា' }
const room = (id: number, name_en: string, capacity: number, owner: typeof ME | null, is_private = true) => ({
  ...listItem(1).room,
  id,
  name_en,
  name_kh: `${name_en} KH`,
  capacity,
  owner,
  is_private,
  province: PP,
  location: { name_en: 'Head Office' },
  cover_photo: null,
})
const ROOMS = [
  room(13, 'Governor Room', 20, ME),
  room(14, 'Board Room', 12, ME),
  room(15, 'Other Room', 30, { id: 99, name_en: 'Someone', name_kh: 'x' }),
  room(12, 'Mekong Room', 200, ME, false),
]
const session = (date: string, start = '14:00') => ({ id: 1, date, start_time: start, end_time: '15:30' })
const ITEMS = [
  listItem(21, {
    meeting_title: 'Board risk review',
    reference_code: 'NBC-26-39730',
    route: 'R2',
    status: 'PENDING_OWNER',
    display_status: 'PENDING_OWNER',
    room: { ...listItem(1).room, id: 13, name_en: 'Governor Room', name_kh: 'Governor Room KH' },
    first_session: session('2026-11-05'),
    attendees: 25,
    has_it: true,
    meeting_type: 'INTERNAL_WITH_GOVERNOR',
  }),
]
const DETAIL = {
  private_justification: 'The Governor attends',
  reviews: [{ stage: 'PITIKA', decision: 'APPROVED', reviewer: { id: 9, name_en: 'Chan Sophea' }, notes: 'Check the projector', reviewed_at: '2026-11-05T01:00:00Z', by_admin: false }],
  catering: { packages: [{ id: 1, name: 'Lunch box' }], servings: 25, delivery_date: '2026-11-05', delivery_time: '12:00', remarks: null },
  it: { items: [{ id: 2, name: 'Projector setup' }], special_requirements: null, staff: [], status: 'RECEIVED', forwarded_at: null, assigned_at: null, ready_at: null },
}

const calls: string[] = []
const bodies: string[] = []
let items: Array<ReturnType<typeof listItem>>

function json(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } })
}

beforeEach(() => {
  vi.useFakeTimers({ toFake: ['Date'] })
  vi.setSystemTime(new Date('2026-11-05T02:20:00Z'))
  setActivePinia(createPinia())
  useSessionStore().accessToken = 'A1'
  useSessionStore().user = { id: 7, roles: [{ code: 'ROOM_OWNER' }], province: PP } as never
  calls.length = 0
  bodies.length = 0
  items = ITEMS
  vi.stubGlobal(
    'fetch',
    vi.fn<typeof fetch>(async (input, init) => {
      const url = new URL(String(input))
      calls.push(`${init?.method ?? 'GET'} ${url.pathname}${url.search}`)
      if (/^\/api\/v1\/owner\/bookings\/\d+\/(approve|reject)$/.test(url.pathname)) {
        bodies.push(String(init?.body))
        items = []
        return json({ ...ITEMS[0], status: 'SETUP_IN_PROGRESS' })
      }
      if (url.pathname === '/api/v1/owner/bookings') return json({ items, page: 1, size: 100, total: items.length })
      if (url.pathname === '/api/v1/owner/bookings/summary') return json({ waiting: items.length, approved_today: 2, rejected_today: 0 })
      if (url.pathname === '/api/v1/owner/bookings/decided') return json({ items: [], page: 1, size: 20, total: 0 })
      if (/^\/api\/v1\/bookings\/21$/.test(url.pathname)) {
        const base = ITEMS[0]!
        return json({
          ...base,
          requester_info: { name_en: 'Sok Dara', division: 'Payments' },
          meeting_purpose: null,
          participant_emails: [],
          sessions: [base.first_session],
          last_end: { date: base.first_session.date, time: base.first_session.end_time },
          rejection: null,
          cancelled_at: null,
          cancel_reason: null,
          cancelled_by: null,
          ...DETAIL,
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

async function mountOwner(path = '/owner-review') {
  const router = createRouter({ history: createMemoryHistory(), routes: [{ path: '/owner-review', name: 'owner-review', component: ReviewView }] })
  await router.push(path)
  const wrapper = mount(ReviewView, { props: { reviewer: 'owner' }, global: { plugins: [router] }, attachTo: document.body })
  await flushPromises()
  return { wrapper, router }
}
const row = (wrapper: Awaited<ReturnType<typeof mountOwner>>['wrapper']) => wrapper.get('[data-booking="21"]')
const dialog = () => document.body.querySelector('.action-dialog') as HTMLElement | null
const panel = () => document.body.querySelector('.review-panel')?.closest('[role="dialog"]') as HTMLElement | null
const button = (root: ParentNode | null, text: string) => [...(root?.querySelectorAll<HTMLButtonElement>('button') ?? [])].find((b) => b.textContent?.trim() === text)

describe('Owner To review', () => {
  it('asks for the bookings waiting for me, all on one page, and my summary', async () => {
    await mountOwner()
    expect(calls).toContain('GET /api/v1/owner/bookings?status=PENDING_OWNER&page=1&size=100')
    expect(calls).toContain('GET /api/v1/owner/bookings/summary')
    expect(calls.some((c) => c.includes('/pitika/'))).toBe(false)
  })

  it('shows what an owner checks, and no food or IT labels', async () => {
    const { wrapper } = await mountOwner()
    const checks = row(wrapper).findAll('.chk').map((c) => c.text())
    expect(checks).toEqual(['Private · reason given', 'With Governor', '25 people · 20 seats', 'Pitika notes'])
    expect(row(wrapper).get('.chk.seats').classes()).toContain('over')
    expect(row(wrapper).find('.chk.food').exists()).toBe(false)
  })

  it('draws the row bar with Pitika done and the gap for my decision', async () => {
    const { wrapper } = await mountOwner()
    const steps = row(wrapper).findAll('.process-bar li.step .n').map((n) => n.text())
    expect(steps).toEqual(['Sent', 'Pitika', 'IT setup', 'Confirmed'])
    expect(row(wrapper).findAll('.process-bar li.step.gap')).toHaveLength(1)
  })

  it('opens the panel with my waiting label and the Pitika notes', async () => {
    const { wrapper } = await mountOwner()
    await row(wrapper).trigger('click')
    await flushPromises()
    expect(panel()?.textContent).toContain('Waiting for room owner')
    expect(panel()?.textContent).toContain('The Pitika wrote: “Check the projector”')
  })

  it('approves through the owner API and says IT setup is next', async () => {
    const { wrapper } = await mountOwner()
    button(row(wrapper).element, 'Approve')!.click()
    await flushPromises()
    expect(dialog()?.textContent).toContain('It goes to IT setup next.')
    dialog()!.querySelector<HTMLElement>('button.confirm')!.click()
    await flushPromises()

    expect(calls).toContain('POST /api/v1/owner/bookings/21/approve')
    expect(bodies).toEqual([JSON.stringify({ notes: null, version: 1 })])
    expect(useToast().toasts.value.map((t) => t.title)).toContain('NBC-26-39730 approved')
  })

  it('needs a reason of 5 characters to reject', async () => {
    const { wrapper } = await mountOwner()
    button(row(wrapper).element, 'Reject')!.click()
    await flushPromises()
    expect(dialog()!.querySelector<HTMLButtonElement>('button.confirm')!.disabled).toBe(true)
  })

  it('lists my decisions on the Approved tab', async () => {
    await mountOwner('/owner-review?tab=approved')
    expect(calls).toContain('GET /api/v1/owner/bookings/decided?decision=APPROVED&page=1&size=20')
  })

  it('filters by my private rooms only', async () => {
    await mountOwner()
    expect(await pickerOptions('filter-room')).toEqual(['All rooms', 'Governor Room', 'Board Room'])
  })
})
