import { enableAutoUnmount, flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createMemoryHistory, createRouter, type Router } from 'vue-router'

import { useSessionStore } from '../../../stores/session'
import { building, roomItem } from '../../../test-utils/staff'
import FindRoomView from '../FindRoomView.vue'

enableAutoUnmount(afterEach)

const ROOMS = [
  roomItem(1, 'Mekong Room'),
  roomItem(2, 'Bassac Room', { building: building(2, 'Annex') }),
  roomItem(3, 'Governor Room', { is_private: true }),
]
const busy = (start: string, end: string) => ({
  date: '2026-11-12',
  start_time: start,
  end_time: end,
  booking_id: 9,
  reference_code: 'NBC-26-9',
  title: 'Budget',
  requester_name: 'Sok Dara',
  status: 'CONFIRMED',
  is_masked: false,
})
const calls: string[] = []

function json(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } })
}

let router: Router
beforeEach(async () => {
  // Thursday 12 Nov 2026, 10:00 in Phnom Penh
  vi.useFakeTimers({ toFake: ['Date'] })
  vi.setSystemTime(new Date('2026-11-12T03:00:00Z'))
  setActivePinia(createPinia())
  useSessionStore().accessToken = 'A1'
  calls.length = 0
  vi.stubGlobal(
    'fetch',
    vi.fn<typeof fetch>(async (input) => {
      const url = new URL(String(input))
      calls.push(url.pathname + url.search)
      if (url.pathname === '/api/v1/rooms') return json({ items: ROOMS, page: 1, size: 100, total: ROOMS.length })
      if (url.pathname === '/api/v1/room-schedule')
        return json({
          items: [
            { room_id: 1, items: [busy('14:00', '15:00')] },
            { room_id: 2, items: [busy('09:30', '11:00')] },
            { room_id: 3, items: [] },
          ],
          total: 3,
        })
      return json({}, 404)
    }),
  )
  const Empty = { template: '<div />' }
  router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/find-room', name: 'find-room', component: FindRoomView },
      { path: '/find-room/:roomId', name: 'staff-room', component: Empty },
      { path: '/book/:roomId', name: 'book', component: Empty },
    ],
  })
  await router.push('/find-room')
})
afterEach(() => {
  vi.useRealTimers()
  vi.unstubAllGlobals()
})

async function open() {
  const wrapper = mount(FindRoomView, { global: { plugins: [router] } })
  await flushPromises()
  return wrapper
}
const names = (w: Awaited<ReturnType<typeof open>>) => w.findAll('.room-card h2').map((h) => h.text())

describe('Find a room', () => {
  it('shows one card per room and asks every room’s day in one request', async () => {
    const w = await open()
    expect(names(w)).toEqual(['Mekong Room', 'Bassac Room', 'Governor Room'])
    const day = calls.filter((c) => c.startsWith('/api/v1/room-schedule'))
    expect(day).toEqual(['/api/v1/room-schedule?date=2026-11-12&room_ids=1%2C2%2C3'])
  })

  it('says until when each room is free or in use, and Free now hides the busy one', async () => {
    const w = await open()
    const lineOf = (name: string) => w.findAll('.room-card').find((c) => c.find('h2').text() === name)!.find('.now').text()
    expect(lineOf('Mekong Room')).toBe('Free until 14:00')
    expect(lineOf('Bassac Room')).toBe('In use until 11:00')
    expect(lineOf('Governor Room')).toBe('Free all day')
    await w.get('button.free-now').trigger('click')
    expect(names(w)).toEqual(['Mekong Room', 'Governor Room'])
  })

  it('offers Request on a private room and Book on a shared one', async () => {
    const w = await open()
    expect(w.find('[aria-label="Request Governor Room"]').exists()).toBe(true)
    expect(w.find('[aria-label="Book Mekong Room"]').exists()).toBe(true)
    await w.get('[aria-label="Book Mekong Room"]').trigger('click')
    await flushPromises()
    expect(router.currentRoute.value.name).toBe('book')
    expect(router.currentRoute.value.params.roomId).toBe('1')
    expect(router.currentRoute.value.query.date).toBeUndefined()
  })

  it('opens the room page from Details', async () => {
    const w = await open()
    await w.get('[aria-label="Details of Bassac Room"]').trigger('click')
    await flushPromises()
    expect(router.currentRoute.value).toMatchObject({ name: 'staff-room', params: { roomId: '2' } })
  })

  it('filters by search, building and type', async () => {
    const w = await open()
    await w.get('input[type="search"]').setValue('mekong')
    expect(names(w)).toEqual(['Mekong Room'])
    await w.get('input[type="search"]').setValue('')
    await w.get('[role="radio"][data-building="2"]').trigger('click')
    expect(names(w)).toEqual(['Bassac Room'])
    await w.get('[role="radio"][data-building="all"]').trigger('click')
    await w.get('[role="radio"][data-kind="private"]').trigger('click')
    expect(names(w)).toEqual(['Governor Room'])
  })

  it('says so when nothing matches, and Clear filters brings every room back', async () => {
    const w = await open()
    await w.get('input[type="search"]').setValue('zzz')
    expect(w.text()).toContain('No room matches')
    await w.get('button.clear').trigger('click')
    expect(names(w)).toHaveLength(3)
  })
})
