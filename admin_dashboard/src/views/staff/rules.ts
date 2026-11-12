// The Staff booking pages' rules, with no Vue in them: room hours, free start times, the "Free
// until 14:00" line, joining picked sessions, the meeting type, and search and groups for food
// and IT. Times are minutes after midnight; days are Phnom Penh days as YYYY-MM-DD.
import type { MeetingType } from '../../api/types'

export interface Span {
  a: number
  b: number
  masked: boolean
}
export interface Hours {
  open: number
  close: number
}
export interface PickedSession {
  date: string
  a: number
  b: number
}
export interface NowLine {
  tone: 'ok' | 'alert' | 'off'
  text: string
}

export const toMin = (t: string): number => {
  const [h, m] = t.split(':').map(Number)
  return h! * 60 + m!
}
export const toTime = (m: number): string =>
  `${String(Math.floor(m / 60)).padStart(2, '0')}:${String(m % 60).padStart(2, '0')}`

export function lenText(min: number): string {
  const h = Math.floor(min / 60)
  const m = min % 60
  return [h ? `${h} h` : '', m ? `${m} min` : ''].filter(Boolean).join(' ') || '0 min'
}

const dayOf = (iso: string) => new Date(`${iso}T00:00:00Z`)
const isoOf = (d: Date) => d.toISOString().slice(0, 10)
export const isWeekend = (iso: string) => [0, 6].includes(dayOf(iso).getUTCDay())

/** `count` working days from `day` (that day included when it is a working day). */
export function workdaysFrom(day: string, count: number): string[] {
  const out: string[] = []
  for (const d = dayOf(day); out.length < count; d.setUTCDate(d.getUTCDate() + 1)) {
    const iso = isoOf(d)
    if (!isWeekend(iso)) out.push(iso)
  }
  return out
}

export const roomHours = (room: { start_time: string; end_time: string }): Hours => ({
  open: toMin(room.start_time),
  close: toMin(room.end_time),
})

/** The blocking times of `day`, sorted. A masked private booking is busy like any other. */
export function busySpans(
  items: { date: string; start_time: string; end_time: string; is_masked: boolean }[],
  day: string,
): Span[] {
  return items
    .filter((item) => item.date === day)
    .map((item) => ({ a: toMin(item.start_time), b: toMin(item.end_time), masked: item.is_masked }))
    .sort((x, y) => x.a - y.a)
}

/** Can `len` minutes from `a` be booked on `day`? Inside the room hours, not started yet, not busy. */
export function fits(busy: Span[], hours: Hours, day: string, today: string, now: number, a: number, len: number): boolean {
  if (a < hours.open || a + len > hours.close) return false
  if (day < today || (day === today && a <= now)) return false
  return !busy.some((s) => a < s.b && s.a < a + len)
}

/** The start times (every `step` minutes) where `len` minutes fit. */
export function freeStarts(busy: Span[], hours: Hours, day: string, today: string, now: number, len: number, step = 30): number[] {
  const out: number[] = []
  for (let a = Math.ceil(hours.open / step) * step; a + len <= hours.close; a += step) {
    if (fits(busy, hours, day, today, now, a, len)) out.push(a)
  }
  return out
}

/** The live line on a room card. Meetings that touch count as one ("In use until 16:00"). */
export function nowLine(busy: Span[], hours: Hours, day: string, today: string, now: number): NowLine {
  if (day !== today || now >= hours.close) return { tone: 'off', text: 'Closed now' }
  if (now < hours.open) return { tone: 'off', text: `Opens at ${toTime(hours.open)}` }
  const current = busy.find((s) => s.a <= now && now < s.b)
  if (current) {
    let until = current.b
    for (const s of busy) if (s.a <= until && s.b > until) until = s.b
    return { tone: 'alert', text: `In use until ${toTime(until)}` }
  }
  const next = busy.find((s) => s.a > now)
  return next ? { tone: 'ok', text: `Free until ${toTime(next.a)}` } : { tone: 'ok', text: 'Free all day' }
}

/** Sorted by day and time; picks that touch or overlap on one day become one. */
export function mergeSessions(list: PickedSession[]): PickedSession[] {
  const out: PickedSession[] = []
  for (const s of [...list].sort((x, y) => x.date.localeCompare(y.date) || x.a - y.a)) {
    const last = out[out.length - 1]
    if (last && last.date === s.date && s.a <= last.b) last.b = Math.max(last.b, s.b)
    else out.push({ ...s })
  }
  return out
}

/** Internal / External plus "The Governor attends" (owner decision, 12 Nov 2026). */
export function toMeetingType(external: boolean, governor: boolean): MeetingType {
  return `${external ? 'EXTERNAL' : 'INTERNAL'}${governor ? '_WITH_GOVERNOR' : ''}` as MeetingType
}
export function fromMeetingType(type: MeetingType): { external: boolean; governor: boolean } {
  return { external: type.startsWith('EXTERNAL'), governor: type.endsWith('_WITH_GOVERNOR') }
}

/** The food group that suits the first session's start (shown first, with no label). */
export function foodGroupFirst(start: number): 'BREAKFAST' | 'MEALS' | 'BREAKS' {
  if (start < 630) return 'BREAKFAST'
  if (start < 810) return 'MEALS'
  return 'BREAKS'
}

const escape = (w: string) => w.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')

/** Every typed word must match the start of a word: "tea" finds "Tea", not "steamed". */
export function matchesWords(text: string, query: string): boolean {
  const words = query.trim().toLowerCase().split(/\s+/).filter(Boolean)
  return words.every((w) => new RegExp(`(^|[^\\p{L}\\p{N}])${escape(w)}`, 'iu').test(text))
}

/** Items in groups, `order` first and no group (or an unknown one) as OTHER last; empty groups
 *  are left out. The search looks at the name and the description. */
export function groupServices<T extends { group: string | null; name: string; description: string | null }>(
  items: T[],
  order: string[],
  query: string,
): { group: string; items: T[] }[] {
  const shown = items.filter((item) => matchesWords(`${item.name} ${item.description ?? ''}`, query))
  const keyOf = (item: T) => (item.group && order.includes(item.group) ? item.group : 'OTHER')
  return [...order, 'OTHER']
    .map((group) => ({ group, items: shown.filter((item) => keyOf(item) === group) }))
    .filter((g) => g.items.length > 0)
}
