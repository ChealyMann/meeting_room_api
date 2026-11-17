import { enableAutoUnmount, flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createMemoryHistory, createRouter, type Router } from 'vue-router'

import { NAV_GROUPS } from '../../layouts/nav'
import { useSessionStore } from '../../stores/session'
import { pickDate } from '../../test-utils/datePicker'
import { bookingDetail, bookingItem } from '../../test-utils/staff'
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
    building: { id: 2, name_en: 'Building A', name_kh: 'អគារ A', short_name: 'A' },
    floor: { id: 4, floor_label: '2nd floor' },
    capacity: 20,
    category: { id: 1, name_en: 'Meeting Room', name_kh: 'បន្ទប់ប្រជុំ' },
    owner: null,
    map_query: null,
  },
  meeting_title: 'Budget review',
  delivery_date: '2026-11-04',
  delivery_time: '12:00',
  packages: [
    { id: 1, name: 'Coffee break' },
    { id: 2, name: 'Lunch box' },
  ],
  remarks: 'No pork',
  approver_notes: 'Approved',
  session_number: 1,
  session_count: 1,
  ...changes,
})

const calls: string[] = []
const bookingCalls: string[] = []
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
  bookingCalls.length = 0
  orders = [order()]
  vi.stubGlobal(
    'fetch',
    vi.fn<typeof fetch>(async (input) => {
      const url = new URL(String(input))
      if (url.pathname === '/api/v1/pitika/catering') {
        calls.push(url.search)
        return json({ items: orders, total: orders.length })
      }
      if (url.pathname === '/api/v1/bookings/7') {
        bookingCalls.push(url.pathname)
        return json(bookingDetail(bookingItem(7, 'Budget review', 'CONFIRMED', '2026-11-04')))
      }
      return json({ items: [], page: 1, size: 1, total: 0 })
    }),
  )
})

afterEach(() => {
  vi.useRealTimers()
  vi.unstubAllGlobals()
  document.body.innerHTML = ''
})

