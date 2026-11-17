// The Food list's day (owner pick, 17 Nov 2026, look A): which deliveries are past, which is
// next, and where the red "Now" line goes.

export type DeliveryState = 'past' | 'next' | 'later'

export interface FoodDay {
  /** One per delivery, in the list's order. Only today has past and next rows. */
  states: DeliveryState[]
  /** The row the now line sits above (the list's length: under the last row); null: no line. */
  nowAt: number | null
  /** "HH:MM" of the next delivery today, or null. */
  nextAt: string | null
}

type Delivery = { delivery_time: string }

/** `items` sorted by time (as the API sends them); `clock` is "HH:MM" in Phnom Penh. */
export function foodDay(items: Delivery[], day: string, today: string, clock: string): FoodDay {
  const isToday = day === today
  const times = items.map((i) => i.delivery_time.slice(0, 5))
  const past = times.map((t) => isToday && t < clock)
  const firstAhead = past.indexOf(false)
  const nextAt = isToday && firstAhead >= 0 ? times[firstAhead]! : null
  const states = times.map((t, i): DeliveryState => (past[i] ? 'past' : t === nextAt ? 'next' : 'later'))
  const pastCount = past.filter(Boolean).length

  return {
    states,
    nowAt: pastCount > 0 ? pastCount : null,
    nextAt,
  }
}
