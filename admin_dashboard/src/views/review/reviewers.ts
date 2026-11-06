// Whose To review page it is (spec 2026-11-05-owner-and-it-pages-design, Part A: "like Pitika").
// The page is the same for the Pitika and the room owner; what differs lives here: the API
// calls, the row's process bar, what to check, what approving leads to, and which rooms.
import { api } from '../../api'
import {
  getOwnerSummary,
  getPitikaSummary,
  listOwnerBookingPage,
  listOwnerDecidedPage,
  listPitikaBookingPage,
  listPitikaDecidedPage,
  ownerApprove,
  ownerReject,
  pitikaApprove,
  pitikaReject,
  type BookingFilters,
} from '../../api/bookings'
import type { BookingDetail, BookingListItem, DecidedBookingItem, Page, ReviewSummary, RoomListItem } from '../../api/types'
import { ownerCheckLabels, ownerNextStepText, ownerRowSteps, pitikaNotes } from '../../utils/ownerQueue'
import { checkLabels, nextStepText, rowSteps, type RowStep } from '../../utils/reviewQueue'

export type ReviewerKey = 'pitika' | 'owner'

export interface ReviewLabel {
  kind: string
  text: string
  /** Servings, for food. */
  count?: number
  /** More people than seats. */
  over?: boolean
}

type DecidedFilters = Omit<BookingFilters, 'status' | 'province'> & { decision: 'APPROVED' | 'REJECTED' }

export interface Reviewer {
  key: ReviewerKey
  waitingStatus: 'PENDING_PITIKA' | 'PENDING_OWNER'
  /** The panel's subtitle while the booking waits. */
  waitingLabel: string
  /** The empty queue's line. */
  emptyText: string
  list(f: BookingFilters): Promise<Page<BookingListItem>>
  approve(id: number, body: { notes: string | null; version: number }): Promise<BookingDetail>
  reject(id: number, body: { reason: string; version: number }): Promise<BookingDetail>
  decided(f: DecidedFilters): Promise<Page<DecidedBookingItem>>
  summary(): Promise<ReviewSummary>
  rowSteps(item: BookingListItem): RowStep[]
  /** `seats`: the room's capacity, or null when not known. */
  labels(detail: BookingDetail, seats: number | null): ReviewLabel[]
  nextStepText(detail: BookingDetail): string
  /** One note on amber wash in the panel, or null. */
  panelNote(detail: BookingDetail): string | null
  /** The rooms of the room filter. */
  rooms(all: RoomListItem[], user: { id?: number; province?: { code: string } | null } | null): RoomListItem[]
}

export const REVIEWERS: Record<ReviewerKey, Reviewer> = {
  pitika: {
    key: 'pitika',
    waitingStatus: 'PENDING_PITIKA',
    waitingLabel: 'Waiting for Pitika',
    emptyText: 'New bookings in your province show here.',
    list: (f) => listPitikaBookingPage(api, f),
    approve: (id, body) => pitikaApprove(api, id, body),
    reject: (id, body) => pitikaReject(api, id, body),
    decided: (f) => listPitikaDecidedPage(api, f),
    summary: () => getPitikaSummary(api),
    rowSteps,
    labels: (detail) => checkLabels(detail),
    nextStepText,
    panelNote: (detail) => (detail.route === 'R4' ? 'The owner books their own room: you check the food and IT only.' : null),
    rooms: (all, user) => {
      const province = user?.province?.code
      return all.filter((r) => !province || r.province.code === province)
    },
  },
  owner: {
    key: 'owner',
    waitingStatus: 'PENDING_OWNER',
    waitingLabel: 'Waiting for room owner',
    emptyText: 'Bookings of your rooms show here once the Pitika approves them.',
    list: (f) => listOwnerBookingPage(api, f),
    approve: (id, body) => ownerApprove(api, id, body),
    reject: (id, body) => ownerReject(api, id, body),
    decided: (f) => listOwnerDecidedPage(api, f),
    summary: () => getOwnerSummary(api),
    rowSteps: ownerRowSteps,
    labels: ownerCheckLabels,
    nextStepText: ownerNextStepText,
    panelNote: (detail) => {
      const notes = pitikaNotes(detail)
      return notes ? `The Pitika wrote: “${notes}”` : null
    },
    rooms: (all, user) => all.filter((r) => r.is_private && user?.id !== undefined && r.owner?.id === user.id),
  },
}
