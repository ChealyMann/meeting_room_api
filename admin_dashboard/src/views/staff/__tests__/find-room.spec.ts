import { enableAutoUnmount, flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createMemoryHistory, createRouter, type Router } from 'vue-router'

import { useSessionStore } from '../../../stores/session'
import { building, roomItem } from '../../../test-utils/staff'
import FindRoomView from '../FindRoomView.vue'

enableAutoUnmount(afterEach)

const THREE = [
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
let allRooms: ReturnType<typeof roomItem>[]
let room3: unknown[] = []

function json(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } })
}

// jsdom has no IntersectionObserver: this one lets a test say "the end of the list is in view".
let reachEnd: (() => void) | null = null
class FakeObserver {
  constructor(callback: (entries: Array<{ isIntersecting: boolean }>) => void) {
    reachEnd = () => callback([{ isIntersecting: true }])
  }
  observe() {}
  unobserve() {}
  disconnect() {}
}

let router: Router
beforeEach(async () => {
  // Thursday 12 Nov 2026, 10:00 in Phnom Penh
  vi.useFakeTimers({ toFake: ['Date'] })
  vi.setSystemTime(new Date('2026-11-12T03:00:00Z'))
  setActivePinia(createPinia())
  useSessionStore().accessToken = 'A1'
  calls.length = 0
  allRooms = THREE
  room3 = []
  reachEnd = null
  vi.stubGlobal('IntersectionObserver', FakeObserver)
  vi.stubGlobal(
    'fetch',
    vi.fn<typeof fetch>(async (input) => {
      const url = new URL(String(input))
      calls.push(url.pathname + url.search)
      const p = url.searchParams
      if (url.pathname === '/api/v1/rooms') {
        // The server does the search and the filters, and pages the answer.
        const search = (p.get('search') ?? '').toLowerCase()
        const found = allRooms.filter(
          (r) =>
            (!search || r.name_en.toLowerCase().includes(search)) &&
            (!p.has('is_private') || String(r.is_private) === p.get('is_private')) &&
            (!p.has('building_id') || String(r.building.id) === p.get('building_id')),
        )
        const page = Number(p.get('page'))
        const size = Number(p.get('size'))
        return json({ items: found.slice((page - 1) * size, page * size), page, size, total: found.length })
      }
      if (url.pathname === '/api/v1/buildings')
        return json({ items: [building(1, 'Head office'), building(2, 'Annex')], page: 1, size: 100, total: 2 })
      if (url.pathname === '/api/v1/room-schedule') {
        const ids = (p.get('room_ids') ?? '').split(',').map(Number)
        const of = (id: number) => (id === 1 ? [busy('14:00', '15:00')] : id === 2 ? [busy('09:30', '11:00')] : id === 3 ? room3 : [])
        return json({ items: ids.map((id) => ({ room_id: id, items: of(id) })), total: ids.length })
      }
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
const roomCalls = () => calls.filter((c) => c.startsWith('/api/v1/rooms?')).map((c) => Object.fromEntries(new URL(c, 'http://x').searchParams))
const dayCalls = () => calls.filter((c) => c.startsWith('/api/v1/room-schedule'))
/** Typing waits 250 ms before it asks the server. */
async function search(w: Awaited<ReturnType<typeof open>>, text: string) {
  vi.useFakeTimers({ toFake: ['Date', 'setTimeout', 'clearTimeout'] })
  await w.get('input[type="search"]').setValue(text)
  vi.advanceTimersByTime(250)
  await flushPromises()
}

describe('Find a room', () => {
  it('loads the first 24 bookable rooms and their day in one request', async () => {
    const w = await open()
    expect(names(w)).toEqual(['Mekong Room', 'Bassac Room', 'Governor Room'])
    expect(roomCalls()).toEqual([{ is_bookable: 'true', page: '1', size: '24' }])
    expect(dayCalls()).toEqual(['/api/v1/room-schedule?date=2026-11-12&room_ids=1%2C2%2C3'])
    expect(w.text()).toContain('3 rooms')
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

  it('asks the server to search, and to filter by building and type', async () => {
    const w = await open()
    await search(w, 'mekong')
    expect(roomCalls().at(-1)).toEqual({ is_bookable: 'true', search: 'mekong', page: '1', size: '24' })
    expect(names(w)).toEqual(['Mekong Room'])
    await search(w, '')
    await w.get('[role="radio"][data-building="2"]').trigger('click')
    await flushPromises()
    expect(roomCalls().at(-1)).toMatchObject({ building_id: '2', page: '1' })
    expect(names(w)).toEqual(['Bassac Room'])
    await w.get('[role="radio"][data-building="all"]').trigger('click')
    await w.get('[role="radio"][data-kind="private"]').trigger('click')
    await flushPromises()
    expect(roomCalls().at(-1)).toMatchObject({ is_private: 'true' })
    expect(names(w)).toEqual(['Governor Room'])
  })

  it('says so when nothing matches, and Clear filters brings every room back', async () => {
    const w = await open()
    await search(w, 'zzz')
    expect(w.text()).toContain('No room matches')
    await w.get('button.clear').trigger('click')
    await flushPromises()
    expect(names(w)).toHaveLength(3)
  })

  it('loads the next 24 rooms when the end of the list comes into view, and stops at the last', async () => {
    allRooms = Array.from({ length: 30 }, (_, i) => roomItem(i + 1, `Room ${i + 1}`))
    const w = await open()
    expect(names(w)).toHaveLength(24)
    expect(w.text()).toContain('30 rooms')
    reachEnd!()
    await flushPromises()
    expect(names(w)).toHaveLength(30)
    expect(names(w).at(-1)).toBe('Room 30')
    expect(roomCalls().map((c) => c.page)).toEqual(['1', '2'])
    expect(dayCalls().at(-1)).toBe('/api/v1/room-schedule?date=2026-11-12&room_ids=25%2C26%2C27%2C28%2C29%2C30')
    reachEnd!()
    await flushPromises()
    expect(roomCalls()).toHaveLength(2)
    expect(w.find('button.more').exists()).toBe(false)
  })

  it('keeps loading while the end of the list stays in view (a tall screen)', async () => {
    allRooms = Array.from({ length: 60 }, (_, i) => roomItem(i + 1, `Room ${i + 1}`))
    // Every box is 600 px tall at the top of the page: the end of the list is always in view.
    vi.spyOn(HTMLElement.prototype, 'clientHeight', 'get').mockReturnValue(600)
    vi.spyOn(HTMLElement.prototype, 'getBoundingClientRect').mockReturnValue({ top: 0, bottom: 600 } as DOMRect)
    const w = await open()
    reachEnd!() // the browser says so once; after that it says nothing while the end stays in view
    await flushPromises()
    await flushPromises()
    expect(names(w)).toHaveLength(60)
    expect(roomCalls().map((c) => c.page)).toEqual(['1', '2', '3'])
    vi.restoreAllMocks()
  })

  it('has a Show more rooms button too, for the keyboard', async () => {
    allRooms = Array.from({ length: 30 }, (_, i) => roomItem(i + 1, `Room ${i + 1}`))
    const w = await open()
    await w.get('button.more').trigger('click')
    await flushPromises()
    expect(names(w)).toHaveLength(30)
  })

  it('shows a new booking with no click (quiet refresh)', async () => {
    vi.useFakeTimers({ toFake: ['Date', 'setInterval', 'clearInterval'] })
    vi.setSystemTime(new Date('2026-11-12T03:00:00Z'))
    const w = await open()
    const line = () => w.findAll('.room-card').find((c) => c.find('h2').text() === 'Governor Room')!.find('.now').text()
    expect(line()).toBe('Free all day')
    room3 = [busy('09:30', '11:00')]
    vi.advanceTimersByTime(15_000)
    await flushPromises()
    expect(line()).toBe('In use until 11:00')
    expect(names(w)).toHaveLength(3)
  })
})
