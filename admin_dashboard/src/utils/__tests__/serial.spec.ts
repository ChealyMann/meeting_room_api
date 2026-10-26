import { describe, expect, it } from 'vitest'

import { serial } from '../serial'

describe('serial', () => {
  it('pads ids to four digits after the prefix and a middle dot', () => {
    expect(serial('RM', 12)).toBe('RM·0012')
    expect(serial('RM', 123456)).toBe('RM·123456')
  })

  it('marks a record that has no id yet', () => {
    expect(serial('RM', null)).toBe('RM·new')
  })
})
