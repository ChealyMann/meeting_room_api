import { enableAutoUnmount, flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createMemoryHistory, createRouter } from 'vue-router'

import { REVIEW_SUMMARY_EVENT } from '../../composables/useWaitingCounts'
import { useSessionStore } from '../../stores/session'
import { listItem } from '../../test-utils/bookings'
import MyTasksView from '../MyTasksView.vue'

enableAutoUnmount(afterEach)

// Now: Thu 5 Nov 2026, 06:00 in Phnom Penh. I am IT Staff 32.
const ME = { id: 32, name_en: 'Sok Pisey', name_kh: 'x', is_active: true }
const ticket = (id: number, setup_date: string) => ({
  id,
  status: 'ASSIGNED',
  items: [{ id: 1, name: 'Projector setup' }],
  special_requirements: null,
  technician_notes: 'Bring the long HDMI cable',
  staff: [ME],
  setup_date,
  setup_time: '07:30',
  forwarded_at: '2026-11-04T02:00:00Z',
  assigned_at: '2026-11-04T03:00:00Z',
  ready_at: null,
  missed: false,
  review_notes: [],
  booking: listItem(100 + id, {
    meeting_title: `Training ${id}`,
    status: 'SETUP_IN_PROGRESS',
    display_status: 'SETUP_IN_PROGRESS',
    first_session: { id: 1, date: setup_date, start_time: '08:00', end_time: '11:00' },
    has_it: true,
  }),
})
let items: ReturnType<typeof ticket>[]
const calls: string[] = []
const reported: unknown[] = []
const onReport = (e: Event) => reported.push((e as CustomEvent).detail)

function json(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } })
}

beforeEach(() => {
  vi.useFakeTimers({ toFake: ['Date'] })
  vi.setSystemTime(new Date('2026-11-04T23:00:00Z'))
  setActivePinia(createPinia())
  useSessionStore().accessToken = 'A1'
  useSessionStore().user = { id: 32, roles: [{ code: 'IT_STAFF' }] } as never
  calls.length = 0
  reported.length = 0
  items = [ticket(7, '2026-11-05'), ticket(8, '2026-11-07')]
  window.addEventListener(REVIEW_SUMMARY_EVENT, onReport)
  vi.stubGlobal(
    'fetch',
    vi.fn<typeof fetch>(async (input, init) => {
      const url = new URL(String(input))
      calls.push(`${init?.method ?? 'GET'} ${url.pathname}${url.search}`)
      if (url.pathname === '/api/v1/it/tickets') return json({ items, page: 1, size: 100, total: items.length })
      if (/^\/api\/v1\/bookings\/\d+$/.test(url.pathname)) return json({ error: { code: 'NOT_FOUND', message: 'Not found.', fields: {} } }, 404)
      return json({ items: [], page: 1, size: 100, total: 0 })
    }),
  )
})
afterEach(() => {
  window.removeEventListener(REVIEW_SUMMARY_EVENT, onReport)
  vi.useRealTimers()
  vi.unstubAllGlobals()
})

async function mountAt(path = '/my-tasks') {
  const router = createRouter({ history: createMemoryHistory(), routes: [{ path: '/my-tasks', name: 'my-tasks', component: MyTasksView }] })
  await router.push(path)
  const wrapper = mount(MyTasksView, { global: { plugins: [router] }, attachTo: document.body })
  await flushPromises()
  return { wrapper, router }
}
const panel = () => document.body.querySelector('.it-panel')?.closest('[role="dialog"]') as HTMLElement | null

describe('My tasks', () => {
  it('asks for my setups not ready yet, on one page', async () => {
    await mountAt()
    expect(calls).toContain('GET /api/v1/it/tickets?state=in_progress&mine=true&page=1&size=100')
  })

  it('says how many and what is next, and groups by setup day', async () => {
    const { wrapper } = await mountAt()
    expect(wrapper.get('h1').text()).toBe('My tasks')
    expect(wrapper.get('.sub').text()).toBe('2 setups to do · next: today 07:30, Mekong Room')
    expect(wrapper.findAll('.group-head h2').map((h) => h.text())).toEqual(['Today', 'This week'])
    expect(wrapper.find('[role="tab"]').exists()).toBe(false)
  })

  it('has no buttons on the rows, and the panel has only Close', async () => {
    const { wrapper } = await mountAt()
    expect(wrapper.get('[data-ticket="7"]').findAll('button')).toHaveLength(0)
    await wrapper.get('[data-ticket="7"]').trigger('click')
    await flushPromises()
    expect(panel()?.textContent).toContain('Bring the long HDMI cable')
    const foot = [...(panel()?.querySelectorAll('.panel-foot button') ?? [])].map((b) => b.textContent?.trim())
    expect(foot).toEqual(['Close'])
  })

  it('says when there is nothing to set up', async () => {
    items = []
    const { wrapper } = await mountAt()
    expect(wrapper.text()).toContain('Nothing to set up')
    expect(wrapper.text()).toContain('Setups assigned to you show here.')
  })

  it('still asks for mine only when I am also the IT Lead', async () => {
    useSessionStore().user = { id: 32, roles: [{ code: 'IT_LEAD' }, { code: 'IT_STAFF' }] } as never
    await mountAt()
    expect(calls.filter((c) => c.startsWith('GET /api/v1/it/tickets'))).toEqual(['GET /api/v1/it/tickets?state=in_progress&mine=true&page=1&size=100'])
  })

  it('tells the menu how many tasks there are', async () => {
    await mountAt()
    expect(reported).toContainEqual({ route: 'my-tasks', waiting: 2 })
  })
})