async function mountAt(path: string) {
  const router: Router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/food-list', name: 'food-list', component: FoodListView },
      { path: '/bookings', name: 'bookings', component: FoodListView },
      { path: '/', name: 'home', component: { template: '<div />' } },
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

  it('jumps to a day picked in the date picker', async () => {
    const { router } = await mountAt('/food-list')

    await pickDate('food-day', '2026-11-20')

    expect(router.currentRoute.value.query).toEqual({ date: '2026-11-20' })
    expect(calls[calls.length - 1]).toBe('?date=2026-11-20')
  })

  it('shows each order: the time, where to bring it (room, floor, building, office), the food and the meeting', async () => {
    const { wrapper } = await mountAt('/food-list?date=2026-11-04')

    expect(wrapper.findAll('thead th').map((th) => th.text())).toEqual(['Time', 'Deliver to', 'Food', 'Meeting', 'IT'])
    const row = wrapper.get('tbody tr[data-order]')
    const texts = (selector: string) => row.findAll(selector).map((e) => e.text())
    expect(texts('.time .mono')).toEqual(['12:00'])
    expect(texts('.room, .room-kh, .floor, td:nth-child(2) .sub')).toEqual(['Mekong Room', 'បន្ទប់មេគង្គ', '2nd floor', 'Building A · Head Office'])
    expect(texts('.packages-line, .note')).toEqual(['Coffee break, Lunch box', 'Booker: No pork', 'Pitika: Approved'])
    expect(texts('.meeting .title, .meeting .sub')).toEqual(['Budget review', 'NBC-26-48213'])
    // A confirmed booking says nothing more; food has no numbers (owner decision, 17 Nov 2026).
    expect(row.get('.it').text()).toBe('')
    expect(row.text()).not.toMatch(/\d+ ?×|servings/i)
  })

  it('says "IT setting up" only while IT is still setting up', async () => {
    orders = [order(), order({ booking_id: 8, booking_status: 'SETUP_IN_PROGRESS' })]
    const { wrapper } = await mountAt('/food-list?date=2026-11-04')

    expect(wrapper.findAll('tbody tr[data-order] .it').map((td) => td.text())).toEqual(['', 'IT setting up'])
  })

  it('has no "To prepare" card above the table (owner, 17 Nov 2026)', async () => {
    const { wrapper } = await mountAt('/food-list')
    expect(wrapper.find('.prep').exists()).toBe(false)
    expect(wrapper.text()).not.toContain('To prepare')
  })

  it('today: past rows are faded, the next time is marked, and a red Now line sits between them', async () => {
    vi.setSystemTime(new Date('2026-11-04T05:20:00Z')) // 12:20 in Phnom Penh
    orders = [
      order({ delivery_time: '08:00', packages: [{ id: 3, name: 'តែ' }] }),
      order({ booking_id: 8, delivery_time: '12:00' }),
      order({ booking_id: 9, delivery_time: '14:00', packages: [{ id: 2, name: 'Lunch box' }] }),
    ]
    const { wrapper } = await mountAt('/food-list')

    const rows = wrapper.findAll('tbody tr')
    expect(rows.map((r) => (r.classes('now-line') ? 'now' : r.attributes('data-state')))).toEqual(['past', 'past', 'now', 'next'])
    expect(wrapper.get('.now-line').text()).toBe('Now 12:20')
    expect(wrapper.get('tr[data-state="next"]').text()).toContain('Next')
  })

  it('another day has no Now line, no Next and nothing faded', async () => {
    const { wrapper } = await mountAt('/food-list?date=2026-11-05')

    expect(wrapper.find('.now-line').exists()).toBe(false)
    expect(wrapper.get('tbody tr[data-order]').attributes('data-state')).toBe('later')
  })

  it('shows each session of a booking with food as its own delivery, saying which session it is', async () => {
    orders = [order({ delivery_time: '08:00', session_number: 3, session_count: 4 }), order({ delivery_time: '14:00', session_number: 4, session_count: 4 })]
    const { wrapper } = await mountAt('/food-list?date=2026-11-04')

    const rows = wrapper.findAll('tbody tr[data-order]')
    expect(rows.map((r) => r.get('.time').text())).toEqual(['08:00Next', '14:00'])
    expect(rows.map((r) => r.get('.session').text())).toEqual(['Session 3 of 4', 'Session 4 of 4'])
  })

  it('says nothing about sessions for a one-session booking', async () => {
    const { wrapper } = await mountAt('/food-list?date=2026-11-04')
    expect(wrapper.find('tbody .session').exists()).toBe(false)
  })

  it("puts the booker's note and the Pitika note under the food, and nothing when there is none", async () => {
    orders = [order(), order({ booking_id: 8, remarks: null, approver_notes: null })]
    const { wrapper } = await mountAt('/food-list?date=2026-11-04')

    const notes = (row: number) => wrapper.findAll('tbody tr[data-order]')[row]!.findAll('.note').map((n) => n.text())
    expect(notes(0)).toEqual(['Booker: No pork', 'Pitika: Approved'])
    expect(notes(1)).toEqual([])
  })

  it('moves to the new day when the list stays open past midnight', async () => {
    vi.useFakeTimers({ toFake: ['Date', 'setInterval', 'clearInterval'] })
    vi.setSystemTime(new Date('2026-11-04T16:59:00Z')) // 23:59 in Phnom Penh
    const { wrapper } = await mountAt('/food-list')
    expect(calls).toEqual(['?date=2026-11-04'])

    vi.setSystemTime(new Date('2026-11-04T17:01:00Z')) // 00:01 on 5 Nov
    vi.advanceTimersByTime(60_000)
    await flushPromises()

    expect(calls[calls.length - 1]).toBe('?date=2026-11-05')
    expect(wrapper.text()).toContain('Thu 5 Nov 2026')
  })

  it('keeps a chosen day when the date changes', async () => {
    vi.useFakeTimers({ toFake: ['Date', 'setInterval', 'clearInterval'] })
    vi.setSystemTime(new Date('2026-11-04T16:59:00Z'))
    await mountAt('/food-list?date=2026-11-02')

    vi.setSystemTime(new Date('2026-11-04T17:01:00Z'))
    vi.advanceTimersByTime(60_000)
    await flushPromises()

    // The quiet refresh asks again, always for the chosen day.
    expect([...new Set(calls)]).toEqual(['?date=2026-11-02'])
  })

  it('opens the booking in a drawer on this page, not on the Bookings page (owner, 17 Nov 2026)', async () => {
    const { wrapper, router } = await mountAt('/food-list?date=2026-11-04')

    await wrapper.get('tbody tr[data-order] button.title').trigger('click')
    await flushPromises()

    expect(router.currentRoute.value.name).toBe('food-list')
    expect(router.currentRoute.value.query).toEqual({ date: '2026-11-04', booking: '7' })
    expect(bookingCalls).toEqual(['/api/v1/bookings/7'])
    const drawer = document.body.querySelector('[role="dialog"]')
    expect(drawer?.querySelector('h2')?.textContent).toBe('Budget review')
    expect(wrapper.find('tbody a').exists()).toBe(false)
  })

  it('opens the drawer from the address, and closes it again', async () => {
    const { router } = await mountAt('/food-list?booking=7')
    await flushPromises()
    expect(document.body.querySelector('[role="dialog"] h2')?.textContent).toBe('Budget review')

    ;(document.body.querySelector('[role="dialog"] button[aria-label="Close"]') as HTMLButtonElement).click()
    await flushPromises()
    expect(router.currentRoute.value.query).toEqual({})
  })

  it('says when there is no food that day', async () => {
    orders = []
    const { wrapper } = await mountAt('/food-list')

    expect(wrapper.text()).toContain('No food orders on this day.')
  })

  it('is in the Daily group of the sidebar', () => {
    const group = NAV_GROUPS.find((g) => g.title === 'Daily')
    expect(group?.items.find((i) => i.label === 'Food list')?.route).toBe('food-list')
  })
})
