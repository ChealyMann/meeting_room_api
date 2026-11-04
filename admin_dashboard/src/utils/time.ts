// The API sends UTC; people read Cambodia time (Asia/Phnom_Penh, UTC+7).
const ZONE = 'Asia/Phnom_Penh'

const dateTime = new Intl.DateTimeFormat('en-US', {
  timeZone: ZONE,
  day: 'numeric',
  month: 'short',
  year: 'numeric',
  hour: '2-digit',
  minute: '2-digit',
  hourCycle: 'h23',
})

const clock = new Intl.DateTimeFormat('en-US', {
  timeZone: ZONE,
  hour: '2-digit',
  minute: '2-digit',
  hourCycle: 'h23',
})

const day = new Intl.DateTimeFormat('en-US', {
  timeZone: ZONE,
  day: '2-digit',
  month: '2-digit',
  year: 'numeric',
})

// Booking days ("2026-11-04") are already Phnom Penh days: read and shown as plain calendar days.
const calendarDay = new Intl.DateTimeFormat('en-US', {
  timeZone: 'UTC',
  weekday: 'short',
  day: 'numeric',
  month: 'short',
  year: 'numeric',
})

function parts(format: Intl.DateTimeFormat, date: Date): Record<string, string> {
  return Object.fromEntries(format.formatToParts(date).map((p) => [p.type, p.value]))
}

/** "2026-10-23T06:51:03Z" → "23 Oct 2026, 13:51" */
export function formatPhnomPenh(isoUtc: string): string {
  const p = parts(dateTime, new Date(isoUtc))
  return `${p.day} ${p.month} ${p.year}, ${p.hour}:${p.minute}`
}

/** The time now in Phnom Penh, "HH:MM". */
export function phnomPenhClock(now: Date): string {
  const p = parts(clock, now)
  return `${p.hour}:${p.minute}`
}

/** Today in Phnom Penh, "YYYY-MM-DD". */
export function phnomPenhDate(now: Date): string {
  const p = parts(day, now)
  return `${p.year}-${p.month}-${p.day}`
}

/** "2026-12-29" + 6 → "2027-01-04" (calendar days). */
export function addDays(date: string, days: number): string {
  const value = new Date(`${date}T00:00:00Z`)
  value.setUTCDate(value.getUTCDate() + days)
  return value.toISOString().slice(0, 10)
}

/** "2026-11-04" → "Wed 4 Nov 2026" */
export function formatDay(date: string): string {
  const p = parts(calendarDay, new Date(`${date}T00:00:00Z`))
  return `${p.weekday} ${p.day} ${p.month} ${p.year}`
}
