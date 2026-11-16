import { enableAutoUnmount, flushPromises, mount, type VueWrapper } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createMemoryHistory, createRouter, type Router } from 'vue-router'

import { useToast } from '../../../composables/useToast'
import { useSessionStore } from '../../../stores/session'
import { bookingStubs, roomDetail, service, type StubAnswers } from '../../../test-utils/staff'
import BookView from '../BookView.vue'

enableAutoUnmount(afterEach)

let router: Router
beforeEach(() => {
  vi.useFakeTimers({ toFake: ['Date'] })
  vi.setSystemTime(new Date('2026-11-12T03:00:00Z'))
  setActivePinia(createPinia())
  useSessionStore().accessToken = 'A1'
  useToast().toasts.value = []
  router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/book/:roomId', name: 'book', component: BookView },
      { path: '/find-room/:roomId', name: 'staff-room', component: { template: '<div />' } },
      { path: '/my-bookings', name: 'my-bookings', component: { template: '<div />' } },
    ],
  })
})
afterEach(() => {
  vi.useRealTimers()
  vi.unstubAllGlobals()
})

async function step4(answers: StubAnswers = {}, extra: Record<string, unknown> = {}, files: File[] = []) {
  const stubs = bookingStubs(roomDetail(12, 'Mekong Room', extra), { foods: [service(1, 'Coffee and tea', 'BREAKS')], ...answers })
  vi.stubGlobal('fetch', stubs.fetch)
  await router.push('/book/12?date=2026-11-13&start=09:00&end=10:00')
  const w = mount(BookView, { global: { plugins: [router] }, attachTo: document.body })
  await flushPromises()
  await w.get('button.next').trigger('click')
  await w.get('input[name="title"]').setValue('Budget review')
  if (extra.is_private) await w.get('textarea[name="justification"]').setValue('Board papers')
  for (const file of files) {
    const input = w.get('.ms input[type="file"]')
    Object.defineProperty(input.element, 'files', { value: [file], configurable: true })
    await input.trigger('change')
  }
  await w.get('button.next').trigger('click')
  await flushPromises()
  await w.get('button.next').trigger('click')
  await flushPromises()
  return { w, stubs }
}
const onStep = (w: VueWrapper) => w.get('.bf-steps button.on').text()
const send = (w: VueWrapper) => w.get('button.next')
async function press(w: VueWrapper) {
  await send(w).trigger('click')
  await flushPromises()
}

