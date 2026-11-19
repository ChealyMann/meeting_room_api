import { describe, expect, it } from 'vitest'

import { holidayMap, holidayTag } from '../holidays'

// Holiday alert on To review (owner, 19 Nov 2026): the Khmer name, and "1/3" when only some of
// the booking's days are holidays.
const LIST = [
  { id: 1, holiday_date: '2026-11-23', name_km: 'បុណ្យអុំទូក', name_en: 'Water Festival', remarks: null, created_at: '', updated_at: '' },
  { id: 2, holiday_date: '2026-11-24', name_km: 'បុណ្យអុំទូក', name_en: 'Water Festival', remarks: null, created_at: '', updated_at: '' },
  { id: 3, holiday_date: '2026-12-10', name_km: 'ទិវាសិទ្ធិមនុស្ស', name_en: null, remarks: null, created_at: '', updated_at: '' },
]
const map = holidayMap(LIST)

describe('holidayTag', () => {
  it('is the Khmer name for a one-day booking on a holiday', () => {
    expect(holidayTag(['2026-11-23'], map)).toEqual({ text: 'បុណ្យអុំទូក', title: 'Mon 23 Nov 2026 is a public holiday: បុណ្យអុំទូក (Water Festival)' })
  })

  it('adds how many of the days are holidays when there are several days', () => {
    expect(holidayTag(['2026-11-24', '2026-11-26', '2026-11-27'], map)?.text).toBe('បុណ្យអុំទូក · 1/3')
    expect(holidayTag(['2026-11-23', '2026-11-24'], map)?.text).toBe('បុណ្យអុំទូក · 2/2')
  })

  it('names the first holiday and leaves out a missing English name', () => {
    expect(holidayTag(['2026-12-10'], map)?.title).toBe('Thu 10 Dec 2026 is a public holiday: ទិវាសិទ្ធិមនុស្ស')
  })

  it('is null when no day is a holiday', () => {
    expect(holidayTag(['2026-11-26'], map)).toBeNull()
    expect(holidayTag([], map)).toBeNull()
  })
})
