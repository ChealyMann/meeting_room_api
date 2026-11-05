// The IT pages (spec 2026-11-05-owner-and-it-pages-design, Part B): the open tab, setups by
// day, the Ready tab's days, and the head's line and ring. Setup days and times are Phnom Penh
// time from the API; `ready_at` is UTC.
import type { ITSummary, ITTicketItem } from '../api/types'
import { addDays, formatDay, phnomPenhDate } from './time'

export type ItTab = 'to_assign' | 'in_progress' | 'ready'

/** The tab in the address (`?tab=`); anything else is To assign. */
export function itTabFrom(query: unknown): ItTab {
  const value = Array.isArray(query) ? query[0] : query
  return value === 'in_progress' || value === 'ready' ? value : 'to_assign'
}

export type SetupGroupKey = 'today' | 'tomorrow' | 'week' | 'later'
export interface SetupGroup {
  key: SetupGroupKey
  label: string
  items: ITTicketItem[]
}

const GROUPS: Array<[SetupGroupKey, string]> = [
  ['today', 'Today'],
  ['tomorrow', 'Tomorrow'],
  ['week', 'This week'],
  ['later', 'Later'],
]
const weekday = (day: string) => (new Date(`${day}T00:00:00Z`).getUTCDay() + 6) % 7

/** By the setup day: today (or earlier, still open) → Today, Tomorrow, the rest of this week,
 *  then Later. The API order (earliest first) is kept; empty groups are left out. */
export function groupBySetupDay(items: ITTicketItem[], today: string): SetupGroup[] {
  const tomorrow = addDays(today, 1)
  const sunday = addDays(today, 6 - weekday(today))
  const keyOf = (day: string): SetupGroupKey => (day <= today ? 'today' : day === tomorrow ? 'tomorrow' : day <= sunday ? 'week' : 'later')
  return GROUPS.map(([key, label]) => ({ key, label, items: items.filter((t) => keyOf(t.setup_date) === key) })).filter((g) => g.items.length)
}

export interface DoneDay {
  key: string
  label: string
  items: ITTicketItem[]
}

/** "Thu 5 Nov 2026" → "Thu 5 Nov" when it is this year. */
function shortDay(day: string, today: string): string {
  const text = formatDay(day)
  return day.slice(0, 4) === today.slice(0, 4) ? text.slice(0, -5) : text
}

/** The Ready tab: by the Phnom Penh day it was made ready (a missed one: its meeting day),
 *  newest first; the API order is kept inside a day. */
export function groupByDoneDay(items: ITTicketItem[], today: string): DoneDay[] {
  const yesterday = addDays(today, -1)
  const groups: DoneDay[] = []
  for (const item of items) {
    const day = item.ready_at ? phnomPenhDate(new Date(item.ready_at)) : item.booking.first_session.date
    let group = groups.find((g) => g.key === day)
    if (!group) {
      const short = shortDay(day, today)
      group = { key: day, label: day === today ? `Today · ${short}` : day === yesterday ? `Yesterday · ${short}` : short, items: [] }
      groups.push(group)
    }
    group.items.push(item)
  }
  return groups.sort((a, b) => (a.key < b.key ? 1 : a.key > b.key ? -1 : 0))
}

/** "Set up by 07:30" */
export function setupText(t: ITTicketItem): string {
  return `Set up by ${t.setup_time.slice(0, 5)}`
}

/** The line under the IT setup title. */
export function itSummaryLine(s: ITSummary): string {
  const left = s.due_today ? `Today ${s.due_today_ready} of ${s.due_today} setups ready` : 'No setups today'
  return `${left} · ${s.to_assign ? `${s.to_assign} to assign` : 'nothing to assign'}`
}

/** The ring: today's setups that are ready, of all due today. */
export function itRing(s: ITSummary): { parts: Array<{ value: number; tone: 'ok' | 'no' }>; label: string; spoken: string } {
  if (!s.due_today) return { parts: [], label: '0/0', spoken: 'No setups today' }
  return {
    parts: [{ value: s.due_today_ready / s.due_today, tone: 'ok' }],
    label: `${s.due_today_ready}/${s.due_today}`,
    spoken: `${s.due_today_ready} of ${s.due_today} setups ready today`,
  }
}

/** IT Staff's line: how many to do, and the next one. */
export function myTasksLine(items: ITTicketItem[], today: string): string {
  const next = items[0]
  if (!next) return 'Nothing to set up'
  const day = next.setup_date === today ? 'today' : shortDay(next.setup_date, today)
  const count = `${items.length} ${items.length === 1 ? 'setup' : 'setups'} to do`
  return `${count} · next: ${day} ${next.setup_time.slice(0, 5)}, ${next.booking.room.name_en}`
}
