import { enableAutoUnmount, flushPromises, mount, type VueWrapper } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createMemoryHistory, createRouter, type Router } from 'vue-router'

import { useConfirm } from '../../../composables/useConfirm'
import { useSessionStore } from '../../../stores/session'
import { bookingDetail, bookingItem } from '../../../test-utils/staff'
import MyBookingsView from '../MyBookingsView.vue'

enableAutoUnmount(afterEach)

const SOON = bookingItem(7, 'Budget review', 'CONFIRMED', '2026-11-13')
const WAITING = bookingItem(8, 'Team sync', 'PENDING_PITIKA', '2026-11-16')
const GONE = bookingItem(9, 'Old plan', 'CANCELLED', '2026-11-03')
const DONE = bookingItem(10, 'Kick-off', 'COMPLETED', '2026-11-02')

let router: Router
let calls: string[]
let bodies: Record<string, unknown>
let cancelAnswer: () => [unknown, number]
let mine: unknown[]
let detail8: unknown
let mineFails = false

function stub() {
  calls = []
  bodies = {}
  const json = (body: unknown, status = 200) =>
    new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } })
  return async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = new URL(String(input))
    const key = `${init?.method ?? 'GET'} ${url.pathname}`
    calls.push(key)
    if (init?.body) bodies[key] = JSON.parse(String(init.body))
    if (key === 'GET /api/v1/bookings/mine')
      return mineFails ? json({ error: { code: 'X', message: 'Down.' } }, 503) : json({ items: mine, page: 1, size: 100, total: mine.length })
    if (key === 'GET /api/v1/rooms') return json({ items: [], page: 1, size: 100, total: 0 })
    if (key === 'GET /api/v1/bookings/7') return json(bookingDetail(SOON))
    if (key === 'GET /api/v1/bookings/8') return json(detail8)
    if (key === 'GET /api/v1/bookings/7/door-pass') return json({ passcode: '482913', expires_at: '2026-11-13T03:00:00Z', expired: false })
    if (key === 'POST /api/v1/bookings/7/cancel') {
      const [body, status] = cancelAnswer()
      return json(body, status)
    }
    return json({}, 404)
  }
}

beforeEach(() => {
  vi.useFakeTimers({ toFake: ['Date'] })
  vi.setSystemTime(new Date('2026-11-12T03:00:00Z'))
  setActivePinia(createPinia())
  useSessionStore().accessToken = 'A1'
  mine = [SOON, WAITING, GONE, DONE]
  mineFails = false
  detail8 = bookingDetail(WAITING)
  cancelAnswer = () => [bookingDetail({ ...SOON, status: 'CANCELLED', display_status: 'CANCELLED', version: 4 }), 200]
  vi.stubGlobal('fetch', stub())
  router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/my-bookings', name: 'my-bookings', component: MyBookingsView },
      { path: '/find-room', name: 'find-room', component: { template: '<div />' } },
    ],
  })
})
afterEach(() => {
  vi.useRealTimers()
  vi.unstubAllGlobals()
  document.body.innerHTML = ''
})

async function open(query = '') {
  await router.push(`/my-bookings${query}`)
  const w = mount(MyBookingsView, { global: { plugins: [router] }, attachTo: document.body })
  await flushPromises()
  return w
}
const titles = (w: VueWrapper) => w.findAll('.bk-card h2').map((h) => h.text())
const panel = () => document.body.querySelector('.side-panel, [role="dialog"]')
async function openCard(w: VueWrapper, title: string) {
  await w.findAll('.bk-card').find((c) => c.get('h2').text() === title)!.trigger('click')
  await flushPromises()
}
function buttonIn(root: Element, text: string) {
  return [...root.querySelectorAll('button')].find((b) => b.textContent?.trim() === text) as HTMLButtonElement | undefined
}