describe('Booking step 4: review, check and send', () => {
  it('asks the API to check and shows its steps after "You send it"', async () => {
    const { w, stubs } = await step4({
      check: () => [{ route: 'R2', first_status: 'PENDING_PITIKA', steps: ['PITIKA', 'OWNER', 'CONFIRMED'], problem: null, warnings: [] }],
    })
    expect(onStep(w)).toContain('Review')
    expect(stubs.bodies['POST /api/v1/bookings/check']).toEqual({
      room_id: 12,
      sessions: [{ date: '2026-11-13', start_time: '09:00', end_time: '10:00' }],
      has_catering: false,
      has_it: false,
    })
    const path = w.findAll('.bf-path li').map((li) => li.text())
    expect(path[0]).toContain('You send it')
    expect(path.slice(1, 4)).toEqual(['Pitika checks it', 'The room owner checks it', 'Confirmed'])
    expect(w.get('.rv').text()).toContain('Budget review')
  })

  it('names the picked food with no serving count', async () => {
    const stubs = bookingStubs(roomDetail(12, 'Mekong Room'), { foods: [service(1, 'Coffee and tea', 'BREAKS')] })
    vi.stubGlobal('fetch', stubs.fetch)
    await router.push('/book/12?date=2026-11-13&start=09:00&end=10:00')
    const w = mount(BookView, { global: { plugins: [router] }, attachTo: document.body })
    await flushPromises()
    await w.get('button.next').trigger('click')
    await w.get('input[name="title"]').setValue('Budget review')
    await w.get('button.next').trigger('click')
    await flushPromises()
    await w.get('.svc[data-kind="food"] .row').trigger('click')
    await w.get('button.next').trigger('click')
    await flushPromises()
    expect(w.get('.rv').text()).toContain('Coffee and tea')
    expect(w.get('.rv').text()).not.toContain('each')
  })

  it('shows a public holiday warning and still lets you send', async () => {
    const { w } = await step4({
      check: () => [
        {
          route: 'R1',
          first_status: 'PENDING_PITIKA',
          steps: ['PITIKA', 'CONFIRMED'],
          problem: null,
          warnings: [{ code: 'PUBLIC_HOLIDAY', date: '2026-11-13', name: 'Water Festival' }],
        },
      ],
    })
    expect(w.get('.rv-warn').text()).toContain('Fri 13 Nov is Water Festival')
    expect(send(w).attributes('disabled')).toBeUndefined()
  })

  it('turns Send off while the check has a problem', async () => {
    const { w } = await step4({
      check: () => [
        {
          route: null,
          first_status: null,
          steps: null,
          problem: { code: 'SLOT_TAKEN', message: 'This time is already booked.', fields: { sessions: 'This time is already booked.' } },
          warnings: [],
        },
      ],
    })
    expect(w.text()).toContain('This time is already booked.')
    expect(send(w).attributes('disabled')).toBeDefined()
  })

  it('goes back to the table with every session kept when the time was taken on send', async () => {
    const { w } = await step4({
      send: () => [
        { error: { code: 'SLOT_TAKEN', message: 'Someone just booked this time.', fields: { sessions: 'Someone just booked this time.' } } },
        409,
      ],
    })
    await press(w)
    expect(onStep(w)).toContain('Schedule')
    expect(w.text()).toContain('Someone just booked this time.')
    expect(w.findAll('.bf-sess li').map((li) => li.text().replace(/\s+/g, ' '))).toEqual(['Tomorrow 09:00–10:00 · 1 h'])
  })

  it('sends the booking and opens My bookings with a toast', async () => {
    const { w, stubs } = await step4()
    await press(w)
    expect(stubs.bodies['POST /api/v1/bookings']).toMatchObject({
      room_id: 12,
      meeting_title: 'Budget review',
      meeting_type: 'INTERNAL',
      attendees: 8,
      catering: null,
      it: null,
    })
    expect(router.currentRoute.value.name).toBe('my-bookings')
    expect(useToast().toasts.value.map((t) => t.title)).toContain('Request sent. Pitika checks it next.')
  })

  it('lists the files on the review', async () => {
    const { w } = await step4({}, {}, [new File(['%PDF-1'], 'agenda.pdf'), new File(['x'], 'budget.xlsx')])
    expect(w.findAll('.rv .att-name').map((n) => n.text())).toEqual(['agenda.pdf', 'budget.xlsx'])
    expect(w.find('.rv [aria-label="Remove agenda.pdf"]').exists()).toBe(false)
  })

  it('sends the booking, then each file', async () => {
    const { w, stubs } = await step4({}, {}, [new File(['%PDF-1'], 'agenda.pdf'), new File(['x'], 'budget.xlsx')])
    await press(w)
    const posts = stubs.calls.filter((c) => c.startsWith('POST /api/v1/bookings') && !c.endsWith('/check'))
    expect(posts).toEqual(['POST /api/v1/bookings', 'POST /api/v1/bookings/77/attachments', 'POST /api/v1/bookings/77/attachments'])
    expect(useToast().toasts.value.map((t) => t.title)).toContain('Request sent. Pitika checks it next.')
  })

  it('still sends when a file fails, and says so', async () => {
    const failSecond = (n: number): [unknown, number?] =>
      n === 1 ? [{ error: { code: 'UNSUPPORTED_FILE_TYPE', message: 'Only PDF, Word or Excel files.', fields: {} } }, 415] : [{ id: 1, file_name: 'a.pdf', content_type: 'application/pdf', size_bytes: 6, created_at: '2026-11-12T03:00:00Z', url: '/x' }, 201]
    const { w } = await step4({ upload: failSecond }, {}, [new File(['%PDF-1'], 'agenda.pdf'), new File(['x'], 'budget.xlsx')])
    await press(w)
    expect(router.currentRoute.value.name).toBe('my-bookings')
    expect(useToast().toasts.value.map((t) => t.title)).toContain('Request sent. 1 file could not be added — add it from My bookings.')
  })

  it('says the room owner checks too on a private room', async () => {
    const { w } = await step4({}, { is_private: true })
    await press(w)
    expect(useToast().toasts.value.map((t) => t.title)).toContain('Request sent. Pitika and the room owner check it next.')
  })
})
