import { enableAutoUnmount, flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createMemoryHistory, createRouter, type Router } from 'vue-router'

import { NAV_GROUPS } from '../../layouts/nav'
import { useSessionStore } from '../../stores/session'
import { choosePicker } from '../../test-utils/picker'
import { building, roomItem } from '../../test-utils/staff'
import RoomAvailabilityView from '../RoomAvailabilityView.vue'

enableAutoUnmount(afterEach)

// Now: Wed 4 Nov 2026, 10:20 in Phnom Penh. Two Phnom Penh rooms and one in Siem Reap.
const ROOMS = [
  roomItem(12, 'Mekong Room', { start_time: '07:30', end_time: '18:00', building: building(1, 'Head office') }),
  roomItem(13, 'Board Room', { start_time: '07:30', end_time: '18:00', is_private: true, building: building(2, 'Annex') }),
  roomItem(99, 'Siem Reap Room', { province: { code: 'SIEM_REAP', name_en: 'Siem Reap', name_kh: 'x' } }),
]
const item = (booking: number, start: string, end: string, title: string, status: string, extra: Record<string, unknown> = {}) => ({
  date: '2026-11-04',
  start_time: start,
  end_time: end,
  booking_id: booking,
  reference_code: `NBC-26-${booking}`,
  title,
  requester_name: 'Sok Dara',
  status,
  is_masked: false,
  ...extra,
})
let day: Record<number, unknown[]>
const calls: string[] = []

function json(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } })
}

beforeEach(() => {
  vi.useFakeTimers({ toFake: ['Date'] })
  vi.setSystemTime(new Date('2026-11-04T03:20:00Z'))
  setActivePinia(createPinia())
  const session = useSessionStore()
  session.accessToken = 'A1'
  session.user = { id: 5, name_en: 'Chan Sophea', roles: [{ code: 'PITIKA' }], province: { code: 'PHNOM_PENH', name_en: 'Phnom Penh', name_kh: 'x' } } as never
  calls.length = 0
  day = {
    12: [item(70, '09:00', '10:30', 'Budget review', 'CONFIRMED')],
    13: [item(71, '14:00', '16:00', 'Risk review', 'PENDING_PITIKA')],
  }
  vi.stubGlobal(
    'fetch',
    vi.fn<typeof fetch>(async (input) => {
      const url = new URL(String(input))
      calls.push(`${url.pathname}${url.search}`)
      if (url.pathname === '/api/v1/rooms') return json({ items: ROOMS, page: 1, size: 100, total: ROOMS.length })
      if (url.pathname === '/api/v1/room-schedule') {
        const ids = (url.searchParams.get('room_ids') ?? '').split(',').map(Number)
        const items = ids.map((id) => ({ room_id: id, items: day[id] ?? [] }))
        return json({ items, total: items.length })
      }
      return json({ items: [], page: 1, size: 20, total: 0 })
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
      { path: '/room-availability', name: 'room-availability', component: RoomAvailabilityView },
      { path: '/bookings', name: 'bookings', component: { template: '<div />' } },
      { path: '/', name: 'home', component: { template: '<div />' } },
    ],
  })
  await router.push(path)
  const wrapper = mount(RoomAvailabilityView, { global: { plugins: [router] }, attachTo: document.body })
  await flushPromises()
  return { wrapper, router }
}
/** The text on a picker's button (our dropdown, SearchPicker). */
const pickerText = (id: string) => document.getElementById(id)?.textContent?.trim() ?? ''
/** Types in the list search (it waits 300ms after the last key). */
async function search(w: Awaited<ReturnType<typeof mountAt>>['wrapper'], text: string) {
  await w.get('.search input').setValue(text)
  await new Promise((done) => setTimeout(done, 350))
  await flushPromises()
}
const rowIds = (w: Awaited<ReturnType<typeof mountAt>>['wrapper']) => w.findAll('[data-room]').map((r) => Number(r.attributes('data-room')))

describe('RoomAvailabilityView', () => {
  it('shows only rooms of my province, and asks for their day in one call', async () => {
    const { wrapper } = await mountAt('/room-availability?date=2026-11-04')

    expect(wrapper.get('h1').text()).toBe('Room availability')
    expect(rowIds(wrapper).sort()).toEqual([12, 13])
    expect(calls).toContain('/api/v1/room-schedule?date=2026-11-04&room_ids=12%2C13')
  })

  it('draws each booking on the lane: booked or waiting', async () => {
    const { wrapper } = await mountAt('/room-availability')

    const budget = wrapper.get('[data-room="12"] .block')
    expect(budget.text()).toContain('Budget review')
    expect(budget.text()).toContain('09:00–10:30')
    expect(budget.classes()).toContain('booked')
    expect(wrapper.get('[data-room="13"] .block').classes()).toContain('waiting')
  })

  it('Free at Now puts the free rooms first and says how many', async () => {
    const { wrapper } = await mountAt('/room-availability')

    expect(pickerText('free-at')).toBe('Now')
    expect(rowIds(wrapper)).toEqual([13, 12]) // Mekong Room is in use at 10:20
    expect(wrapper.get('.result').text()).toBe('1 of 2 rooms free at 10:20, now')
    expect(wrapper.get('[data-room="13"] .fits').text()).toBe('Free until 14:00')
    expect(wrapper.get('[data-room="12"]').classes()).toContain('not-free')
    expect(wrapper.findAll('.now-line')).toHaveLength(2)
  })

  it('Free at 14:00 shows the rooms free then', async () => {
    const { wrapper } = await mountAt('/room-availability')

    await choosePicker('free-at', '14:00')
    expect(rowIds(wrapper)).toEqual([12, 13])
    expect(wrapper.get('[data-room="12"] .fits').text()).toBe('Free for the rest of the day')
    expect(wrapper.get('.result').text()).toBe('1 of 2 rooms free at 14:00')
  })

  it('filters by search, kind and building, and Clear filters resets them', async () => {
    const { wrapper } = await mountAt('/room-availability')

    await search(wrapper, 'board')
    expect(rowIds(wrapper)).toEqual([13])
    await search(wrapper, '')
    await choosePicker('room-kind', 'Shared rooms')
    expect(rowIds(wrapper)).toEqual([12])
    await choosePicker('room-kind', 'Shared and private')
    await choosePicker('room-building', 'Annex')
    expect(rowIds(wrapper)).toEqual([13])

    await wrapper.get('button.clear-filters').trigger('click')
    await flushPromises()
    expect(rowIds(wrapper).sort()).toEqual([12, 13])
    expect(pickerText('room-building')).toBe('All buildings')
    expect(wrapper.find('button.clear-filters').exists()).toBe(false)
  })

  it('another day has no Now line, and Free at starts at Any time', async () => {
    const { wrapper } = await mountAt('/room-availability?date=2026-11-05')

    expect(wrapper.find('.now-line').exists()).toBe(false)
    expect(pickerText('free-at')).toBe('Any time')
    expect(wrapper.find('.result').exists()).toBe(false)
  })

  it('is in the Daily group of the sidebar after Food list, for Admin and Pitika', () => {
    const daily = NAV_GROUPS.find((g) => g.title === 'Daily')!
    const routes = daily.items.map((i) => i.route)
    expect(routes.indexOf('room-availability')).toBe(routes.indexOf('food-list') + 1)
    const entry = daily.items.find((i) => i.route === 'room-availability')!
    expect([entry.label, entry.roles]).toEqual(['Room availability', ['ADMIN', 'PITIKA']])
  })
})
