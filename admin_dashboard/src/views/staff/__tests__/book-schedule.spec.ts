import { enableAutoUnmount, flushPromises, mount, type VueWrapper } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createMemoryHistory, createRouter, type Router } from 'vue-router'

import { useSessionStore } from '../../../stores/session'
import { bookingStubs, roomDetail, scheduleItem } from '../../../test-utils/staff'
import BookView from '../BookView.vue'

enableAutoUnmount(afterEach)

let router: Router
beforeEach(() => {
  vi.useFakeTimers({ toFake: ['Date'] })
  vi.setSystemTime(new Date('2026-11-12T03:00:00Z')) // Thu 12 Nov 2026, 10:00 in Phnom Penh
  setActivePinia(createPinia())
  useSessionStore().accessToken = 'A1'
  vi.stubGlobal('fetch', bookingStubs(roomDetail(12, 'Mekong Room')).fetch)
  router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/book/:roomId', name: 'book', component: BookView },
      { path: '/find-room/:roomId', name: 'staff-room', component: { template: '<div />' } },
    ],
  })
})
afterEach(() => {
  vi.useRealTimers()
  vi.unstubAllGlobals()
})

async function open(query = '') {
  await router.push(`/book/12${query}`)
  const wrapper = mount(BookView, { global: { plugins: [router] }, attachTo: document.body })
  await flushPromises()
  return wrapper
}
const cell = (w: VueWrapper, day: string, time: string) => {
  const [h, m] = time.split(':').map(Number)
  const index = (h! * 60 + m! - 480) / 30
  return w.get(`.tbl-col[data-day="${day}"]`).findAll('.cell')[index]!
}
/** A left mouse press (jsdom has no PointerEvent, so a MouseEvent carries pointerType). */
async function press(c: ReturnType<typeof cell>) {
  const e = new MouseEvent('pointerdown', { button: 0, bubbles: true })
  Object.defineProperty(e, 'pointerType', { value: 'mouse' })
  c.element.dispatchEvent(e)
  await flushPromises()
}
async function click(w: VueWrapper, day: string, time: string) {
  const c = cell(w, day, time)
  await press(c)
  window.dispatchEvent(new Event('pointerup'))
  await c.trigger('click')
  await flushPromises()
}
const sessions = (w: VueWrapper) => w.findAll('.bf-sess li').map((li) => li.text().replace(/\s+/g, ' '))

describe('Booking step 1: the week table', () => {
  it('shows the next 5 working days from today', async () => {
    const w = await open()
    expect(w.findAll('.tbl-col').map((c) => c.attributes('data-day'))).toEqual([
      '2026-11-12',
      '2026-11-13',
      '2026-11-16',
      '2026-11-17',
      '2026-11-18',
    ])
  })

  it('starts with the time picked on the room page', async () => {
    const w = await open('?date=2026-11-13&start=09:00&end=10:00')
    expect(sessions(w)).toEqual(['Tomorrow 09:00–10:00 · 1 h'])
  })

  it('adds 1 hour with a click, and joins picks that touch', async () => {
    const w = await open()
    await click(w, '2026-11-16', '09:00')
    expect(sessions(w)).toEqual(['Mon 16 Nov 09:00–10:00 · 1 h'])
    await click(w, '2026-11-16', '10:00')
    expect(sessions(w)).toEqual(['Mon 16 Nov 09:00–11:00 · 2 h'])
  })

  it('picks any length by pressing and dragging down', async () => {
    const w = await open()
    const first = cell(w, '2026-11-18', '13:00')
    await press(first)
    for (const t of ['13:30', '14:00', '14:30', '15:00', '15:30']) await cell(w, '2026-11-18', t).trigger('pointerenter')
    window.dispatchEvent(new Event('pointerup'))
    await flushPromises()
    expect(sessions(w)).toEqual(['Wed 18 Nov 13:00–16:00 · 3 h'])
  })

  it('removes a picked block when clicked again, not in the click that added it', async () => {
    const w = await open()
    await click(w, '2026-11-16', '09:00')
    expect(sessions(w)).toHaveLength(1)
    await cell(w, '2026-11-16', '09:00').trigger('click')
    await flushPromises()
    expect(sessions(w)).toEqual([])
  })

  it('shows a private booking as Busy with no title, and cannot pick it', async () => {
    const w = await open()
    const busy = cell(w, '2026-11-13', '10:00')
    expect(busy.attributes('disabled')).toBeDefined()
    expect(w.get('.tbl-col[data-day="2026-11-13"]').text()).toContain('Busy')
    expect(w.text()).not.toContain('Reserved (Private Session)')
  })

  it('marks a public holiday softly and keeps it bookable', async () => {
    const w = await open()
    const head = w.get('.tbl-day[data-day="2026-11-17"]')
    expect(head.text()).toContain('Holiday')
    expect(head.attributes('title')).toBe('Test holiday')
    expect(cell(w, '2026-11-17', '09:00').attributes('disabled')).toBeUndefined()
    await click(w, '2026-11-17', '09:00')
    expect(w.get('.bf-side').text()).toContain('Tue 17 Nov is Test holiday')
  })

  it('says No time left on today when the rest of the day is busy, not Full', async () => {
    vi.stubGlobal('fetch', bookingStubs(roomDetail(12, 'Mekong Room'), { schedule: [scheduleItem('2026-11-12', '10:00', '17:00')] }).fetch)
    const w = await open()
    expect(w.get('.tbl-day[data-day="2026-11-12"]').text()).toContain('No time left')
    expect(w.get('.tbl-day[data-day="2026-11-12"]').text()).not.toContain('Full')
  })

  it('needs at least one time before going on', async () => {
    const w = await open()
    await w.get('button.next').trigger('click')
    expect(w.text()).toContain('Pick at least one time in the table.')
    expect(w.get('.bf-steps button.on').text()).toContain('Schedule')
  })
})
