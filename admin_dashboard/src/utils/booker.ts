// Who booked, for the soft row's footer (owner pick E, 18 Nov 2026): the name, photo and phone
// are today's; the position and department are as they were when the booking was sent (the
// API's BookerRef). The phone comes after the department, a click copies it (owner pick B
// "Plain", 19 Nov 2026).
import type { BookingListItem } from '../api/types'

export interface RowBooker {
  name: string
  photo: string | null
  position: string | null
  department: string | null
  phone?: string | null
}

export function rowBooker(b: Pick<BookingListItem, 'requester'>): RowBooker {
  const r = b.requester
  return {
    name: r.name_en,
    photo: r.avatar_url ?? null,
    position: r.position ?? null,
    department: r.department ?? null,
    phone: r.phone ?? null,
  }
}

/** "Officer · Statistics Department", leaving out what is missing. */
export function bookerRole(booker: RowBooker): string {
  return [booker.position, booker.department].filter(Boolean).join(' · ')
}
