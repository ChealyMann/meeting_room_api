// What stops step 2 (Meeting details) from going on. Empty when the details are good.
import type { BookingDraft } from './useBookingDraft'

export type MeetingErrors = Partial<Record<'title' | 'people' | 'justification', string>>

export const EMAIL = /^[^\s@,]+@[^\s@,]+\.[^\s@,]{2,}$/

export function meetingErrors(draft: BookingDraft, room: { capacity: number; is_private: boolean }): MeetingErrors {
  const errors: MeetingErrors = {}
  if (!draft.title.trim()) errors.title = 'Write a title for the meeting.'
  const people = Number(draft.people)
  if (!Number.isInteger(people) || people < 1) errors.people = 'At least 1 person comes.'
  else if (people > room.capacity) errors.people = `This room has ${room.capacity} seats.`
  if (room.is_private && !draft.justification.trim()) errors.justification = 'Tell the room owner why you need this room.'
  return errors
}
