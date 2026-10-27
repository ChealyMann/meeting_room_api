import { describe, expect, it } from 'vitest'

import { orderProblem, orderValue } from '../sortOrder'

const MESSAGE = 'Order must be a whole number from 0 to 9999.'

describe('sort order', () => {
  it('accepts empty and whole numbers from 0 to 9999', () => {
    for (const text of ['', ' ', '0', '9999', ' 12 ']) expect(orderProblem(text)).toBeNull()
  })

  it('refuses anything else with one message', () => {
    for (const text of ['10000', '-1', '1.5', 'a']) expect(orderProblem(text)).toBe(MESSAGE)
  })

  it('sends empty as 0, the API default', () => {
    expect(orderValue('')).toBe(0)
    expect(orderValue(' 12 ')).toBe(12)
  })
})
