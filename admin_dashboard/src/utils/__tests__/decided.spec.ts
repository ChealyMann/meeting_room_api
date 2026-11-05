import { describe, expect, it } from 'vitest'

import type { DecidedBookingItem } from '../../api/types'
import { listItem } from '../../test-utils/bookings'
import { decidedTime, groupByDecisionDay, nowPill, ringArcs, summaryLine, tabFrom } from '../decided'

const decided = (id: number, decided_at: string, changes: Record<string, unknown> = {}) =>
  ({ ...listItem(id, changes), decided_at, decision_note: null }) as unknown as DecidedBookingItem

describe('groupByDecisionDay', () => {
  it('groups by the Phnom Penh day of the decision, newest first, keeping the API order', () => {
    const items = [
      decided(1, '2026-11-05T06:38:00Z'),
      decided(2, '2026-11-04T17:10:00Z'), // 00:10 on 5 Nov in Phnom Penh
      decided(3, '2026-11-04T16:50:00Z'), // 23:50 on 4 Nov in Phnom Penh
      decided(4, '2026-11-02T03:00:00Z'),
    ]

    const groups = groupByDecisionDay(items, '2026-11-05')

    expect(groups.map((g) => [g.label, g.items.map((b) => b.id)])).toEqual([
      ['Today · Thu 5 Nov', [1, 2]],
      ['Yesterday · Wed 4 Nov', [3]],
      ['Mon 2 Nov', [4]],
    ])
    expect(groups.map((g) => g.key)).toEqual(['2026-11-05', '2026-11-04', '2026-11-02'])
  })

  it('shows the year for a day in another year', () => {
    const groups = groupByDecisionDay([decided(1, '2025-12-30T03:00:00Z')], '2026-01-05')
    expect(groups[0]!.label).toBe('Tue 30 Dec 2025')
  })
})

describe('nowPill', () => {
  it.each([
    ['PENDING_OWNER', 'Room owner next', 'warn'],
    ['SETUP_IN_PROGRESS', 'IT setup', 'plain'],
    ['CONFIRMED', 'Confirmed', 'ok'],
    ['COMPLETED', 'Completed', 'plain'],
    ['CANCELLED', 'Cancelled', 'plain'],
    ['REJECTED', 'Rejected', 'no'],
  ])('%s → %s (%s)', (status, text, tone) => {
    expect(nowPill(decided(1, '2026-11-05T06:38:00Z', { display_status: status }))).toEqual({ text, tone })
  })
})

describe('summaryLine', () => {
  it.each([
    [{ waiting: 3, approved_today: 5, rejected_today: 1 }, 'Today you decided 6 · 3 still waiting'],
    [{ waiting: 0, approved_today: 5, rejected_today: 1 }, 'Today you decided 6 · nothing waiting'],
    [{ waiting: 3, approved_today: 0, rejected_today: 0 }, 'Nothing decided yet today · 3 waiting'],
    [{ waiting: 0, approved_today: 0, rejected_today: 0 }, 'Nothing decided yet today · nothing waiting'],
  ])('%j → %s', (summary, line) => {
    expect(summaryLine(summary)).toBe(line)
  })
})

describe('ringArcs', () => {
  it('gives the parts of the whole day and the label', () => {
    expect(ringArcs({ waiting: 3, approved_today: 5, rejected_today: 1 })).toEqual({ approved: 5 / 9, rejected: 1 / 9, label: '6/9' })
  })

  it('is empty, not NaN, when there is nothing', () => {
    expect(ringArcs({ waiting: 0, approved_today: 0, rejected_today: 0 })).toEqual({ approved: 0, rejected: 0, label: '0/0' })
  })
})

describe('tabFrom', () => {
  it('reads the tab from the address, Waiting by default', () => {
    expect(tabFrom('approved')).toBe('approved')
    expect(tabFrom('rejected')).toBe('rejected')
    expect(tabFrom(['rejected'])).toBe('rejected')
    expect(tabFrom('x')).toBe('waiting')
    expect(tabFrom(undefined)).toBe('waiting')
  })
})

describe('decidedTime', () => {
  it('is the Phnom Penh time of the decision', () => {
    expect(decidedTime(decided(1, '2026-11-05T06:38:00Z'))).toBe('13:38')
  })
})
