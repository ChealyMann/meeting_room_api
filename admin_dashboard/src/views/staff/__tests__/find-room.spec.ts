import { enableAutoUnmount, flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createMemoryHistory, createRouter, type Router } from 'vue-router'

import { useSessionStore } from '../../../stores/session'
import { choosePicker, pickerOptions } from '../../../test-utils/picker'
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
const place = (id: number, name: string, office: number) => ({ ...building(id, name), name_kh: '', location_id: office, is_active: true })
const kit = (id: number, name: string) => ({ id, name, icon: null, sort_order: id, is_active: true })
let offices: Array<{ id: number; name_en: string; name_kh?: string; province?: { code: string; name_en: string; name_kh: string } }> = []
let kits: ReturnType<typeof kit>[] = []
const PP = { code: 'PHNOM_PENH', name_en: 'Phnom Penh', name_kh: 'ភ្នំពេញ' }
const KAMPOT = { code: 'KAMPOT', name_en: 'Kampot', name_kh: 'កំពត' }
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
  offices = [{ id: 3, name_en: 'Head Office' }]
  kits = [kit(4, 'Projector'), kit(7, 'Video call')]
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
        return json({ items: [place(1, 'Head office', 3), place(2, 'Annex', 3)], page: 1, size: 100, total: 2 })
      if (url.pathname === '/api/v1/locations')
        return json({ items: offices.map((o) => ({ ...o, is_active: true })), page: 1, size: 100, total: offices.length })
      if (url.pathname === '/api/v1/equipment')
        return json({ items: kits, page: 1, size: 100, total: kits.length })
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
  const wrapper = mount(FindRoomView, { global: { plugins: [router] }, attachTo: document.body })
  await flushPromises()
  return wrapper
}
const names = (w: Awaited<ReturnType<typeof open>>) => w.findAll('.room-card h2').map((h) => h.text())
const roomCalls = () => calls.filter((c) => c.startsWith('/api/v1/rooms?')).map((c) => Object.fromEntries(new URL(c, 'http://x').searchParams))
const dayCalls = () => calls.filter((c) => c.startsWith('/api/v1/room-schedule'))
const lineOf = (w: Awaited<ReturnType<typeof open>>, name: string) =>
  w.findAll('.room-card').find((c) => c.find('h2').text() === name)!.find('.now').text()
