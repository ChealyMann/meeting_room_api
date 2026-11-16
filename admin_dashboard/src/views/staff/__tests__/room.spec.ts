import { enableAutoUnmount, flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createMemoryHistory, createRouter, type Router } from 'vue-router'

import { useSessionStore } from '../../../stores/session'
import { roomItem } from '../../../test-utils/staff'
import RoomView from '../RoomView.vue'

enableAutoUnmount(afterEach)

const photo = (id: number) => ({
  id,
  room_id: 12,
  url: `/media/rooms/12/${id}.jpg`,
  thumbnail_url: `/media/rooms/12/${id}-t.jpg`,
  sort_order: id,
  created_at: '2026-11-01T00:00:00Z',
  updated_at: '2026-11-01T00:00:00Z',
})
const ROOM = {
  ...roomItem(12, 'Mekong Room'),
  description: 'A bright room by the river.',
  photos: [photo(1), photo(2)],
  equipment: [{ id: 5, name: 'Smart TV', icon: 'monitor', sort_order: 1, is_active: true, created_at: '', updated_at: '' }],
  created_at: '2026-11-01T00:00:00Z',
  updated_at: '2026-11-01T00:00:00Z',
}
const calls: string[] = []

function json(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } })
}

let router: Router
beforeEach(async () => {
  vi.useFakeTimers({ toFake: ['Date'] })
  vi.setSystemTime(new Date('2026-11-12T03:00:00Z')) // Thu 12 Nov 2026, 10:00 in Phnom Penh
  setActivePinia(createPinia())
  useSessionStore().accessToken = 'A1'
  calls.length = 0
  vi.stubGlobal(
    'fetch',
    vi.fn<typeof fetch>(async (input) => {
      const url = new URL(String(input))
      calls.push(url.pathname + url.search)
      if (url.pathname === '/api/v1/rooms/12') return json(ROOM)
      if (url.pathname === '/api/v1/rooms/12/schedule')
        return json({
          items: [
            {
              date: '2026-11-13',
              start_time: '10:00',
              end_time: '11:00',
              booking_id: null,
              reference_code: null,
              title: 'Reserved (Private Session)',
              requester_name: null,
              status: 'CONFIRMED',
              is_masked: true,
            },
          ],
          total: 1,
        })
      if (url.pathname === '/api/v1/public-holidays')
        return json({ items: [{ id: 1, holiday_date: '2026-11-16', name_km: 'x', name_en: 'Test holiday' }], page: 1, size: 100, total: 1 })
      return json({}, 404)
    }),
  )
  const Empty = { template: '<div />' }
  router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/find-room/:roomId', name: 'staff-room', component: RoomView },
      { path: '/book/:roomId', name: 'book', component: Empty },
    ],
  })
  await router.push('/find-room/12')
})
afterEach(() => {
  vi.useRealTimers()
  vi.unstubAllGlobals()
})

async function open() {
  const wrapper = mount(RoomView, { global: { plugins: [router] } })
  await flushPromises()
  return wrapper
}
const times = (w: Awaited<ReturnType<typeof open>>) => w.findAll('.tp-times button').map((b) => b.text())

describe('Room details', () => {
  it('shows the room, its photos and its equipment', async () => {
    const w = await open()
    expect(w.find('h1').text()).toBe('Mekong Room')
    expect(w.findAll('.gal-dots button')).toHaveLength(2)
    expect(w.text()).toContain('Smart TV')
    expect(calls.some((c) => c.startsWith('/api/v1/rooms/12/schedule?from=2026-11-12&to=2026-11-18'))).toBe(true)
  })

  it('offers the next 7 days, Saturday and Sunday too', async () => {
    const w = await open()
    expect(w.findAll('.tp-days button[data-day]').map((b) => b.attributes('data-day'))).toEqual([
      '2026-11-12',
      '2026-11-13',
      '2026-11-14',
      '2026-11-15',
      '2026-11-16',
      '2026-11-17',
      '2026-11-18',
    ])
  })

  it('offers only the start times that are free for the chosen length', async () => {
    const w = await open()
    await w.get('.tp-days button[data-day="2026-11-13"]').trigger('click')
    expect(times(w)).toContain('09:00')
    expect(times(w)).not.toContain('09:30')
    expect(times(w)).not.toContain('10:00')
    expect(times(w)).toContain('11:00')
  })

  it('goes on to the booking with the picked time', async () => {
    const w = await open()
    await w.get('.tp-days button[data-day="2026-11-13"]').trigger('click')
    await w.findAll('.tp-times button').find((b) => b.text() === '09:00')!.trigger('click')
    expect(w.get('.tp-go').text()).toBe('Continue · 09:00–10:00, Fri 13 Nov')
    await w.get('.tp-go').trigger('click')
    await flushPromises()
    expect(router.currentRoute.value).toMatchObject({
      name: 'book',
      params: { roomId: '12' },
      query: { date: '2026-11-13', start: '09:00', end: '10:00' },
    })
  })

  it('marks a public holiday softly and keeps it bookable', async () => {
    const w = await open()
    const holiday = w.get('.tp-days button[data-day="2026-11-16"]')
    expect(holiday.classes()).toContain('holiday')
    expect(holiday.attributes('title')).toBe('Test holiday')
    await holiday.trigger('click')
    expect(times(w).length).toBeGreaterThan(0)
  })

  it('opens the week table for several days', async () => {
    const w = await open()
    await w.get('button.more').trigger('click')
    await flushPromises()
    expect(router.currentRoute.value.name).toBe('book')
    expect(router.currentRoute.value.query).toEqual({})
  })
})
