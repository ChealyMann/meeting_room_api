// Plain words for the booking API's codes (display status, meeting type, route).
export const STATUS_LABELS: Record<string, string> = {
  PENDING_PITIKA: 'Waiting for Pitika',
  PENDING_OWNER: 'Waiting for owner',
  SETUP_IN_PROGRESS: 'IT setup',
  CONFIRMED: 'Confirmed',
  COMPLETED: 'Completed',
  REJECTED: 'Rejected',
  CANCELLED: 'Cancelled',
}

export const MEETING_TYPE_LABELS: Record<string, string> = {
  INTERNAL: 'Internal',
  EXTERNAL: 'External',
  INTERNAL_WITH_GOVERNOR: 'Internal, with Governor',
  EXTERNAL_WITH_GOVERNOR: 'External, with Governor',
}

export const ROUTE_LABELS: Record<string, string> = {
  R1: 'Shared room',
  R2: 'Private room, owner approves',
  R3: "Owner's own room",
  R4: "Owner's own room, with services",
}

/** The words for a status; a code this list does not know shows as it is. */
export function statusLabel(code: string): string {
  return STATUS_LABELS[code] ?? code
}
