// Approved by (owner, 16 Nov 2026): every approval with name, role, time and note, then the step
// still waiting. Rejections and "not required" steps are not approvals, so they are left out.
import type { BookingDetail } from '../api/types'
import { formatPhnomPenh } from './time'

const STAGE_ROLE: Record<string, string> = { PITIKA: 'Pitika', OWNER: 'Room owner' }
const WAITING: Record<string, string> = {
  PENDING_PITIKA: 'Waiting for Pitika',
  PENDING_OWNER: 'Waiting for the room owner',
  SETUP_IN_PROGRESS: 'IT is setting up the room',
}

export interface Approval {
  who: string
  role: string
  when: string
  note: string | null
}

/** The approvals of a booking, in the order they came: who, role, when, note. */
export function approvedBy(booking: BookingDetail): Approval[] {
  return (booking.reviews ?? [])
    .filter((r) => r.decision === 'APPROVED')
    .map((r) => {
      const role = STAGE_ROLE[r.stage] ?? r.stage
      return {
        who: r.reviewer?.name_en ?? 'Unknown',
        role: r.by_admin ? `Admin, for ${role}` : role,
        when: formatPhnomPenh(r.reviewed_at),
        note: r.notes,
      }
    })
}

/** What the booking still waits for ("Waiting for the room owner"), or null. */
export function waitingFor(booking: BookingDetail): string | null {
  return WAITING[booking.status] ?? null
}
