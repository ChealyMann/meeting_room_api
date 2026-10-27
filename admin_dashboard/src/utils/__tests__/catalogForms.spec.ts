import { describe, expect, it } from 'vitest'

import type { CategoryOut } from '../../api/types'
import { emptyRoomTypeForm, roomTypeChanges, roomTypeCreateBody, roomTypeFormOf, roomTypeProblems } from '../catalogForms'

const ROOM_TYPE = {
  id: 2,
  name_en: 'Meeting room',
  name_kh: 'បន្ទប់ប្រជុំ',
  sort_order: 1,
  is_active: true,
  created_at: '2026-10-01T00:00:00Z',
  updated_at: '2026-10-01T00:00:00Z',
} as CategoryOut

describe('room type form', () => {
  it('needs both names', () => {
    expect(roomTypeProblems(emptyRoomTypeForm())).toEqual({
      name_kh: 'Enter the Khmer name.',
      name_en: 'Enter the English name.',
    })
  })

  it('applies the API limits', () => {
    expect(roomTypeProblems({ ...roomTypeFormOf(ROOM_TYPE), name_en: 'x'.repeat(101), sort_order: '10000' })).toEqual({
      name_en: 'Max 100 characters.',
      sort_order: 'Order must be a whole number from 0 to 9999.',
    })
  })

  it('trims, and sends order 0 when it is empty', () => {
    expect(roomTypeCreateBody({ name_kh: ' បន្ទប់ ', name_en: ' Board room ', sort_order: '' })).toEqual({
      name_kh: 'បន្ទប់',
      name_en: 'Board room',
      sort_order: 0,
    })
  })

  it('sends only what changed', () => {
    expect(roomTypeChanges(roomTypeFormOf(ROOM_TYPE), ROOM_TYPE)).toEqual({})
    expect(roomTypeChanges({ ...roomTypeFormOf(ROOM_TYPE), sort_order: '3' }, ROOM_TYPE)).toEqual({ sort_order: 3 })
  })
})
