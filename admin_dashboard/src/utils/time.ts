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
