import { describe, expect, it } from 'vitest'

import { mapSearchUrl } from '../mapLink'

describe('mapSearchUrl', () => {
  it('makes a Google Maps search link from the office map text', () => {
    expect(mapSearchUrl('National Bank of Cambodia, Phnom Penh')).toBe(
      'https://www.google.com/maps/search/?api=1&query=National%20Bank%20of%20Cambodia%2C%20Phnom%20Penh',
    )
  })

  it('works with a "lat,lng" pair', () => {
    expect(mapSearchUrl('11.5564,104.9282')).toBe('https://www.google.com/maps/search/?api=1&query=11.5564%2C104.9282')
  })

  it('gives null when there is no map text', () => {
    expect(mapSearchUrl(null)).toBeNull()
    expect(mapSearchUrl('   ')).toBeNull()
  })
})
