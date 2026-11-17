// The day of a room on the Room availability page (spec 2026-11-17-room-availability-design):
// clock times in minutes, a time's place on the 07:00–18:00 lane, what kind of block a booking
// is, and whether a room is free at a time and until when.

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

/** The words on the lane of a room with no booking that day, and the span they sit over, true
 * to the clock (owner, 17 Nov 2026): another day or before it opens, "Free all day" over its
 * hours; today while open, "Free for the rest of the day" over the time left; after it closes,
 * "Closed for today". Null when the room has bookings. */
export function freeLabel(room: Span, items: Span[], today: boolean, now: number): { text: string; from: number; to: number } | null {
  if (items.length) return null
  const opens = toMinutes(room.start_time)
  const closes = toMinutes(room.end_time)
  if (!today || now < opens) return { text: 'Free all day', from: opens, to: closes }
  if (now < closes) return { text: 'Free for the rest of the day', from: now, to: closes }
  return { text: 'Closed for today', from: opens, to: closes }
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
