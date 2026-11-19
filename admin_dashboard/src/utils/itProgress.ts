// Where a booking's IT setup is (owner pick F, 19 Nov 2026): IT help is an add-on, so the booking
// is confirmed at the last approval and the setup runs beside it. One answer for the step bar,
// History, the IT help card and the booker's step line.
import type { BookingDetail } from '../api/types'

export type ItState = 'sent' | 'setting' | 'ready' | 'missed'

/** The IT help card's own words, and "Not marked ready" for a setup IT missed. */
export const IT_WORDS: Record<ItState, string> = {
  sent: 'Sent to IT',
  setting: 'Setting up',
  ready: 'Room ready',
  missed: 'Not marked ready',
}

/** The first session's start as a moment (its date and time are Phnom Penh time, UTC+7). */
export function firstStart(b: Pick<BookingDetail, 'first_session'>): number {
  const s = b.first_session
  return Date.parse(`${s.date}T${s.start_time.slice(0, 5)}:00+07:00`)
}

type ItBooking = Pick<BookingDetail, 'status' | 'first_session' | 'it'>

/** Null with no IT help, before IT has the ticket, or once the booking stopped. A setup not
 *  ready when the meeting starts is missed; a booking still in IT setup from before the change
 *  is never missed (the system confirms it at the start). */
export function itState(b: ItBooking, now: Date): ItState | null {
  const it = b.it
  if (!it || !it.forwarded_at) return null
  if (it.status === 'READY') return 'ready'
  if (b.status !== 'CONFIRMED' && b.status !== 'SETUP_IN_PROGRESS') return null
  if (b.status === 'CONFIRMED' && now.getTime() >= firstStart(b)) return 'missed'
  return it.status === 'ASSIGNED' ? 'setting' : 'sent'
}
