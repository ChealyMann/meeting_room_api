import { describe, expect, it } from 'vitest'

import { MEETING_TYPE_LABELS, ROUTE_LABELS, statusLabel } from '../bookingLabels'

describe('booking labels', () => {
  it('names every display status in plain words', () => {
    expect(statusLabel('PENDING_PITIKA')).toBe('Waiting for Pitika')
    expect(statusLabel('PENDING_OWNER')).toBe('Waiting for owner')
    expect(statusLabel('SETUP_IN_PROGRESS')).toBe('IT setup')
    expect(statusLabel('COMPLETED')).toBe('Completed')
  })

  it('shows a status it does not know as the code', () => {
    expect(statusLabel('NEW_THING')).toBe('NEW_THING')
  })

  it('names meeting types and routes', () => {
    expect(MEETING_TYPE_LABELS.EXTERNAL_WITH_GOVERNOR).toBe('External, with Governor')
    expect(ROUTE_LABELS.R2).toBe('Private room, owner approves')
  })
})
