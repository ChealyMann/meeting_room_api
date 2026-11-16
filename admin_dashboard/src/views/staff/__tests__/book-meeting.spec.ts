import { enableAutoUnmount, flushPromises, mount, type VueWrapper } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createMemoryHistory, createRouter, type Router } from 'vue-router'

import { useSessionStore } from '../../../stores/session'
import { bookingStubs, roomDetail } from '../../../test-utils/staff'
import BookView from '../BookView.vue'
import MeetingStep from '../book/MeetingStep.vue'
import { useBookingDraft } from '../book/useBookingDraft'

enableAutoUnmount(afterEach)

let router: Router
beforeEach(() => {
  vi.useFakeTimers({ toFake: ['Date'] })
  vi.setSystemTime(new Date('2026-11-12T03:00:00Z'))
  setActivePinia(createPinia())
  useSessionStore().accessToken = 'A1'
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

async function step2(extra: Record<string, unknown> = {}) {
  vi.stubGlobal('fetch', bookingStubs(roomDetail(12, 'Mekong Room', extra)).fetch)
  await router.push('/book/12?date=2026-11-13&start=09:00&end=10:00')
  const w = mount(BookView, { global: { plugins: [router] }, attachTo: document.body })
  await flushPromises()
  await w.get('button.next').trigger('click')
  await flushPromises()
  return w
}
const onStep = (w: VueWrapper) => w.get('.bf-steps button.on').text()
async function next(w: VueWrapper) {
  await w.get('button.next').trigger('click')
  await flushPromises()
}

describe('Booking step 2: meeting details', () => {
  it('needs a title before going on', async () => {
    const w = await step2()
    expect(onStep(w)).toContain('Meeting details')
    await next(w)
    expect(w.text()).toContain('Write a title for the meeting.')
    expect(onStep(w)).toContain('Meeting details')
  })

  it('stops more people than seats, even typed by hand', async () => {
    const w = await step2()
    await w.get('input[name="title"]').setValue('Budget review')
    await w.get('input[name="people"]').setValue('30')
    await next(w)
    expect(w.text()).toContain('This room has 14 seats.')
    expect(onStep(w)).toContain('Meeting details')
  })

  it('sets the people with a quick button, only up to the seats', async () => {
    const w = await step2()
    const quick = w.findAll('.quick button')
    expect(quick.map((b) => b.text())).toEqual(['2', '4', '6', '8', '10'])
    await quick.find((b) => b.text() === '10')!.trigger('click')
    expect((w.get('input[name="people"]').element as HTMLInputElement).value).toBe('10')
    expect(w.text()).toContain('Up to 14')
  })

  it('goes on to Food & IT when the details are good', async () => {
    const w = await step2()
    await w.get('input[name="title"]').setValue('Budget review')
    await next(w)
    expect(onStep(w)).toContain('Food & IT')
  })

  it('asks why on a private room', async () => {
    const w = await step2({ is_private: true })
    expect(w.text()).toContain('Only Pitika and the room owner read this.')
    await w.get('input[name="title"]').setValue('Budget review')
    await next(w)
    expect(w.text()).toContain('Tell the room owner why you need this room.')
    expect(onStep(w)).toContain('Meeting details')
  })

  it('has no private reason field on a normal room', async () => {
    const w = await step2()
    expect(w.find('textarea[name="justification"]').exists()).toBe(false)
  })
})

describe('Meeting type and emails', () => {
  function mountStep() {
    const booking = useBookingDraft(12)
    const w = mount(MeetingStep, { props: { draft: booking.draft, room: roomDetail(12, 'Mekong Room') as never, errors: {} } })
    return { w, booking }
  }

  it('is Internal with no Governor at first', () => {
    const { booking } = mountStep()
    expect(booking.toCreateBody().meeting_type).toBe('INTERNAL')
  })

  it('maps External and The Governor attends to EXTERNAL_WITH_GOVERNOR', async () => {
    const { w, booking } = mountStep()
    await w.findAll('[role="radio"]').find((b) => b.text() === 'External')!.trigger('click')
    await w.get('[role="switch"]').trigger('click')
    expect(w.get('[role="switch"]').attributes('aria-checked')).toBe('true')
    expect(booking.toCreateBody().meeting_type).toBe('EXTERNAL_WITH_GOVERNOR')
  })

  it('adds an email as a chip with Enter or a comma, and refuses a bad one', async () => {
    const { w, booking } = mountStep()
    const input = w.get('input[name="email"]')
    await input.setValue('sok@nbc.gov.kh')
    await input.trigger('keydown', { key: 'Enter' })
    await input.setValue('dara@nbc.gov.kh,')
    expect(booking.draft.emails).toEqual(['sok@nbc.gov.kh', 'dara@nbc.gov.kh'])
    expect(w.findAll('.chip')).toHaveLength(2)
    await input.setValue('dara@')
    await input.trigger('keydown', { key: 'Enter' })
    expect(w.text()).toContain('Write a full email address.')
    expect(booking.draft.emails).toHaveLength(2)
  })
})

describe('Files (optional)', () => {
  async function pick(w: VueWrapper, file: File) {
    const input = w.get('.ms input[type="file"]')
    Object.defineProperty(input.element, 'files', { value: [file], configurable: true })
    await input.trigger('change')
  }

  it('adds and removes files, and goes on with none', async () => {
    const w = await step2()
    await w.get('input[name="title"]').setValue('Budget review')
    await pick(w, new File(['%PDF-1'], 'agenda.pdf'))
    expect(w.findAll('.ms .att-name').map((n) => n.text())).toEqual(['agenda.pdf'])
    await w.get('[aria-label="Remove agenda.pdf"]').trigger('click')
    expect(w.find('.ms .att-name').exists()).toBe(false)
    await next(w)
    expect(onStep(w)).toContain('Food')
  })

  it('refuses a picture with the reason', async () => {
    const w = await step2()
    await pick(w, new File(['x'], 'photo.png'))
    expect(w.find('.ms .att-name').exists()).toBe(false)
    expect(w.get('.ms .att-problem').text()).toBe('Only PDF, Word or Excel files.')
  })
})
