import { describe, expect, it } from 'vitest'

import { foodDay } from '../foodDay'

// One delivery: only what foodDay reads.
const d = (time: string) => ({ delivery_time: `${time}:00` })
const DAY = [d('08:00'), d('09:00'), d('12:00'), d('12:00'), d('15:00')]

describe('foodDay', () => {
  it('today: deliveries before now are past, the first time after now is next (every room at it)', () => {
    const f = foodDay(DAY, '2026-11-17', '2026-11-17', '11:20')
    expect(f.states).toEqual(['past', 'past', 'next', 'next', 'later'])
    expect(f.nowAt).toBe(2)
    expect(f.nextAt).toBe('12:00')
  })

  it('today: a delivery at this very minute is next, not past', () => {
    const f = foodDay(DAY, '2026-11-17', '2026-11-17', '12:00')
    expect(f.states.slice(2, 4)).toEqual(['next', 'next'])
  })

  it('today: no now line on top when nothing is past yet', () => {
    const f = foodDay(DAY, '2026-11-17', '2026-11-17', '07:00')
    expect(f.nowAt).toBeNull()
    expect(f.states[0]).toBe('next')
  })

  it('today: the now line goes under the last row when all are past', () => {
    const f = foodDay(DAY, '2026-11-17', '2026-11-17', '16:00')
    expect(f.nowAt).toBe(5)
    expect(f.nextAt).toBeNull()
  })

  it('another day: nothing is past or next, and no now line', () => {
    for (const day of ['2026-11-16', '2026-11-18']) {
      const f = foodDay(DAY, day, '2026-11-17', '11:20')
      expect(f.states.every((s) => s === 'later')).toBe(true)
      expect([f.nowAt, f.nextAt]).toEqual([null, null])
    }
  })
})
