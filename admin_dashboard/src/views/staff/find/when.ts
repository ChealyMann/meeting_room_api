// The "When" filter of Find a room (owner pick, 13 Nov 2026: filter chips, "day to day"): one
// day or a range of working days, and a time that is the same every day. Pure helpers only.
import { dayLabel, toTime } from '../rules'

export interface When {
  mode: 'one' | 'range'
  /** The first and last day (equal for one day), ISO dates from the day list. */
  first: string
  last: string
  /** Minutes from midnight; both null = any time. */
  start: number | null
  end: number | null
}

/** How many days the picker offers: today and the next 13 (two weeks, weekends too). */
export const PICK_DAYS = 14

export const anyTime = (today: string): When => ({ mode: 'one', first: today, last: today, start: null, end: null })

/** The days from `first` to `last` in the day list. */
export function datesOf(when: When, days: string[]): string[] {
  return days.filter((d) => d >= when.first && d <= when.last)
}

export const hasTime = (when: When) => when.start !== null && when.end !== null
export const isRange = (when: When) => when.last > when.first

/** Anything other than today, any time. */
export const whenSet = (when: When, today: string) => hasTime(when) || when.first !== today || isRange(when)

const short = (iso: string) => dayLabel(iso).split(' ').slice(0, 2).join(' ') // "Mon 16"
const dayName = (iso: string, today: string) => (iso === today ? 'Today' : dayLabel(iso))

/** "Today, any time" · "Mon 16 Nov, 09:00–10:00" · "Mon 16 – Wed 18 Nov (3 days), 08:00–12:00". */
export function whenLabel(when: When, days: string[], today: string): string {
  const time = hasTime(when) ? `${toTime(when.start!)}–${toTime(when.end!)}` : 'any time'
  if (!isRange(when)) return `${dayName(when.first, today)}, ${time}`
  const month = dayLabel(when.last).split(' ')[2]
  return `${short(when.first)} – ${short(when.last)} ${month} (${datesOf(when, days).length} days), ${time}`
}

/** The line under "Find a room": what the list shows (owner pick, 20 Nov 2026). Today's date is
 *  in the top bar, so it is never repeated; a day is named only when another day is picked.
 *  "16 rooms" · "8 rooms free today, 14:00–16:00" · "8 rooms free on Mon 23 Nov, 09:00–11:00" ·
 *  "3 rooms free on all 3 days, Mon 16 – Wed 18 Nov, 08:00–12:00" · "16 rooms on Mon 23 Nov". */
export function countLine(when: When, days: string[], today: string, total: number): { count: string; rest: string; free: boolean } {
  const rooms = `${total} ${total === 1 ? 'room' : 'rooms'}`
  const free = hasTime(when)
  const time = free ? `, ${toTime(when.start!)}–${toTime(when.end!)}` : ''
  let rest: string
  if (isRange(when)) {
    const month = dayLabel(when.last).split(' ')[2]
    const span = `${short(when.first)} – ${short(when.last)} ${month}`
    rest = free ? ` on all ${datesOf(when, days).length} days, ${span}${time}` : ` on ${span}`
  } else if (when.first === today) {
    rest = free ? ` today${time}` : ''
  } else {
    rest = ` on ${dayLabel(when.first)}${time}`
  }
  return { count: free ? `${rooms} free` : rooms, rest, free }
}

/** The query the rooms list takes: only with a time (the API needs all three). */
export function freeQuery(when: When, days: string[]) {
  if (!hasTime(when)) return {}
  return { free_dates: datesOf(when, days), free_from: toTime(when.start!), free_to: toTime(when.end!) }
}

/** The start times that can still be picked: from 07:00 to 17:30, not passed when today is in. */
export function startChoices(when: When, today: string, now: number): number[] {
  const out: number[] = []
  const includesToday = when.first <= today && when.last >= today
  for (let m = 7 * 60; m <= 17 * 60 + 30; m += 30) if (!includesToday || m > now) out.push(m)
  return out
}

/** For Book: one day goes as date/start/end, a range as dates/start/end. */
export function bookQuery(when: When, days: string[]): Record<string, string> {
  if (!hasTime(when)) return {}
  const start = toTime(when.start!)
  const end = toTime(when.end!)
  return isRange(when) ? { dates: datesOf(when, days).join(','), start, end } : { date: when.first, start, end }
}
