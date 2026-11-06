// The Pitika's To review queue (spec 2026-11-05-pitika-review-design): urgency groups, how
// soon a booking starts, the row's process bar ("gap is you") and what the Pitika checks.
// Days are Phnom Penh days; a session's date and times are already Phnom Penh time.
import type { BookingDetail, BookingListItem } from '../api/types'
import { addDays } from './time'

export type UrgencyKey = 'today' | 'tomorrow' | 'week' | 'later'
export interface UrgencyGroup {
  key: UrgencyKey
  label: string
  hint: string
  items: BookingListItem[]
}

const GROUPS: Array<[UrgencyKey, string, string]> = [
  ['today', 'Today', 'Decide before they start, or they expire'],
  ['tomorrow', 'Tomorrow', ''],
  ['week', 'This week', ''],
  ['later', 'Later', ''],
]

/** Monday = 0 … Sunday = 6. */
const weekday = (day: string) => (new Date(`${day}T00:00:00Z`).getUTCDay() + 6) % 7

/** By the first session's day: today (or already started) → Today, then Tomorrow, the rest of
 *  this week (to Sunday), then Later. The order inside a group is kept; empty groups are left out. */
export function groupByUrgency(items: BookingListItem[], today: string): UrgencyGroup[] {
  const tomorrow = addDays(today, 1)
  const sunday = addDays(today, 6 - weekday(today))
  const keyOf = (day: string): UrgencyKey =>
    day <= today ? 'today' : day === tomorrow ? 'tomorrow' : day <= sunday ? 'week' : 'later'
  return GROUPS.map(([key, label, hint]) => ({
    key,
    label,
    hint,
    items: items.filter((item) => keyOf(item.first_session.date) === key),
  })).filter((group) => group.items.length > 0)
}

/** "Starts in 4 h 40 min", "Starts in 2 h", "Starts in 25 min", or "Started". */
export function startsIn(item: BookingListItem, now: Date): string {
  return startsAt(item.first_session.date, item.first_session.start_time, now)
}

/** "Starts in 4 h 40 min" (or "Started") for any session: its Phnom Penh day and start time. */
export function startsAt(date: string, startTime: string, now: Date): string {
  const start = Date.parse(`${date}T${startTime.slice(0, 5)}:00+07:00`)
  const minutes = Math.floor((start - now.getTime()) / 60_000)
  if (minutes <= 0) return 'Started'
  const h = Math.floor(minutes / 60)
  const m = minutes % 60
  if (!h) return `Starts in ${m} min`
  return m ? `Starts in ${h} h ${m} min` : `Starts in ${h} h`
}

export interface RowStep {
  label: string
  state: 'done' | 'todo'
  /** The dashed amber line into this step: the Pitika's decision, waiting. */
  gap?: boolean
}

/** Sent, then the steps after Pitika: the room owner (R2), IT setup (IT asked, not R3), Confirmed. */
export function rowSteps(item: BookingListItem): RowStep[] {
  const after = [
    ...(item.route === 'R2' ? ['Room owner'] : []),
    ...(item.has_it && item.route !== 'R3' ? ['IT setup'] : []),
    'Confirmed',
  ]
  return [{ label: 'Sent', state: 'done' }, ...after.map((label, k) => ({ label, state: 'todo' as const, ...(k === 0 ? { gap: true } : {}) }))]
}

export interface CheckLabel {
  kind: 'private' | 'food' | 'it' | 'r4'
  text: string
  /** Servings, for food. */
  count?: number
}

const names = (list: Array<Record<string, unknown>>) => list.map((x) => String(x.name)).join(', ')

/** What the Pitika approves with the booking: a private room's reason, the food, the IT help. */
export function checkLabels(b: BookingDetail): CheckLabel[] {
  const labels: CheckLabel[] = []
  if (b.route === 'R2') labels.push({ kind: 'private', text: b.private_justification ? 'Private · reason given' : 'Private · no reason' })
  if (b.route === 'R4') labels.push({ kind: 'r4', text: 'Food and IT only' })
  if (b.catering) labels.push({ kind: 'food', text: names(b.catering.packages), count: b.catering.servings })
  if (b.it) labels.push({ kind: 'it', text: names(b.it.items) })
  return labels
}

/** What approving leads to (T3, T4, T5), and that the food is approved with it. */
export function nextStepText(b: BookingDetail): string {
  const next =
    b.route === 'R2' ? 'It goes to the room owner next.' : b.has_it ? 'It goes to IT setup next.' : 'It is confirmed, with a door pass.'
  return b.catering ? `${next} The food is approved with it.` : next
}
