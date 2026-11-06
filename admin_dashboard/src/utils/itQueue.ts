// The IT pages (spec 2026-11-05-owner-and-it-pages-design, Part B): the open tab, setups by
// day, the Ready tab's days, and the head's line and ring. Setup days and times are Phnom Penh
// time from the API; `ready_at` is UTC.
import { Cable, Laptop, Mic, Monitor, Printer, Projector, Speaker, Video, Wifi } from 'lucide-vue-next'
import type { FunctionalComponent } from 'vue'

import type { ITSetup, ITSummary, ITTicketItem } from '../api/types'
import { addDays, formatDay, phnomPenhDate } from './time'

export type ItTab = 'to_assign' | 'in_progress' | 'ready'

/** The tab in the address (`?tab=`); anything else is To assign. */
export function itTabFrom(query: unknown): ItTab {
  const value = Array.isArray(query) ? query[0] : query
  return value === 'in_progress' || value === 'ready' ? value : 'to_assign'
}

export type SetupGroupKey = 'today' | 'tomorrow' | 'week' | 'later'
export interface SetupGroup<T extends ITTicketItem = ITTicketItem> {
  key: SetupGroupKey
  label: string
  items: T[]
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
export function groupBySetupDay<T extends ITTicketItem>(items: T[], today: string): SetupGroup<T>[] {
  const tomorrow = addDays(today, 1)
  const sunday = addDays(today, 6 - weekday(today))
  const keyOf = (day: string): SetupGroupKey => (day <= today ? 'today' : day === tomorrow ? 'tomorrow' : day <= sunday ? 'week' : 'later')
  return GROUPS.map(([key, label]) => ({ key, label, items: items.filter((t) => keyOf(t.setup_date) === key) })).filter((g) => g.items.length)
}

export interface DoneDay<T extends ITTicketItem = ITTicketItem> {
  key: string
  label: string
  items: T[]
}

/** "Thu 5 Nov 2026" → "Thu 5 Nov" when it is this year. */
function shortDay(day: string, today: string): string {
  const text = formatDay(day)
  return day.slice(0, 4) === today.slice(0, 4) ? text.slice(0, -5) : text
}

/** The Ready tab: by the Phnom Penh day it was made ready (a missed one: its meeting day),
 *  newest first; the API order is kept inside a day. */
export function groupByDoneDay<T extends ITTicketItem>(items: T[], today: string): DoneDay<T>[] {
  const yesterday = addDays(today, -1)
  const groups: DoneDay<T>[] = []
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

/** The day a session starts: its setup's day, or the next one when the setup is before midnight. */
export function sessionDate(s: ITSetup): string {
  return s.start_time < s.setup_time ? addDays(s.date, 1) : s.date
}

const sessionStart = (s: ITSetup) => Date.parse(`${sessionDate(s)}T${s.start_time.slice(0, 5)}:00+07:00`)

/** A booking with several sessions, with one not started: staff can still be assigned or changed. */
export function hasSessionAhead(t: ITTicketItem, now: Date): boolean {
  const setups = t.setups ?? []
  return setups.length > 1 && setups.some((s) => sessionStart(s) > now.getTime())
}

/** One row of the IT lists: a setup, or one session's setup of a booking with several. */
export type SetupRow = ITTicketItem & { session: ITSetup | null; rowKey: string }

/**
 * IT sets up before every session (owner decision, 6 Nov 2026): a booking with several sessions
 * is one row per session that has not started (with that session's set-up day and time); a
 * booking with one session, or the Ready tab (`whole`), is one row per setup.
 */
export function setupRows(items: ITTicketItem[], now: Date, whole = false): SetupRow[] {
  const rows: SetupRow[] = items.flatMap((t): SetupRow[] => {
    const setups = t.setups ?? []
    const plain: SetupRow[] = [{ ...t, session: null, rowKey: String(t.id) }]
    if (whole || setups.length < 2) return plain
    const ahead = setups.filter((s) => sessionStart(s) > now.getTime())
    if (!ahead.length) return plain
    return ahead.map((s) => ({ ...t, setup_date: s.date, setup_time: s.setup_time, session: s, rowKey: `${t.id}-${s.session_number}` }))
  })
  if (whole) return rows
  // Several bookings' sessions mix: by set-up day and time, as the API orders whole setups.
  return rows.sort((a, b) => `${a.setup_date} ${a.setup_time}`.localeCompare(`${b.setup_date} ${b.setup_time}`))
}

/** The line under the IT setup title. */
export function itSummaryLine(s: ITSummary): string {
  const again = s.repeat_today ? `${s.repeat_today} to set up again` : null
  const today = s.due_today
    ? [`Today ${s.due_today_ready} of ${s.due_today} setups ready`, again]
    : [again ? `${again} today` : 'No setups today']
  return [...today, s.to_assign ? `${s.to_assign} to assign` : 'nothing to assign'].filter(Boolean).join(' · ')
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
export function myTasksLine(items: Array<ITTicketItem & { session?: ITSetup | null }>, today: string): string {
  const next = items[0]
  if (!next) return 'Nothing to set up'
  const day = next.setup_date === today ? 'today' : shortDay(next.setup_date, today)
  const count = `${items.length} ${items.length === 1 ? 'setup' : 'setups'} to do`
  const start = next.session?.start_time ?? next.booking.first_session.start_time
  return `${count} · next: ${day} ${start.slice(0, 5)}, ${next.booking.room.name_en}`
}

// IT items have no icon of their own: the name tells which one fits (first match wins).
const ITEM_ICONS: Array<[RegExp, string, FunctionalComponent]> = [
  [/projector|hdmi|screen/i, 'Projector', Projector],
  [/mic/i, 'Mic', Mic],
  [/sound|speaker|audio/i, 'Speaker', Speaker],
  [/video|zoom|teams|conference|camera/i, 'Video', Video],
  [/laptop|computer|pc/i, 'Laptop', Laptop],
  [/wi-?fi|internet|network/i, 'Wifi', Wifi],
  [/cable|adapter/i, 'Cable', Cable],
  [/print/i, 'Printer', Printer],
]

/** The icon for an IT item, by its name ("Projector setup" → Projector); a monitor otherwise. */
export function itItemIcon(name: string): { key: string; icon: FunctionalComponent } {
  const hit = ITEM_ICONS.find(([pattern]) => pattern.test(name))
  return hit ? { key: hit[1], icon: hit[2] } : { key: 'Monitor', icon: Monitor }
}
