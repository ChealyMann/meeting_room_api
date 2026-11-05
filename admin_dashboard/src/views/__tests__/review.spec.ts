import { enableAutoUnmount, flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createMemoryHistory, createRouter } from 'vue-router'

import { useSessionStore } from '../../stores/session'
import { listItem } from '../../test-utils/bookings'
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
  21: { catering: { packages: [{ id: 1, name: 'Lunch box' }], servings: 25 }, it: { items: [{ id: 2, name: 'Projector setup' }] } },
  22: { private_justification: "The Governor's team asked." },
  23: {},
}
const ROOMS = [
  { id: 12, cover_photo: { url: '/uploads/rooms/12/a.jpg', thumbnail_url: '/uploads/rooms/12/a_t.jpg' } },
  { id: 13, cover_photo: null },
]

const calls: string[] = []
let items: unknown[]

function json(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } })
}

beforeEach(() => {
  vi.useFakeTimers({ toFake: ['Date'] })
  vi.setSystemTime(new Date('2026-11-05T02:20:00Z'))
  setActivePinia(createPinia())
  useSessionStore().accessToken = 'A1'
  calls.length = 0
  items = ITEMS
  vi.stubGlobal(
    'fetch',
    vi.fn<typeof fetch>(async (input) => {
      const url = new URL(String(input))
      calls.push(url.pathname + url.search)
      if (url.pathname === '/api/v1/pitika/bookings') return json({ items, page: 1, size: 100, total: items.length })
      const detail = /^\/api\/v1\/bookings\/(\d+)$/.exec(url.pathname)
      if (detail) {
        const id = Number(detail[1])
        const base = ITEMS.find((i) => i.id === id)!
        return json({ ...base, private_justification: null, catering: null, it: null, ...DETAILS[id] })
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

async function mountReview() {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/review', name: 'review', component: ReviewView },
      { path: '/bookings', name: 'bookings', component: ReviewView },
    ],
  })
  await router.push('/review')
  const wrapper = mount(ReviewView, { global: { plugins: [router] }, attachTo: document.body })
  await flushPromises()
  return { wrapper, router }
}

const row = (wrapper: Awaited<ReturnType<typeof mountReview>>['wrapper'], id: number) => wrapper.get(`[data-booking="${id}"]`)

describe('ReviewView', () => {
  it('asks for the bookings waiting for Pitika, all on one page', async () => {
    await mountReview()
    expect(calls).toContain('/api/v1/pitika/bookings?status=PENDING_PITIKA&page=1&size=100')
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
    expect(wrapper.get('.page-head .count').text()).toBe('003 waiting')
  })

  it('shows the booking, its room, its time, and what to check in each row', async () => {
    const { wrapper } = await mountReview()

    const first = row(wrapper, 21).text()
    for (const text of ['NBC-26-87467', 'Payment systems workshop', 'បន្ទប់មេគង្គ', 'Mekong Room', '14:00–15:30', 'Sok Dara', '10 people', 'Lunch box', '×25', 'Projector setup']) {
      expect(first).toContain(text)
    }
    expect(row(wrapper, 22).text()).toContain('Private · reason given')
  })

  it('marks only today’s booking with how soon it starts', async () => {
    const { wrapper } = await mountReview()

    expect(row(wrapper, 21).get('.soon').text()).toBe('Starts in 4 h 40 min')
    expect(wrapper.findAll('.soon')).toHaveLength(1)
  })

  it('draws the row bar with a gap for the decision, and no Pitika step', async () => {
    const { wrapper } = await mountReview()

    const steps = row(wrapper, 22).findAll('.process-bar .step')
    expect(steps.map((s) => s.get('.n').text())).toEqual(['Sent', 'Room owner', 'Confirmed'])
    expect(steps[1]!.classes()).toContain('gap')
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
    expect(wrapper.get('.page-head .count').text()).toBe('000 waiting')
  })
})
