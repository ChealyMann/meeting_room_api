import { describe, expect, it } from 'vitest'

import type { BookingDetail } from '../../api/types'
import { listItem } from '../../test-utils/bookings'
import { buildHistory } from '../bookingHistory'

// Times are UTC, as the API sends them; the history shows Phnom Penh time (UTC+7).
const SENT = '2026-11-04T01:36:00Z' // 08:36
const LATER = '2026-11-04T04:00:00Z' // 11:00
const NEXT_DAY = '2026-11-05T00:49:00Z' // 07:49

const booking = (changes: Record<string, unknown> = {}) =>
  ({
    ...listItem(12, { created_at: SENT, requester: { id: 4, name_en: 'Touch Bunthoeun', name_kh: '' } }),
    requester_info: {},
    meeting_purpose: null,
    private_justification: null,
    participant_emails: [],
    sessions: [],
    last_end: { date: '2026-11-10', time: '10:30' },
    catering: null,
    it: null,
    reviews: [],
    rejection: null,
    cancelled_at: null,
    cancel_reason: null,
    cancelled_by: null,
    updated_at: SENT,
    ...changes,
  }) as unknown as BookingDetail

const review = (stage: string, decision: string, at: string, name: string, extra: Record<string, unknown> = {}) => ({
  stage,
  decision,
  reviewer: { id: name.length, name_en: name },
  notes: null,
  reviewed_at: at,
  by_admin: false,
  ...extra,
})
const it_ = (changes: Record<string, unknown> = {}) => ({
  ticket_id: 1,
  items: [],
  special_requirements: null,
  status: 'RECEIVED',
  technician_notes: null,
  staff: [],
  setup_date: '2026-11-10',
  setup_time: '08:30',
  forwarded_at: null,
  assigned_at: null,
  ready_at: null,
  ...changes,
})

const bar = (b: BookingDetail) => buildHistory(b).steps.map((s) => `${s.label}:${s.state}`)
const rows = (b: BookingDetail) => buildHistory(b).events.map((e) => e.label)

