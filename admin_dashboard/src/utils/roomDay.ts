// The day of a room on the Room availability page (spec 2026-11-17-room-availability-design):
// clock times in minutes, a time's place on the 07:00–18:00 lane, what kind of block a booking
// is, whether a room is free at a time and until when, and the one status its row says.

export const DAY_START = 7 * 60
export const DAY_END = 18 * 60

/** "10:45" or "10:45:00" → 645. */
export function toMinutes(time: string): number {
  return Number(time.slice(0, 2)) * 60 + Number(time.slice(3, 5))
}

/** 645 → "10:45". */
export function clockLabel(minutes: number): string {
  return `${String(Math.floor(minutes / 60)).padStart(2, '0')}:${String(minutes % 60).padStart(2, '0')}`
}

/** A time's place on the lane, 0 to 100 (%), clamped to 07:00 and 18:00. */
export function lanePct(minutes: number): number {
  const clamped = Math.min(Math.max(minutes, DAY_START), DAY_END)
  return ((clamped - DAY_START) / (DAY_END - DAY_START)) * 100
}

export type BlockKind = 'booked' | 'waiting' | 'masked'
const WAITING = ['PENDING_PITIKA', 'PENDING_OWNER']

/** Masked: a private booking the reader may not see. Waiting: for Pitika or the room owner. */
export function blockKind(item: { status: string; is_masked: boolean }): BlockKind {
  if (item.is_masked) return 'masked'
  return WAITING.includes(item.status) ? 'waiting' : 'booked'
}

type Span = { start_time: string; end_time: string }

/** Open at `at` (minutes): opening time ≤ at < closing time. Rooms keep their own hours. */
export function isOpenAt(room: Span, at: number): boolean {
  return toMinutes(room.start_time) <= at && at < toMinutes(room.end_time)
}

/** Until when the room stays free from `at` (minutes): the next booking's start or closing
 * time, whichever comes first. Null when the room is closed at `at` or a booking covers it
 * (a booking covers [start, end)). */
export function freeUntil(room: Span, items: Span[], at: number): number | null {
  const closes = toMinutes(room.end_time)
  if (!isOpenAt(room, at)) return null
  let until = closes
  for (const item of items) {
    const start = toMinutes(item.start_time)
    const end = toMinutes(item.end_time)
    if (start <= at && at < end) return null
    if (start > at) until = Math.min(until, start)
  }
  return until
}

export type RoomStatus = { kind: 'free' | 'booked' | 'waiting' | 'closed' | 'some'; text: string }
type Booking = Span & { status: string; is_masked: boolean }

/** The one status a room's row says at `at` (minutes), true to its own hours (owner, 17 Nov 2026):
 * "Free until 14:00" (the next booking or its closing time), "Booked until 11:30" (back-to-back
 * bookings count as one stretch), "Waiting approval until 16:00", "Opens at 08:00" or
 * "Closed after 17:00". */
export function roomStatus(room: Span, items: Booking[], at: number): RoomStatus {
  const opens = toMinutes(room.start_time)
  const closes = toMinutes(room.end_time)
  if (at < opens) return { kind: 'closed', text: `Opens at ${clockLabel(opens)}` }
  if (at >= closes) return { kind: 'closed', text: `Closed after ${clockLabel(closes)}` }
  const on = items.find((i) => toMinutes(i.start_time) <= at && at < toMinutes(i.end_time))
  if (!on) return { kind: 'free', text: `Free until ${clockLabel(freeUntil(room, items, at) ?? closes)}` }
  let until = toMinutes(on.end_time)
  for (let next = items.find((i) => toMinutes(i.start_time) === until); next; next = items.find((i) => toMinutes(i.start_time) === until)) {
    until = toMinutes(next.end_time)
  }
  return blockKind(on) === 'waiting'
    ? { kind: 'waiting', text: `Waiting approval until ${clockLabel(until)}` }
    : { kind: 'booked', text: `Booked until ${clockLabel(until)}` }
}

/** The row's status for the whole day (Free at: Any time). */
export function dayStatus(items: unknown[]): RoomStatus {
  if (!items.length) return { kind: 'free', text: 'Free all day' }
  return { kind: 'some', text: `${items.length} booking${items.length === 1 ? '' : 's'}` }
}

/** The Free at choices: Any time, Now, then every half hour from 07:00 to 17:30. Today, pass the
 * clock (`from`, minutes): only the half hours still to come are offered. */
export function freeAtOptions(from = 0): Array<{ value: string; label: string }> {
  const options = [
    { value: '', label: 'Any time' },
    { value: 'now', label: 'Now' },
  ]
  for (let m = DAY_START; m < DAY_END; m += 30) if (m >= from) options.push({ value: String(m), label: clockLabel(m) })
  return options
}
