import { describe, expect, it } from 'vitest'

import type { BookingDetail, BookingListItem } from '../../api/types'
import { listItem } from '../../test-utils/bookings'
import { ownerCheckLabels, ownerNextStepText, ownerRowSteps, pitikaNotes } from '../ownerQueue'

const item = (changes: Record<string, unknown> = {}) => listItem(21, { route: 'R2', status: 'PENDING_OWNER', ...changes }) as unknown as BookingListItem
const review = (notes: string | null, by_admin = false) => ({
  stage: 'PITIKA',
  decision: 'APPROVED',
  reviewer: { id: 9, name_en: 'Chan Sophea' },
  notes,
  reviewed_at: '2026-11-05T02:00:00Z',
  by_admin,
})
const detail = (changes: Record<string, unknown> = {}) =>
  ({
    ...item(),
    attendees: 10,
    meeting_type: 'INTERNAL',
    private_justification: 'Board members attend',
    reviews: [review(null)],
    catering: null,
    it: null,
    ...changes,
  }) as unknown as BookingDetail

describe('ownerRowSteps', () => {
  it('shows Sent and Pitika done, then the gap into Confirmed when there is no IT', () => {
    expect(ownerRowSteps(item({ has_it: false }))).toEqual([
      { label: 'Sent', state: 'done' },
      { label: 'Pitika', state: 'done' },
      { label: 'Confirmed', state: 'todo', gap: true },
    ])
  })

  it('puts IT setup after the gap when IT help was asked', () => {
    expect(ownerRowSteps(item({ has_it: true }))).toEqual([
      { label: 'Sent', state: 'done' },
      { label: 'Pitika', state: 'done' },
      { label: 'IT setup', state: 'todo', gap: true },
      { label: 'Confirmed', state: 'todo' },
    ])
  })
})

describe('ownerNextStepText', () => {
  it('says what approving leads to', () => {
    expect(ownerNextStepText(detail({ has_it: false }))).toBe('It is confirmed, with a door pass.')
    expect(ownerNextStepText(detail({ has_it: true }))).toBe('It goes to IT setup next.')
  })
})

describe('ownerCheckLabels', () => {
  it('shows the private reason, the Governor, people vs seats and the Pitika notes', () => {
    const labels = ownerCheckLabels(
      detail({ attendees: 25, meeting_type: 'EXTERNAL_WITH_GOVERNOR', reviews: [review('Check the projector')] }),
      20,
    )
    expect(labels).toEqual([
      { kind: 'private', text: 'Private · reason given' },
      { kind: 'governor', text: 'With Governor' },
      { kind: 'seats', text: '25 people · 20 seats', over: true },
      { kind: 'pitika-notes', text: 'Pitika notes' },
    ])
  })

  it('says when no reason was given and when the people fit', () => {
    const labels = ownerCheckLabels(detail({ private_justification: null, attendees: 10 }), 20)
    expect(labels).toEqual([
      { kind: 'private', text: 'Private · no reason' },
      { kind: 'seats', text: '10 people · 20 seats' },
    ])
  })

  it('leaves the seats out when the room size is not known', () => {
    const texts = ownerCheckLabels(detail({ attendees: 25 }), null).map((l) => l.text)
    expect(texts).toEqual(['Private · reason given'])
    expect(texts.join(' ')).not.toMatch(/NaN|undefined|null/)
  })

  it('shows no food or IT label', () => {
    const labels = ownerCheckLabels(detail({ catering: { packages: [{ name: 'Lunch box' }], servings: 10 }, it: { items: [{ name: 'Projector' }] } }), 20)
    expect(labels.map((l) => l.kind)).toEqual(['private', 'seats'])
  })
})

describe('pitikaNotes', () => {
  it('reads the notes of the Pitika approval, also an Admin backup one', () => {
    expect(pitikaNotes(detail({ reviews: [review('Check the projector', true)] }))).toBe('Check the projector')
    expect(ownerCheckLabels(detail({ reviews: [review('Check the projector', true)] }), 20).map((l) => l.kind)).toContain('pitika-notes')
  })

  it('is null without notes', () => {
    expect(pitikaNotes(detail({ reviews: [review(null)] }))).toBeNull()
    expect(pitikaNotes(detail({ reviews: [review('   ')] }))).toBeNull()
    expect(pitikaNotes(detail({ reviews: [] }))).toBeNull()
  })
})