describe('buildHistory', () => {
  it('waits for Pitika on a shared room', () => {
    const b = booking()

    expect(bar(b)).toEqual(['Sent:done', 'Pitika:now', 'Confirmed:todo'])
    const events = buildHistory(b).events
    expect(events.map((e) => e.label)).toEqual(['Sent', 'Waiting for Pitika'])
    expect(events[0]).toMatchObject({ at: '4 Nov 2026, 08:36', name: 'Touch Bunthoeun', role: 'booker' })
    expect(events[1]).toMatchObject({ kind: 'waiting', at: null, role: 'pitika' })
  })

  it('goes from Pitika to the owner on a private room', () => {
    const b = booking({
      route: 'R2',
      status: 'PENDING_OWNER',
      display_status: 'PENDING_OWNER',
      reviews: [review('PITIKA', 'APPROVED', LATER, 'Chan Sophea', { notes: 'Looks fine.' })],
    })

    expect(bar(b)).toEqual(['Sent:done', 'Pitika:done', 'Room owner:now', 'Confirmed:todo'])
    expect(rows(b)).toEqual(['Sent', 'Approved', 'Waiting for the room owner'])
    expect(buildHistory(b).events[1]).toMatchObject({ name: 'Chan Sophea', role: 'pitika', note: 'Looks fine.' })
  })

  it('shows the IT steps while IT gets ready', () => {
    const b = booking({
      has_it: true,
      status: 'SETUP_IN_PROGRESS',
      display_status: 'SETUP_IN_PROGRESS',
      reviews: [review('PITIKA', 'APPROVED', LATER, 'Chan Sophea')],
      it: it_({ status: 'ASSIGNED', forwarded_at: LATER, assigned_at: NEXT_DAY, staff: [{ id: 8, name_en: 'Sok Pisey' }] }),
    })

    expect(bar(b)).toEqual(['Sent:done', 'Pitika:done', 'IT setup:now', 'Confirmed:todo'])
    expect(rows(b)).toEqual(['Sent', 'Approved', 'Sent to IT', 'Staff assigned', 'Waiting for IT to be ready'])
    expect(buildHistory(b).events[3]).toMatchObject({ role: 'it', name: null, note: 'Staff: Sok Pisey' })
  })

  it('confirms when the last review is made, then ends after the meeting', () => {
    const b = booking({
      status: 'CONFIRMED',
      display_status: 'COMPLETED',
      reviews: [review('PITIKA', 'APPROVED', LATER, 'Chan Sophea')],
      last_end: { date: '2026-11-10', time: '10:30' },
    })

    expect(bar(b)).toEqual(['Sent:done', 'Pitika:done', 'Confirmed:done', 'Ended:done'])
    expect(rows(b)).toEqual(['Sent', 'Approved', 'Confirmed · door pass ready', 'Meeting ended'])
    const events = buildHistory(b).events
    expect(events[2]).toMatchObject({ at: '4 Nov 2026, 11:00', role: 'system' })
    expect(events[3]).toMatchObject({ at: '10 Nov 2026, 10:30', role: null })
  })

  it('confirms after IT is ready when IT was asked', () => {
    const b = booking({
      has_it: true,
      status: 'CONFIRMED',
      display_status: 'CONFIRMED',
      reviews: [review('PITIKA', 'APPROVED', SENT, 'Chan Sophea')],
      it: it_({ status: 'READY', forwarded_at: SENT, assigned_at: LATER, ready_at: NEXT_DAY }),
    })

    expect(bar(b)).toEqual(['Sent:done', 'Pitika:done', 'IT setup:done', 'Confirmed:done'])
    expect(rows(b)).toEqual(['Sent', 'Approved', 'Sent to IT', 'Staff assigned', 'IT ready', 'Confirmed · door pass ready'])
    expect(buildHistory(b).events.at(-1)!.at).toBe('5 Nov 2026, 07:49')
  })

  it('has no confirm row when the system confirmed without IT being ready', () => {
    const b = booking({
      has_it: true,
      status: 'CONFIRMED',
      display_status: 'CONFIRMED',
      reviews: [review('PITIKA', 'APPROVED', SENT, 'Chan Sophea')],
      it: it_({ forwarded_at: SENT }),
    })

    expect(bar(b)).toEqual(['Sent:done', 'Pitika:done', 'IT setup:done', 'Confirmed:done'])
    expect(rows(b)).toEqual(['Sent', 'Approved', 'Sent to IT'])
  })

  it("confirms the owner's own room at once, with Pitika not needed", () => {
    const b = booking({
      route: 'R3',
      status: 'CONFIRMED',
      display_status: 'CONFIRMED',
      reviews: [{ ...review('PITIKA', 'NOT_REQUIRED', SENT, 'x'), reviewer: null }],
    })

    expect(bar(b)).toEqual(['Sent:done', 'Confirmed:done'])
    expect(rows(b)).toEqual(['Sent', 'Pitika not needed', 'Confirmed · door pass ready'])
    expect(buildHistory(b).events[1]).toMatchObject({ role: 'system', name: null })
  })

  it('stops at the owner who rejected, and shows the rejection once', () => {
    const reason = 'The Governor uses this room that afternoon.'
    const b = booking({
      route: 'R2',
      status: 'REJECTED',
      display_status: 'REJECTED',
      reviews: [
        review('PITIKA', 'APPROVED', LATER, 'Chan Sophea'),
        review('OWNER', 'REJECTED', NEXT_DAY, 'Keo Vanna', { notes: reason }),
      ],
      rejection: { rejected_by: 'OWNER', actor: { id: 5, name_en: 'Keo Vanna' }, reason, decided_at: NEXT_DAY, by_admin: false },
    })

    expect(bar(b)).toEqual(['Sent:done', 'Pitika:done', 'Room owner:stop', 'Confirmed:todo'])
    expect(rows(b)).toEqual(['Sent', 'Approved', 'Rejected'])
    expect(buildHistory(b).events[2]).toMatchObject({ name: 'Keo Vanna', role: 'owner', note: reason })
  })

  it('marks an expired booking as stopped by the system at the review nobody made', () => {
    const b = booking({
      status: 'REJECTED',
      display_status: 'REJECTED',
      rejection: {
        rejected_by: 'SYSTEM',
        actor: null,
        reason: 'Expired: not approved before the meeting time.',
        decided_at: LATER,
        by_admin: false,
      },
    })

    expect(bar(b)).toEqual(['Sent:done', 'Pitika:stop', 'Confirmed:todo'])
    expect(buildHistory(b).events[1]).toMatchObject({ kind: 'expired', label: 'Expired', role: 'system', name: null })
  })

  it('names the booker who cancelled their own booking', () => {
    const b = booking({
      status: 'CANCELLED',
      display_status: 'CANCELLED',
      cancelled_at: LATER,
      cancel_reason: 'The match moved.',
      cancelled_by: { id: 4, name_en: 'Touch Bunthoeun' },
    })

    expect(bar(b)).toEqual(['Sent:done', 'Cancelled:stop'])
    expect(buildHistory(b).events[1]).toMatchObject({ label: 'Cancelled', role: 'booker', note: 'The match moved.' })
  })

  it('shows the Admin standing in for the owner, then cancelling', () => {
    const b = booking({
      route: 'R2',
      status: 'CANCELLED',
      display_status: 'CANCELLED',
      reviews: [
        review('PITIKA', 'APPROVED', SENT, 'Chan Sophea'),
        review('OWNER', 'APPROVED', NEXT_DAY, 'Mann Chealy', { by_admin: true }),
      ],
      cancelled_at: NEXT_DAY,
      cancelled_by: { id: 3, name_en: 'Mann Chealy' },
    })

    expect(bar(b)).toEqual(['Sent:done', 'Pitika:done', 'Room owner:done', 'Confirmed:done', 'Cancelled:stop'])
    const events = buildHistory(b).events
    expect(events.map((e) => e.label)).toEqual(['Sent', 'Approved', 'Approved', 'Confirmed · door pass ready', 'Cancelled'])
    expect(events[2]).toMatchObject({ name: 'Mann Chealy', role: 'admin', forRole: 'owner' })
    expect(events[4]).toMatchObject({ name: 'Mann Chealy', role: 'admin' })
  })

  it('shows the Admin rejecting for Pitika', () => {
    const b = booking({
      status: 'REJECTED',
      display_status: 'REJECTED',
      rejection: { rejected_by: 'PITIKA', actor: { id: 3, name_en: 'Mann Chealy' }, reason: 'No.', decided_at: LATER, by_admin: true },
    })

    expect(buildHistory(b).events[1]).toMatchObject({ role: 'admin', forRole: 'pitika', note: 'No.' })
  })

  it('says the system cancelled when nobody is named', () => {
    const b = booking({ status: 'CANCELLED', display_status: 'CANCELLED', cancelled_at: LATER, cancelled_by: null })

    expect(buildHistory(b).events[1]).toMatchObject({ label: 'Cancelled', role: 'system', name: null })
  })
})
