// The room owner's To review queue (spec 2026-11-05-owner-and-it-pages-design, Part A): the row's
// process bar ("gap is you"), what an owner checks, and what approving leads to.
import type { BookingDetail, BookingListItem } from '../api/types'
import type { RowStep } from './reviewQueue'

/** Sent and Pitika done; then the gap into the steps after the owner: IT setup (IT asked), Confirmed. */
export function ownerRowSteps(item: BookingListItem): RowStep[] {
  const after = [...(item.has_it ? ['IT setup'] : []), 'Confirmed']
  return [
    { label: 'Sent', state: 'done' },
    { label: 'Pitika', state: 'done' },
    ...after.map((label, k) => ({ label, state: 'todo' as const, ...(k === 0 ? { gap: true } : {}) })),
  ]
}

/** What approving leads to (T7: IT setup, T8: confirmed). */
export function ownerNextStepText(b: BookingDetail): string {
  return b.has_it ? 'It goes to IT setup next.' : 'It is confirmed, with a door pass.'
}

/** The notes of the Pitika's approval (also an Admin's backup one), or null. */
export function pitikaNotes(b: BookingDetail): string | null {
  const review = b.reviews.find((r) => r.stage === 'PITIKA' && r.decision === 'APPROVED')
  const notes = review?.notes?.trim()
  return notes ? notes : null
}

export interface OwnerLabel {
  kind: 'private' | 'governor' | 'seats' | 'pitika-notes'
  text: string
  /** More people than seats. */
  over?: boolean
}

const GOVERNOR = new Set(['INTERNAL_WITH_GOVERNOR', 'EXTERNAL_WITH_GOVERNOR'])

/** What the owner checks: why private, the Governor, people vs seats (`seats` null: unknown,
 *  left out), and that the Pitika wrote notes. Food and IT are not the owner's to check. */
export function ownerCheckLabels(b: BookingDetail, seats: number | null): OwnerLabel[] {
  const labels: OwnerLabel[] = [{ kind: 'private', text: b.private_justification ? 'Private · reason given' : 'Private · no reason' }]
  if (GOVERNOR.has(b.meeting_type)) labels.push({ kind: 'governor', text: 'With Governor' })
  if (seats !== null && Number.isFinite(seats)) {
    const text = `${b.attendees} people · ${seats} seats`
    labels.push(b.attendees > seats ? { kind: 'seats', text, over: true } : { kind: 'seats', text })
  }
  if (pitikaNotes(b)) labels.push({ kind: 'pitika-notes', text: 'Pitika notes' })
  return labels
}
