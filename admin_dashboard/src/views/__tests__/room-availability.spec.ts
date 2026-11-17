import { enableAutoUnmount, flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createMemoryHistory, createRouter, type Router } from 'vue-router'

import { NAV_GROUPS } from '../../layouts/nav'
import { useSessionStore } from '../../stores/session'
import { choosePicker, pickerOptions } from '../../test-utils/picker'
import { bookingDetail, bookingItem, building, roomItem } from '../../test-utils/staff'
import { useToast } from '../../composables/useToast'
import RoomAvailabilityView from '../RoomAvailabilityView.vue'

enableAutoUnmount(afterEach)

// Now: Wed 4 Nov 2026, 10:20 in Phnom Penh. Two Phnom Penh rooms and one in Siem Reap.
const ROOMS = [
  roomItem(12, 'Mekong Room', { start_time: '07:30', end_time: '18:00', building: building(1, 'Head office') }),
  roomItem(13, 'Board Room', { start_time: '08:00', end_time: '17:00', is_private: true, building: building(2, 'Annex') }),
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
const bodies: string[] = []
const DETAILS: Record<number, unknown> = {
  70: bookingDetail(bookingItem(70, 'Budget review', 'CONFIRMED', '2026-11-04', { room: { ...bookingItem(70, 'x', 'CONFIRMED', '2026-11-04').room, id: 12 } })),
  71: bookingDetail(bookingItem(71, 'Risk review', 'PENDING_PITIKA', '2026-11-04', { room: { ...bookingItem(71, 'x', 'PENDING_PITIKA', '2026-11-04').room, id: 13 } })),
}

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
  bodies.length = 0
  day = {
    12: [item(70, '09:00', '10:30', 'Budget review', 'CONFIRMED')],
    13: [item(71, '14:00', '16:00', 'Risk review', 'PENDING_PITIKA')],
  }
  vi.stubGlobal(
    'fetch',
    vi.fn<typeof fetch>(async (input, init) => {
      const url = new URL(String(input))
      calls.push(`${init?.method && init.method !== 'GET' ? `${init.method} ` : ''}${url.pathname}${url.search}`)
      if (init?.body) bodies.push(String(init.body))
      const one = /^\/api\/v1\/bookings\/(\d+)$/.exec(url.pathname)
      if (one && DETAILS[Number(one[1])]) return json(DETAILS[Number(one[1])])
      if (/^\/api\/v1\/pitika\/bookings\/71\/(approve|reject)$/.test(url.pathname)) return json({ ...(DETAILS[71] as object), status: 'CONFIRMED' })
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

  it('hover shows the title, times, booker and who it waits for', async () => {
    const { wrapper } = await mountAt('/room-availability')
    const block = wrapper.get('[data-booking="71"]')

    await block.trigger('mouseenter')
    const tip = () => document.body.querySelector('[role="tooltip"]')
    expect(tip()?.textContent).toContain('Risk review')
    expect(tip()?.textContent).toContain('14:00–16:00')
    expect(tip()?.textContent).toContain('Sok Dara')
    expect(tip()?.textContent).toContain('Waiting for Pitika')
    await block.trigger('mouseleave')
    expect(tip()).toBeNull()
    await block.trigger('focus')
    expect(tip()?.textContent).toContain('Risk review')
  })

  it('a waiting booking opens the To review panel and can be approved', async () => {
    const { wrapper, router } = await mountAt('/room-availability')
    await wrapper.get('[data-booking="71"]').trigger('click')
    await flushPromises()

    expect(router.currentRoute.value.query.booking).toBe('71')
    const panel = document.body.querySelector('.review-panel')?.closest('[role="dialog"]') as HTMLElement
    expect(panel.querySelector('h2')?.textContent).toBe('Risk review')
    ;[...panel.querySelectorAll('button')].find((b) => b.textContent?.trim() === 'Approve')!.click()
    await flushPromises()
    const dialog = document.body.querySelector('.action-dialog') as HTMLElement
    expect(dialog.textContent).toContain('Approve this booking?')
    ;(dialog.querySelector('button.confirm') as HTMLButtonElement).click()
    await flushPromises()

    expect(calls).toContain('POST /api/v1/pitika/bookings/71/approve')
    expect(bodies.at(-1)).toBe(JSON.stringify({ notes: null, version: 3 }))
    expect(useToast().toasts.value.map((t) => t.title)).toContain('NBC-26-71 approved')
    expect(document.body.querySelector('.action-dialog')).toBeNull()
    expect(router.currentRoute.value.query.booking).toBeUndefined()
    expect(calls.filter((c) => c.startsWith('/api/v1/room-schedule')).length).toBeGreaterThan(1)
  })

  it('reject needs a reason of at least 5 characters', async () => {
    const { wrapper } = await mountAt('/room-availability?booking=71')
    await flushPromises()
    const panel = document.body.querySelector('.review-panel')?.closest('[role="dialog"]') as HTMLElement
    ;[...panel.querySelectorAll('button')].find((b) => b.textContent?.trim() === 'Reject')!.click()
    await flushPromises()
    const dialog = () => document.body.querySelector('.action-dialog') as HTMLElement
    const confirm = () => dialog().querySelector('button.confirm') as HTMLButtonElement
    const box = dialog().querySelector('textarea')!
    box.value = 'Room'
    box.dispatchEvent(new Event('input'))
    await flushPromises()
    expect(confirm().disabled).toBe(true)
    box.value = 'Room closed'
    box.dispatchEvent(new Event('input'))
    await flushPromises()
    confirm().click()
    await flushPromises()

    expect(calls).toContain('POST /api/v1/pitika/bookings/71/reject')
    expect(bodies.at(-1)).toBe(JSON.stringify({ reason: 'Room closed', version: 3 }))
    expect(wrapper.exists()).toBe(true)
  })

  it('a booked booking opens the Bookings drawer, with no Approve', async () => {
    const { wrapper } = await mountAt('/room-availability')
    await wrapper.get('[data-booking="70"]').trigger('click')
    await flushPromises()

    const drawer = document.body.querySelector('[role="dialog"]') as HTMLElement
    expect(drawer.querySelector('h2')?.textContent).toBe('Budget review')
    expect(document.body.querySelector('.review-panel')).toBeNull()
    expect([...drawer.querySelectorAll('button')].some((b) => b.textContent?.trim() === 'Approve')).toBe(false)
  })

  it('a masked booking shows Private booking and does not open', async () => {
    day[13] = [item(0, '14:00', '16:00', 'Private booking', 'CONFIRMED', { booking_id: null, reference_code: null, requester_name: null, is_masked: true })]
    const { wrapper, router } = await mountAt('/room-availability')
    const block = wrapper.get('[data-room="13"] .block')

    expect(block.text()).toContain('Private booking')
    expect(block.classes()).toContain('masked')
    expect(block.attributes('aria-disabled')).toBe('true')
    await block.trigger('mouseenter')
    expect(document.body.querySelector('[role="tooltip"]')?.textContent).not.toContain('Sok Dara')
    await block.trigger('click')
    expect(router.currentRoute.value.query.booking).toBeUndefined()
  })

  it("greys out each room's own closed hours", async () => {
    const { wrapper } = await mountAt('/room-availability')

    // Board Room opens 08:00–17:00: closed 07:00–08:00 and 17:00–18:00. Mekong Room 07:30–18:00.
    const closed = (id: number) => wrapper.findAll(`[data-room="${id}"] .closed`).map((c) => c.attributes('style'))
    expect(closed(13)).toEqual(['left: 0%; width: 9.090909090909092%;', 'left: 90.9090909090909%; width: 9.090909090909093%;'])
    expect(closed(12)).toHaveLength(1)
  })

  it('a free room says Free for the rest of the day today, over the time left', async () => {
    day[13] = []
    const { wrapper } = await mountAt('/room-availability')
    expect(wrapper.get('[data-room="13"] .free-label').text()).toBe('Free for the rest of the day')
  })

  it('a free room says Free all day on another day', async () => {
    day[13] = []
    const { wrapper } = await mountAt('/room-availability?date=2026-11-05')
    expect(wrapper.get('[data-room="13"] .free-label').text()).toBe('Free all day')
  })

  it('after closing time: Closed for today, and the line says every room is closed', async () => {
    vi.setSystemTime(new Date('2026-11-04T11:30:00Z')) // 18:30 in Phnom Penh
    day[12] = []
    day[13] = []
    const { wrapper } = await mountAt('/room-availability')

    expect(wrapper.findAll('.free-label').map((l) => l.text())).toEqual(['Closed for today', 'Closed for today'])
    expect(wrapper.get('.result').text()).toBe('All rooms are closed now')
  })

  it('today, Free at offers only Now and the times still to come', async () => {
    await mountAt('/room-availability')
    const options = await pickerOptions('free-at')
    expect(options.slice(0, 3)).toEqual(['Any time', 'Now', '10:30'])
    expect(options).not.toContain('10:00')
  })

  it('keeps a picked Free at time after the clock passes it', async () => {
    vi.useFakeTimers({ toFake: ['Date', 'setInterval', 'clearInterval'] })
    vi.setSystemTime(new Date('2026-11-04T03:20:00Z')) // 10:20
    await mountAt('/room-availability')
    await choosePicker('free-at', '10:30')

    vi.setSystemTime(new Date('2026-11-04T03:40:00Z')) // 10:40
    vi.advanceTimersByTime(20_000)
    await flushPromises()
    expect(pickerText('free-at')).toBe('10:30')
  })

  it('is in the Daily group of the sidebar after Food list, for Admin and Pitika', () => {
    const daily = NAV_GROUPS.find((g) => g.title === 'Daily')!
    const routes = daily.items.map((i) => i.route)
    expect(routes.indexOf('room-availability')).toBe(routes.indexOf('food-list') + 1)
    const entry = daily.items.find((i) => i.route === 'room-availability')!
    expect([entry.label, entry.roles]).toEqual(['Room availability', ['ADMIN', 'PITIKA']])
  })
})
