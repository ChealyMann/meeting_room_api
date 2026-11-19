import { enableAutoUnmount, mount } from '@vue/test-utils'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import BookingServices from '../BookingServices.vue'

enableAutoUnmount(afterEach)

// The IT help card's word on a confirmed booking: IT is an add-on since 19 Nov 2026 (owner pick
// F), so the setup goes on after the booking is confirmed, and a missed setup says so in crimson.
beforeEach(() => {
  vi.useFakeTimers({ toFake: ['Date'] })
  vi.setSystemTime(new Date('2026-11-10T01:00:00Z')) // Tue 10 Nov, 08:00 in Phnom Penh
})
afterEach(() => vi.useRealTimers())

const booking = (it: Record<string, unknown>, start = '09:00') => ({
  status: 'CONFIRMED',
  display_status: 'CONFIRMED',
  first_session: { id: 1, date: '2026-11-10', start_time: start, end_time: '10:00' },
  sessions: [],
  catering: null,
  it: {
    items: [{ id: 1, name: 'Projector' }],
    special_requirements: null,
    staff: [],
    technician_notes: null,
    status: 'RECEIVED',
    forwarded_at: '2026-11-09T02:00:00Z',
    ready_at: null,
    ...it,
  },
})
const pill = (b: ReturnType<typeof booking>) => {
  const w = mount(BookingServices, { props: { booking: b as never, viewer: 'booker' } })
  const p = w.get('[data-kind="it"] .pill')
  return [p.text(), p.classes().filter((c) => c !== 'pill')[0]]
}

describe('IT help card on a confirmed booking', () => {
  it('says where IT is while the setup goes on', () => {
    expect(pill(booking({}))).toEqual(['Sent to IT', 'wait'])
    expect(pill(booking({ status: 'ASSIGNED' }))).toEqual(['Setting up', 'wait'])
    expect(pill(booking({ status: 'READY', ready_at: '2026-11-10T00:20:00Z' }))).toEqual(['Room ready', 'ok'])
  })

  it('says "Not marked ready" in crimson once the meeting started without it', () => {
    expect(pill(booking({ status: 'ASSIGNED' }, '07:30'))).toEqual(['Not marked ready', 'stop'])
  })
})
