import { describe, expect, it } from 'vitest'

import { formatPhnomPenh, phnomPenhClock } from '../time'

describe('formatPhnomPenh', () => {
  it('shows API UTC time as Phnom Penh time (UTC+7)', () => {
    expect(formatPhnomPenh('2026-10-23T06:51:03Z')).toBe('23 Oct 2026, 13:51')
  })

  it('moves to the next day after 17:00 UTC', () => {
    expect(formatPhnomPenh('2026-09-30T17:05:00Z')).toBe('1 Oct 2026, 00:05')
  })

  it('uses three-letter months', () => {
    expect(formatPhnomPenh('2026-09-15T02:00:00Z')).toBe('15 Sep 2026, 09:00')
  })
})

describe('phnomPenhClock', () => {
  it('is 24-hour HH:MM in Phnom Penh', () => {
    expect(phnomPenhClock(new Date('2026-10-23T23:30:00Z'))).toBe('06:30')
    expect(phnomPenhClock(new Date('2026-10-23T17:00:00Z'))).toBe('00:00')
  })
})
