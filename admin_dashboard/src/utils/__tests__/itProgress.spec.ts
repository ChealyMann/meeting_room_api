import { describe, expect, it } from 'vitest'

import type { BookingDetail } from '../../api/types'
import { IT_WORDS, itState } from '../itProgress'

// IT help is an add-on (owner pick F, 19 Nov 2026): the booking is confirmed at the last approval
// and IT's setup runs beside it, in the words the IT help card already uses.
const NOW = new Date('2026-11-10T01:00:00Z') // Tue 10 Nov, 08:00 in Phnom Penh

const booking = (status: string, it: Record<string, unknown> | null, start = '09:00') =>
  ({
    status,
    display_status: status,
    first_session: { id: 1, date: '2026-11-10', start_time: start, end_time: '10:00' },
    it: it && { status: 'RECEIVED', forwarded_at: '2026-11-09T02:00:00Z', ready_at: null, ...it },
  }) as unknown as BookingDetail

describe('itState', () => {
  it('follows the setup on a confirmed booking: sent to IT, setting up, room ready', () => {
    expect(itState(booking('CONFIRMED', {}), NOW)).toBe('sent')
    expect(itState(booking('CONFIRMED', { status: 'ASSIGNED' }), NOW)).toBe('setting')
    expect(itState(booking('CONFIRMED', { status: 'READY', ready_at: '2026-11-10T00:20:00Z' }), NOW)).toBe('ready')
  })

  it('is missed once the meeting started and IT never marked it ready', () => {
    expect(itState(booking('CONFIRMED', { status: 'ASSIGNED' }, '07:30'), NOW)).toBe('missed')
    expect(itState(booking('CONFIRMED', { status: 'ASSIGNED' }, '08:00:00'), NOW)).toBe('missed')
    expect(itState(booking('CONFIRMED', { status: 'READY', ready_at: '2026-11-10T00:20:00Z' }, '07:30'), NOW)).toBe('ready')
  })

  it('works for a booking still in IT setup from before the change, which is never missed', () => {
    expect(itState(booking('SETUP_IN_PROGRESS', { status: 'ASSIGNED' }, '07:30'), NOW)).toBe('setting')
  })

  it('is null with no IT help, before IT has it, and once the booking stopped', () => {
    expect(itState(booking('CONFIRMED', null), NOW)).toBeNull()
    expect(itState(booking('PENDING_PITIKA', { forwarded_at: null }), NOW)).toBeNull()
    expect(itState(booking('CANCELLED', { status: 'ASSIGNED' }), NOW)).toBeNull()
    expect(itState(booking('REJECTED', {}), NOW)).toBeNull()
  })
})

describe('IT_WORDS', () => {
  it('uses the IT help card’s own words, and "Not marked ready" for a missed setup', () => {
    expect(IT_WORDS).toEqual({ sent: 'Sent to IT', setting: 'Setting up', ready: 'Room ready', missed: 'Not marked ready' })
  })
})
