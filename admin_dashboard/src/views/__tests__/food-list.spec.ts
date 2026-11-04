import { enableAutoUnmount, flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createMemoryHistory, createRouter, type Router } from 'vue-router'

import { NAV_GROUPS } from '../../layouts/nav'
import { useSessionStore } from '../../stores/session'
import FoodListView from '../FoodListView.vue'

enableAutoUnmount(afterEach)

const order = (changes: Record<string, unknown> = {}) => ({
  booking_id: 7,
  reference_code: 'NBC-26-48213',
  booking_status: 'CONFIRMED',
  room: {
    id: 12,
    name_en: 'Mekong Room',
    name_kh: 'បន្ទប់មេគង្គ',
    is_private: false,
    location: { id: 3, name_en: 'Head Office', name_kh: 'ការិយាល័យកណ្តាល' },
    province: { code: 'PP', name_en: 'Phnom Penh', name_kh: 'ភ្នំពេញ' },
  },
  meeting_title: 'Budget review',
  delivery_date: '2026-11-04',
  delivery_time: '12:00',
  servings: 25,
  packages: [
    { id: 1, name: 'Coffee break' },
    { id: 2, name: 'Lunch box' },
  ],
  remarks: 'No pork',
  approver_notes: 'Approved',
  ...changes,
})

const calls: string[] = []
let orders: unknown[]

function json(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } })
}

beforeEach(() => {
  vi.useFakeTimers({ toFake: ['Date'] })
  vi.setSystemTime(new Date('2026-11-04T01:00:00Z'))
  setActivePinia(createPinia())
  useSessionStore().accessToken = 'A1'
  calls.length = 0
  orders = [order()]
  vi.stubGlobal(
    'fetch',
    vi.fn<typeof fetch>(async (input) => {
      const url = new URL(String(input))
      if (url.pathname === '/api/v1/pitika/catering') {
        calls.push(url.search)
        return json({ items: orders, total: orders.length })
      }
      return json({ items: [], page: 1, size: 1, total: 0 })
    }),
  )
})

afterEach(() => {
  vi.useRealTimers()
  vi.unstubAllGlobals()
})

async function mountAt(path: string) {
  const router: Router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/food-list', name: 'food-list', component: FoodListView },
      { path: '/bookings', name: 'bookings', component: FoodListView },
    ],
  })
  await router.push(path)
  const wrapper = mount(FoodListView, { global: { plugins: [router] }, attachTo: document.body })
  await flushPromises()
  return { wrapper, router }
}

describe('FoodListView', () => {
  it("asks for today's food list when the address has no day", async () => {
    const { wrapper } = await mountAt('/food-list')

    expect(calls).toEqual(['?date=2026-11-04'])
    expect(wrapper.get('h1').text()).toBe('Food list')
    expect(wrapper.text()).toContain('Wed 4 Nov 2026')
  })

  it('moves to the next day through the address', async () => {
    const { wrapper, router } = await mountAt('/food-list')

    await wrapper.findAll('button').find((b) => b.text() === 'Next day')!.trigger('click')
    await flushPromises()

    expect(router.currentRoute.value.query).toEqual({ date: '2026-11-05' })
    expect(calls[calls.length - 1]).toBe('?date=2026-11-05')
  })

  it('shows each order', async () => {
    const { wrapper } = await mountAt('/food-list?date=2026-11-04')

    const row = wrapper.get('tbody tr').text()
    expect(row).toContain('12:00')
    expect(row).toContain('Mekong Room')
    expect(row).toContain('NBC-26-48213')
    expect(row).toContain('Coffee break, Lunch box')
    expect(row).toContain('25')
    expect(row).toContain('No pork')
    expect(row).toContain('Confirmed')
  })

  it('says when there is no food that day', async () => {
    orders = []
    const { wrapper } = await mountAt('/food-list')

    expect(wrapper.text()).toContain('No food orders on this day.')
  })

  it('is in the Bookings group of the sidebar', () => {
    const group = NAV_GROUPS.find((g) => g.title === 'Bookings')
    expect(group?.items.find((i) => i.label === 'Food list')?.route).toBe('food-list')
  })
})
