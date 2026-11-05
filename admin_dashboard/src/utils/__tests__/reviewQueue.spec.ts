import { describe, expect, it } from 'vitest'

import type { BookingDetail, BookingListItem } from '../../api/types'
import { listItem } from '../../test-utils/bookings'
import { checkLabels, groupByUrgency, nextStepText, rowSteps, startsIn } from '../reviewQueue'

const TODAY = '2026-11-05' // a Thursday
const on = (id: number, date: string, changes: Record<string, unknown> = {}) =>
  listItem(id, { first_session: { id, date, start_time: '14:00', end_time: '15:30' }, ...changes }) as unknown as BookingListItem

const detail = (changes: Record<string, unknown> = {}) =>
  ({
    ...listItem(12, { route: 'R1', has_it: false }),
    private_justification: null,
    catering: null,
    it: null,
    ...changes,
  }) as unknown as BookingDetail

describe('groupByUrgency', () => {
  it('puts each booking in Today, Tomorrow, This week or Later, in order, dropping empty groups', () => {
    const groups = groupByUrgency(
      [on(1, '2026-11-04'), on(2, '2026-11-05'), on(3, '2026-11-06'), on(4, '2026-11-08'), on(5, '2026-11-09')],
      TODAY,
    )
    expect(groups.map((g) => [g.key, g.label, g.items.map((i) => i.id)])).toEqual([
      ['today', 'Today', [1, 2]],
      ['tomorrow', 'Tomorrow', [3]],
      ['week', 'This week', [4]],
      ['later', 'Later', [5]],
    ])
    expect(groups[0]!.hint).toBe('Decide before they start, or they expire')
    expect(groups.slice(1).map((g) => g.hint)).toEqual(['', '', ''])
  })

  it('leaves out a group with nothing in it', () => {
    expect(groupByUrgency([on(5, '2026-11-20')], TODAY).map((g) => g.key)).toEqual(['later'])
  })
})

describe('startsIn', () => {
  const today14 = on(1, TODAY)
  it('counts hours and minutes to the first session, in Phnom Penh time', () => {
    expect(startsIn(today14, new Date('2026-11-05T02:20:00Z'))).toBe('Starts in 4 h 40 min') // 09:20
    expect(startsIn(today14, new Date('2026-11-05T05:00:00Z'))).toBe('Starts in 2 h') // 12:00
    expect(startsIn(today14, new Date('2026-11-05T06:35:00Z'))).toBe('Starts in 25 min') // 13:35
  })

  it('says Started once the first session has begun', () => {
    expect(startsIn(today14, new Date('2026-11-05T07:00:00Z'))).toBe('Started') // 14:00
    expect(startsIn(on(2, '2026-11-04'), new Date('2026-11-05T02:20:00Z'))).toBe('Started')
  })
})

describe('rowSteps', () => {
  const labels = (changes: Record<string, unknown>) =>
    rowSteps(on(1, TODAY, changes)).map((s) => `${s.label}:${s.state}${s.gap ? ':gap' : ''}`)

  it('starts with Sent done, then a gap into the first step after Pitika', () => {
    expect(labels({ route: 'R1', has_it: false })).toEqual(['Sent:done', 'Confirmed:todo:gap'])
    expect(labels({ route: 'R1', has_it: true })).toEqual(['Sent:done', 'IT setup:todo:gap', 'Confirmed:todo'])
    expect(labels({ route: 'R2', has_it: false })).toEqual(['Sent:done', 'Room owner:todo:gap', 'Confirmed:todo'])
    expect(labels({ route: 'R2', has_it: true })).toEqual(['Sent:done', 'Room owner:todo:gap', 'IT setup:todo', 'Confirmed:todo'])
    expect(labels({ route: 'R4', has_it: true })).toEqual(['Sent:done', 'IT setup:todo:gap', 'Confirmed:todo'])
  })
})

describe('checkLabels', () => {
  it('names what the Pitika approves: private reason, food, IT, owner checks', () => {
    const b = detail({
      route: 'R2',
      private_justification: 'Board members attend',
      catering: { packages: [{ id: 1, name: 'Coffee break' }, { id: 2, name: 'Lunch box' }], servings: 12 },
      it: { items: [{ id: 3, name: 'Projector setup' }, { id: 4, name: 'Microphones' }] },
    })
    expect(checkLabels(b)).toEqual([
      { kind: 'private', text: 'Private · reason given' },
      { kind: 'food', text: 'Coffee break, Lunch box', count: 12 },
      { kind: 'it', text: 'Projector setup, Microphones' },
    ])
  })

  it('says when a private booking has no reason, and marks the owner checking food and IT only', () => {
    expect(checkLabels(detail({ route: 'R2' }))).toEqual([{ kind: 'private', text: 'Private · no reason' }])
    expect(checkLabels(detail({ route: 'R4' }))).toEqual([{ kind: 'r4', text: 'Food and IT only' }])
    expect(checkLabels(detail())).toEqual([])
  })
})

describe('nextStepText', () => {
  it('says what approving leads to, and that the food goes with it', () => {
    expect(nextStepText(detail({ route: 'R2' }))).toBe('It goes to the room owner next.')
    expect(nextStepText(detail({ has_it: true }))).toBe('It goes to IT setup next.')
    expect(nextStepText(detail())).toBe('It is confirmed, with a door pass.')
    expect(nextStepText(detail({ catering: { packages: [], servings: 4 } }))).toBe(
      'It is confirmed, with a door pass. The food is approved with it.',
    )
  })
})