async function openChip(w: Awaited<ReturnType<typeof open>>, name: string) {
  await w.get(`.chip-${name} .f-open`).trigger('click')
}
/** The time uses the app's own picker, never the browser's list (owner, 19 Nov 2026). */
async function pickTime(_w: Awaited<ReturnType<typeof open>>, from: string, to?: string) {
  await choosePicker('when-from', from)
  if (to) await choosePicker('when-to', to)
  await flushPromises()
}
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
    // The line under the title says what the list shows; the date is in the top bar (owner, 20 Nov 2026).
    expect(w.get('.count-line').text()).toBe('3 rooms') // no date, also on a phone (owner, 20 Nov 2026)
  })

  it('says until when each room is free or in use today', async () => {
    const w = await open()
    expect(lineOf(w, 'Mekong Room')).toBe('Free until 14:00')
    expect(lineOf(w, 'Bassac Room')).toBe('In use until 11:00')
    expect(lineOf(w, 'Governor Room')).toBe('Free all day')
  })

  it('draws a green border on a free room and a red one on a room in use', async () => {
    const w = await open()
    const card = (name: string) => w.findAll('.room-card').find((c) => c.find('h2').text() === name)!.classes()
    expect(card('Mekong Room')).toContain('ok')
    expect(card('Bassac Room')).toContain('alert')
    expect(card('Governor Room')).toContain('ok')
  })

  it('shows seats and floor, and keeps the whole description in the title of its one line', async () => {
    const w = await open()
    const card = w.findAll('.room-card').find((c) => c.find('h2').text() === 'Mekong Room')!
    expect(card.findAll('.facts > span').map((s) => s.text())).toEqual(['14 seats', 'Floor 2'])
    expect(card.find('.desc').text()).toBe('4K screen / VC')
    expect(card.find('.desc').attributes('title')).toBe('4K screen / VC')
  })

  it('shows no description line when the room has none', async () => {
    allRooms = [roomItem(1, 'Mekong Room', { short_desc: null })]
    const w = await open()
    expect(w.find('.room-card .desc').exists()).toBe(false)
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
    await openChip(w, 'place')
    await w.get('.chip-place [data-building="2"]').trigger('click')
    await flushPromises()
    expect(roomCalls().at(-1)).toMatchObject({ building_id: '2', page: '1' })
    expect(names(w)).toEqual(['Bassac Room'])
    await w.get('.chip-place [data-office="all"]').trigger('click') // "All offices" clears the building too
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

describe('Find a room office list (look A "One search list", owner pick 20 Nov 2026)', () => {
  const rows = (w: Awaited<ReturnType<typeof open>>) =>
    w.findAll('.chip-place .pl-row').map((r) => r.attributes('data-office') ? `office ${r.attributes('data-office')}` : `building ${r.attributes('data-building')}`)

  it('lists each office with its buildings under it, English over Khmer, and one click picks', async () => {
    offices = [
      { id: 3, name_en: 'Head Office', name_kh: 'ទីស្នាក់ការកណ្តាល' },
      { id: 5, name_en: 'Sensok Branch', name_kh: 'សាខាសែនសុខ' },
    ]
    const w = await open()
    await openChip(w, 'place')
    expect(rows(w)).toEqual(['office all', 'office 3', 'building 1', 'building 2', 'office 5'])
    expect(w.get('.chip-place [data-office="3"]').text()).toBe('Head Officeទីស្នាក់ការកណ្តាល')
    expect(w.get('.chip-place [data-building="2"]').classes()).toContain('sub')
    // Tree lines (owner pick, 20 Nov 2026): an office's buildings hang from one line under it.
    expect(w.findAll('.chip-place .pl-tree').map((t) => t.findAll('[data-building]').length)).toEqual([2])
    await w.get('.chip-place [data-building="2"]').trigger('click')
    await flushPromises()
    // A building picks its office too, and the chip names both.
    expect(roomCalls().at(-1)).toMatchObject({ location_id: '3', building_id: '2' })
    expect(w.get('.chip-place .f-label').text()).toBe('Head Office · Annex')
  })

  it('finds an office or a building by English or Khmer', async () => {
    offices = [
      { id: 3, name_en: 'Head Office', name_kh: 'ទីស្នាក់ការកណ្តាល' },
      { id: 5, name_en: 'Sensok Branch', name_kh: 'សាខាសែនសុខ' },
    ]
    const w = await open()
    await openChip(w, 'place')
    await w.get('.chip-place .pl-search input').setValue('annex')
    expect(rows(w)).toEqual(['office 3', 'building 2'])
    await w.get('.chip-place .pl-search input').setValue('សែនសុខ')
    expect(rows(w)).toEqual(['office 5'])
    await w.get('.chip-place .pl-search input').setValue('zzz')
    expect(w.get('.chip-place .pl-none').text()).toBe('No office or building matches "zzz"')
  })

  it('puts the offices in the user\'s province first', async () => {
    offices = [
      { id: 5, name_en: 'Kampot Branch', province: KAMPOT },
      { id: 3, name_en: 'Head Office', province: PP },
    ]
    useSessionStore().user = { province: PP, roles: [] } as never
    const w = await open()
    await openChip(w, 'place')
    expect(w.find('.chip-place .pl-group').exists()).toBe(false) // no headings (owner, 20 Nov 2026)
    expect(rows(w)).toEqual(['office all', 'office 3', 'building 1', 'building 2', 'office 5'])
  })
})

describe('Find a room equipment list', () => {
  it('searches a long list, shows what is picked as tags, and clears', async () => {
    kits = ['Projector', 'Video call', 'Microphone', 'Speaker', 'Whiteboard', 'Wi-Fi', 'Flip chart'].map((n, i) => kit(i + 1, n))
    const w = await open()
    await openChip(w, 'equipment')
    await w.get('.chip-equipment .pl-search input').setValue('video')
    expect(w.findAll('.chip-equipment [data-equipment]').map((c) => c.attributes('data-equipment'))).toEqual(['2'])
    await w.get('.chip-equipment [data-equipment="2"]').setValue(true)
    await flushPromises()
    expect(w.findAll('.chip-equipment .eq-tag').map((t) => t.text())).toEqual(['Video call'])
    await w.get('.chip-equipment .eq-tag button').trigger('click')
    await flushPromises()
    expect(roomCalls().at(-1)!.equipment_ids).toBeUndefined()
    await w.get('.chip-equipment .pl-search input').setValue('')
    await w.get('.chip-equipment [data-equipment="1"]').setValue(true)
    await w.get('.chip-equipment .eq-clear').trigger('click')
    await flushPromises()
    expect(roomCalls().at(-1)!.equipment_ids).toBeUndefined()
  })

  it('has no search box for a short list', async () => {
    const w = await open()
    await openChip(w, 'equipment')
    expect(w.find('.chip-equipment .pl-search').exists()).toBe(false)
  })
})

describe('Find a room filter chips', () => {
  it('asks for rooms free at a time on one day, and Book carries that time', async () => {
    const w = await open()
    await openChip(w, 'when')
    await w.get('.chip-when [data-day="2026-11-16"]').trigger('click')
    await pickTime(w, '09:00', '10:00')
    expect(roomCalls().at(-1)).toMatchObject({ free_dates: '2026-11-16', free_from: '09:00', free_to: '10:00' })
    expect(w.get('.chip-when .f-label').text()).toBe('Mon 16 Nov, 09:00–10:00')
    expect(lineOf(w, 'Mekong Room')).toBe('Free 09:00–10:00')
    expect(w.get('.count-line').text()).toBe('3 rooms free on Mon 16 Nov, 09:00–10:00')
    await w.get('[aria-label="Book Mekong Room"]').trigger('click')
    await flushPromises()
    expect(router.currentRoute.value.query).toEqual({ date: '2026-11-16', start: '09:00', end: '10:00' })
  })

  it('takes a range of working days, day to day, with one time for all', async () => {
    const w = await open()
    await openChip(w, 'when')
    await w.get('.chip-when [data-mode="range"]').trigger('click')
    await w.get('.chip-when [data-day="2026-11-16"]').trigger('click')
    expect(w.text()).toContain('Now pick the last day')
    await w.get('.chip-when [data-day="2026-11-18"]').trigger('click')
    await w.findAll('.chip-when .quick button').find((b) => b.text() === 'Morning')!.trigger('click')
    await flushPromises()
    expect(roomCalls().at(-1)).toMatchObject({ free_dates: '2026-11-16,2026-11-17,2026-11-18', free_from: '08:00', free_to: '12:00' })
    expect(w.get('.count-line').text()).toBe('3 rooms free on all 3 days, Mon 16 – Wed 18 Nov, 08:00–12:00')
    expect(w.get('.chip-when .f-label').text()).toBe('Mon 16 – Wed 18 Nov (3 days), 08:00–12:00')
    expect(lineOf(w, 'Bassac Room')).toBe('Free all 3 days')
    await w.get('[aria-label="Book Bassac Room"]').trigger('click')
    await flushPromises()
    expect(router.currentRoute.value.query).toEqual({ dates: '2026-11-16,2026-11-17,2026-11-18', start: '08:00', end: '12:00' })
  })

  it('offers 14 days (weekends too) in week rows, and no start time that has passed today', async () => {
    const w = await open()
    await openChip(w, 'when')
    const days = w.findAll('.chip-when .day').map((d) => d.attributes('data-day'))
    expect(days).toHaveLength(14)
    expect(days[0]).toBe('2026-11-12')
    expect(days.at(-1)).toBe('2026-11-25')
    expect(days).toContain('2026-11-14') // Saturday
    expect(days).toContain('2026-11-15') // Sunday
    expect(w.findAll('.chip-when .row')).toHaveLength(3) // Thu–Sun, Mon–Sun, Mon–Wed
    // Seven columns, Mon to Sun: the first week starts under its own weekday (Thursday = 4).
    expect(w.get('.chip-when .day').attributes('style')).toContain('grid-column-start: 4')
    expect(w.get('.chip-when [data-day="2026-11-16"]').attributes('style')).toBeUndefined()
    expect(w.find('.chip-when select').exists()).toBe(false) // no browser list
    const starts = await pickerOptions('when-from')
    expect(starts.slice(0, 2)).toEqual(['Any time', '10:30']) // it is 10:00
    await w.get('.chip-when [data-day="2026-11-13"]').trigger('click')
    expect((await pickerOptions('when-from'))[1]).toBe('07:00')
  })

  it("shows another day with no time from that day's bookings", async () => {
    const w = await open()
    await openChip(w, 'when')
    await w.get('.chip-when [data-day="2026-11-13"]').trigger('click')
    await flushPromises()
    expect(dayCalls().at(-1)).toContain('date=2026-11-13')
    expect(roomCalls().at(-1)!.free_dates).toBeUndefined()
  })

  it('filters by people, equipment and office on the server', async () => {
    offices = [
      { id: 3, name_en: 'Head Office' },
      { id: 5, name_en: 'Sensok Branch' },
    ]
    const w = await open()
    await openChip(w, 'people')
    await w.get('.chip-people [data-people="12"]').trigger('click')
    await flushPromises()
    expect(roomCalls().at(-1)).toMatchObject({ min_capacity: '12' })
    expect(w.get('.chip-people .f-label').text()).toBe('12+ people')
    await openChip(w, 'equipment')
    await w.get('.chip-equipment [data-equipment="4"]').setValue(true)
    await w.get('.chip-equipment [data-equipment="7"]').setValue(true)
    await flushPromises()
    expect(roomCalls().at(-1)).toMatchObject({ equipment_ids: '4,7' })
    expect(w.get('.chip-equipment .f-label').text()).toBe('Projector, Video call')
    await openChip(w, 'place')
    await w.get('.chip-place [data-office="5"]').trigger('click')
    await flushPromises()
    expect(roomCalls().at(-1)).toMatchObject({ location_id: '5' })
    expect(roomCalls().at(-1)!.building_id).toBeUndefined()
  })

  it('clears one chip with its ×, and every filter with Clear filters', async () => {
    const w = await open()
    await openChip(w, 'people')
    await w.get('.chip-people [data-people="20"]').trigger('click')
    await flushPromises()
    await w.get('.chip-people .f-clear').trigger('click')
    await flushPromises()
    expect(roomCalls().at(-1)!.min_capacity).toBeUndefined()
    await openChip(w, 'people')
    await w.get('.chip-people [data-people="20"]').trigger('click')
    await openChip(w, 'when')
    await pickTime(w, '11:00', '12:00')
    await w.get('button.clear-all').trigger('click')
    await flushPromises()
    expect(roomCalls().at(-1)).toEqual({ is_bookable: 'true', page: '1', size: '24' })
    expect(w.find('button.clear-all').exists()).toBe(false)
  })

  it('says no room is free then, with a way out', async () => {
    allRooms = []
    const w = await open()
    await openChip(w, 'when')
    await pickTime(w, '11:00', '12:00')
    expect(w.text()).toContain('No room is free then')
    expect(w.find('button.clear').exists()).toBe(true)
  })

  it('hides the office chip with one office and one building, and equipment when there is none', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn<typeof fetch>(async (input) => {
        const url = new URL(String(input))
        if (url.pathname === '/api/v1/buildings') return json({ items: [place(1, 'Head office', 3)], page: 1, size: 100, total: 1 })
        if (url.pathname === '/api/v1/locations') return json({ items: [{ id: 3, name_en: 'HQ', is_active: true }], page: 1, size: 100, total: 1 })
        return json({ items: [], page: 1, size: 100, total: 0 })
      }),
    )
    const w = await open()
    expect(w.find('.chip-place').exists()).toBe(false)
    expect(w.find('.chip-equipment').exists()).toBe(false)
  })
})
