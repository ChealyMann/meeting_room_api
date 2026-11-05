// The Pitika's "Decided by me" tabs (spec 2026-11-05-pitika-decided-design): the open tab,
// the decision-day groups, where a booking is now, and today's ring and line.
// Days and times are Phnom Penh time; `decided_at` is UTC from the API.
import type { DecidedBookingItem, PitikaSummary } from '../api/types'
import { addDays, formatDay, phnomPenhClock, phnomPenhDate } from './time'

export type Tab = 'waiting' | 'approved' | 'rejected'

/** The tab in the address (`?tab=`); anything else is Waiting. */
export function tabFrom(query: unknown): Tab {
  const value = Array.isArray(query) ? query[0] : query
  return value === 'approved' || value === 'rejected' ? value : 'waiting'
}

export interface DecisionDay {
  key: string
  label: string
  items: DecidedBookingItem[]
}

/** "Thu 5 Nov 2026" → "Thu 5 Nov" when it is this year. */
function shortDay(day: string, today: string): string {
  const text = formatDay(day)
  return day.slice(0, 4) === today.slice(0, 4) ? text.slice(0, -5) : text
}

/** By the Phnom Penh day of the decision; the API order (newest first) is kept. */
export function groupByDecisionDay(items: DecidedBookingItem[], today: string): DecisionDay[] {
  const yesterday = addDays(today, -1)
  const groups: DecisionDay[] = []
  for (const item of items) {
    const day = phnomPenhDate(new Date(item.decided_at))
    let group = groups.find((g) => g.key === day)
    if (!group) {
      const short = shortDay(day, today)
      const label = day === today ? `Today · ${short}` : day === yesterday ? `Yesterday · ${short}` : short
      group = { key: day, label, items: [] }
      groups.push(group)
    }
    group.items.push(item)
  }
  return groups.sort((a, b) => (a.key < b.key ? 1 : a.key > b.key ? -1 : 0))
}

export type PillTone = 'warn' | 'ok' | 'no' | 'plain'

const NOW: Record<string, { text: string; tone: PillTone }> = {
  PENDING_OWNER: { text: 'Room owner next', tone: 'warn' },
  SETUP_IN_PROGRESS: { text: 'IT setup', tone: 'plain' },
  CONFIRMED: { text: 'Confirmed', tone: 'ok' },
  COMPLETED: { text: 'Completed', tone: 'plain' },
  CANCELLED: { text: 'Cancelled', tone: 'plain' },
  REJECTED: { text: 'Rejected', tone: 'no' },
}

/** Where the booking is now. */
export function nowPill(item: DecidedBookingItem): { text: string; tone: PillTone } {
  return NOW[item.display_status] ?? { text: item.display_status, tone: 'plain' }
}

/** "13:38": the Phnom Penh time of the decision. */
export function decidedTime(item: DecidedBookingItem): string {
  return phnomPenhClock(new Date(item.decided_at))
}

/** The line under the title. */
export function summaryLine(s: PitikaSummary): string {
  const decided = s.approved_today + s.rejected_today
  const left = decided ? `Today you decided ${decided}` : 'Nothing decided yet today'
  const right = s.waiting ? (decided ? `${s.waiting} still waiting` : `${s.waiting} waiting`) : 'nothing waiting'
  return `${left} · ${right}`
}

/** The ring: approved and rejected today as parts (0 to 1) of today's whole, and "6/9". */
export function ringArcs(s: PitikaSummary): { approved: number; rejected: number; label: string } {
  const decided = s.approved_today + s.rejected_today
  const whole = decided + s.waiting
  return {
    approved: whole ? s.approved_today / whole : 0,
    rejected: whole ? s.rejected_today / whole : 0,
    label: `${decided}/${whole}`,
  }
}
