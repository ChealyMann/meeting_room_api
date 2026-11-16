// A booking being made: what the four steps fill in, and the two bodies the API takes.
// It lives only in the page (spec: leaving the flow drops it).
import { reactive } from 'vue'

import type { BookingCheck, BookingCreate } from '../../../api/types'
import { mergeSessions, toMeetingType, toTime, type PickedSession } from '../rules'

export interface BookingDraft {
  step: 1 | 2 | 3 | 4
  sessions: PickedSession[]
  title: string
  external: boolean
  governor: boolean
  people: number
  emails: string[]
  justification: string
  notes: string
  foods: number[]
  foodNote: string
  its: number[]
  itNote: string
}

/** `first`: the time or times picked before the form opened (the room page, Find a room). */
export function useBookingDraft(roomId: number, first?: PickedSession | PickedSession[] | null) {
  const draft = reactive<BookingDraft>({
    step: 1,
    sessions: Array.isArray(first) ? mergeSessions(first) : first ? [first] : [],
    title: '',
    external: false,
    governor: false,
    people: 8,
    emails: [],
    justification: '',
    notes: '',
    foods: [],
    foodNote: '',
    its: [],
    itNote: '',
  })

  const addSession = (s: PickedSession) => {
    draft.sessions = mergeSessions([...draft.sessions, s])
  }
  const removeSession = (s: PickedSession) => {
    draft.sessions = draft.sessions.filter((x) => !(x.date === s.date && x.a === s.a && x.b === s.b))
  }
  const sessionsIn = () =>
    mergeSessions(draft.sessions).map((s) => ({ date: s.date, start_time: toTime(s.a), end_time: toTime(s.b) }))

  const toCheckBody = (): BookingCheck => ({
    room_id: roomId,
    sessions: sessionsIn(),
    has_catering: draft.foods.length > 0,
    has_it: draft.its.length > 0,
  })

  /** Servings are not sent: the API serves one per person (B-25). */
  const toCreateBody = (): BookingCreate => ({
    room_id: roomId,
    sessions: sessionsIn(),
    meeting_title: draft.title.trim(),
    meeting_type: toMeetingType(draft.external, draft.governor),
    meeting_purpose: draft.notes.trim() || null,
    attendees: Number(draft.people),
    participant_emails: [...draft.emails],
    private_justification: draft.justification.trim() || null,
    catering: draft.foods.length ? { package_ids: [...draft.foods], remarks: draft.foodNote.trim() || null } : null,
    it: draft.its.length ? { service_ids: [...draft.its], special_requirements: draft.itNote.trim() || null } : null,
  })

  return { draft, addSession, removeSession, toCheckBody, toCreateBody }
}
