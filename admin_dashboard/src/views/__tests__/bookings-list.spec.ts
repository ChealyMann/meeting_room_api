import { enableAutoUnmount, flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createMemoryHistory, createRouter, type Router } from 'vue-router'

import { NAV_GROUPS } from '../../layouts/nav'
import { useSessionStore } from '../../stores/session'
import { pickerLabel } from '../../test-utils/picker'
import BookingsView from '../BookingsView.vue'

enableAutoUnmount(afterEach)

export const listItem = (id: number, changes: Record<string, unknown> = {}) => ({
  id,
  reference_code: 'NBC-26-48213',
  room: {
    id: 12,
    name_en: 'Mekong Room',
    name_kh: 'បន្ទប់មេគង្គ',
    is_private: false,
    location: { id: 3, name_en: 'Head Office', name_kh: 'ការិយាល័យកណ្តាល' },
    province: { code: 'PP', name_en: 'Phnom Penh', name_kh: 'ភ្នំពេញ' },
  },
  meeting_title: 'Budget review',
  meeting_type: 'INTERNAL',
  route: 'R1',
  status: 'PENDING_PITIKA',
  display_status: 'PENDING_PITIKA',
  requester: { id: 4, name_en: 'Sok Dara', name_kh: 'សុខ ដារា' },
  first_session: { id: 1, date: '2026-11-10', start_time: '09:00', end_time: '10:30' },
  session_count: 3,
  attendees: 10,
  has_catering: true,
  has_it: false,
  created_at: '2026-11-03T02:00:00Z',
  version: 1,
  ...changes,
})

const listCalls: string[] = []
let listAnswer: () => Response

function json(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } })
}

beforeEach(() => {
  setActivePinia(createPinia())
  useSessionStore().accessToken = 'A1'
  listCalls.length = 0
  listAnswer = () => json({ items: [listItem(12)], page: 1, size: 20, total: 1 })
  vi.stubGlobal(
    'fetch',
    vi.fn<typeof fetch>(async (input) => {
      const url = new URL(String(input))
      if (url.pathname === '/api/v1/bookings') {
        listCalls.push(url.search)
        return listAnswer()
      }
      if (url.pathname === '/api/v1/provinces') return json({ items: [{ code: 'PP', name_en: 'Phnom Penh', name_kh: 'ភ្នំពេញ' }], total: 1 })
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

describe('BookingsView', () => {
  it('asks the API with the status from the address and shows its words', async () => {
    await mountAt('/bookings?status=PENDING_OWNER')

    expect(listCalls[listCalls.length - 1]).toBe('?status=PENDING_OWNER&page=1&size=20')
    expect(pickerLabel('filter-status')).toBe('Waiting for owner')
  })

  it('shows each booking in a row', async () => {
    const { wrapper } = await mountAt('/bookings')

    const row = wrapper.get('tbody tr')
    expect(row.text()).toContain('NBC-26-48213')
    expect(row.text()).toContain('Budget review')
    expect(row.text()).toContain('Internal')
    expect(row.text()).toContain('Mekong Room')
    expect(row.text()).toContain('Sok Dara')
    expect(row.text()).toContain('Tue 10 Nov 2026')
    expect(row.text()).toContain('+2 more')
    expect(row.text()).toContain('Waiting for Pitika')
    expect(row.find('[aria-label="Food ordered"]').exists()).toBe(true)
    expect(row.find('[aria-label="IT help asked"]').exists()).toBe(false)
    expect(wrapper.get('.count').text()).toBe('001 booking')
  })

  it('shows the API field message when a filter is refused', async () => {
    listAnswer = () =>
      json({ error: { code: 'VALIDATION_ERROR', message: 'Invalid request.', fields: { to: 'Must be on or after from.' } } }, 422)
    const { wrapper } = await mountAt('/bookings?from=2026-11-10&to=2026-11-01')

    expect(wrapper.get('.load-error').text()).toContain('Must be on or after from.')
    expect(wrapper.find('#filter-to').exists()).toBe(true)
  })

  it('opens a booking through the address', async () => {
    const { wrapper, router } = await mountAt('/bookings')

    await wrapper.get('tbody tr').trigger('click')
    await flushPromises()

    expect(router.currentRoute.value.query.id).toBe('12')
  })

  it('is in the Bookings group of the sidebar', () => {
    const group = NAV_GROUPS.find((g) => g.title === 'Bookings')
    expect(group?.items.map((i) => i.route)).toEqual(['bookings', 'food-list'])
  })
})