describe('My bookings', () => {
  it('lists what is coming up, with counts on the tabs', async () => {
    const w = await open()
    expect(titles(w)).toEqual(['Budget review', 'Team sync'])
    const tabs = w.findAll('[role="tab"]').map((t) => t.text().replace(/\s+/g, ' '))
    expect(tabs).toEqual(['Coming up 2', 'Past & cancelled 2'])
  })

  it('shows Door pass on a confirmed booking only', async () => {
    const w = await open()
    const cards = w.findAll('.bk-card')
    expect(cards[0]!.text()).toContain('Door pass')
    expect(cards[1]!.text()).not.toContain('Door pass')
  })

  it('lists cancelled and completed under Past & cancelled', async () => {
    const w = await open()
    await w.findAll('[role="tab"]')[1]!.trigger('click')
    expect(titles(w)).toEqual(['Old plan', 'Kick-off'])
  })

  it('opens the details from ?booking=', async () => {
    await open('?booking=7')
    expect(calls).toContain('GET /api/v1/bookings/7')
    expect(panel()?.textContent).toContain('Budget review')
    expect(panel()?.textContent).toContain('NBC-26-7')
  })

  it('cancels with the version it read, and the card moves to Past', async () => {
    const w = await open()
    await openCard(w, 'Budget review')
    buttonIn(panel()!, 'Cancel booking')!.click()
    await flushPromises()
    expect(useConfirm().current.value?.title).toBeTruthy()
    useConfirm().answer(true)
    await flushPromises()
    expect(bodies['POST /api/v1/bookings/7/cancel']).toEqual({ version: 3 })
    expect(titles(w)).toEqual(['Team sync'])
    await w.findAll('[role="tab"]')[1]!.trigger('click')
    expect(titles(w)).toContain('Budget review')
  })

  it('says the booking changed when someone saved first', async () => {
    cancelAnswer = () => [{ error: { code: 'STALE_VERSION', message: 'Stale.' } }, 409]
    const w = await open()
    await openCard(w, 'Budget review')
    buttonIn(panel()!, 'Cancel booking')!.click()
    await flushPromises()
    useConfirm().answer(true)
    await flushPromises()
    expect(panel()?.textContent).toContain('This item changed. Reload it.')
  })

  describe('quiet refresh', () => {
    beforeEach(() => {
      vi.useFakeTimers({ toFake: ['Date', 'setInterval', 'clearInterval'] })
      vi.setSystemTime(new Date('2026-11-12T03:00:00Z'))
    })

    it('shows a new booking with no click', async () => {
      const w = await open()
      mine = [...mine, bookingItem(11, 'New plan', 'PENDING_PITIKA', '2026-11-17')]
      vi.advanceTimersByTime(15_000)
      await flushPromises()
      expect(titles(w)).toEqual(['Budget review', 'Team sync', 'New plan'])
    })

    it('updates an open booking when someone decides it', async () => {
      await open('?booking=8')
      expect(panel()?.textContent).toContain('Waiting for Pitika')
      detail8 = bookingDetail({ ...WAITING, status: 'CONFIRMED', display_status: 'CONFIRMED', version: 4 })
      vi.advanceTimersByTime(15_000)
      await flushPromises()
      expect(panel()?.textContent).toContain('Confirmed')
      expect(panel()?.textContent).not.toContain('Waiting for Pitika')
    })
  })

  describe('refresh button', () => {
    it('refreshes at once', async () => {
      const w = await open()
      mine = [...mine, bookingItem(12, 'Fresh plan', 'PENDING_PITIKA', '2026-11-18')]
      await w.get('button[aria-label="Refresh"]').trigger('click')
      await flushPromises()
      expect(titles(w)).toContain('Fresh plan')
    })

    it('says when the server cannot be reached, keeps the list, and Try again works', async () => {
      const w = await open()
      mineFails = true
      await w.get('button[aria-label="Refresh"]').trigger('click')
      await flushPromises()
      expect(w.get('[role="status"]').text()).toContain("Can't reach the server.")
      expect(titles(w)).toEqual(['Budget review', 'Team sync'])
      mineFails = false
      await w.get('[role="status"] button').trigger('click')
      await flushPromises()
      expect(w.find('[role="status"]').exists()).toBe(false)
    })
  })
})
