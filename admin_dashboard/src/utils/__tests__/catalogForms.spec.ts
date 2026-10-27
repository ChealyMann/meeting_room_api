import { describe, expect, it } from 'vitest'

import type { CategoryOut, EquipmentOut } from '../../api/types'
import {
  emptyEquipmentForm,
  emptyRoomTypeForm,
  equipmentChanges,
  equipmentCreateBody,
  equipmentFormOf,
  equipmentProblems,
  roomTypeChanges,
  roomTypeCreateBody,
  roomTypeFormOf,
  roomTypeProblems,
} from '../catalogForms'

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

const ITEM = {
  id: 4,
  name: 'Projector',
  icon: 'old-icon',
  sort_order: 2,
  is_active: true,
  created_at: '2026-10-01T00:00:00Z',
  updated_at: '2026-10-01T00:00:00Z',
} as EquipmentOut

describe('equipment form', () => {
  it('needs a name, and applies the API limits', () => {
    expect(equipmentProblems(emptyEquipmentForm())).toEqual({ name: 'Enter the name.' })
    expect(equipmentProblems({ ...equipmentFormOf(ITEM), name: 'x'.repeat(201), sort_order: '-1' })).toEqual({
      name: 'Max 200 characters.',
      sort_order: 'Order must be a whole number from 0 to 9999.',
    })
  })

  it('leaves out a missing icon on create', () => {
    expect(equipmentCreateBody({ name: ' Screen ', icon: null, sort_order: '' })).toEqual({ name: 'Screen', sort_order: 0 })
    expect(equipmentCreateBody({ name: 'Projector', icon: 'projector', sort_order: '1' })).toEqual({
      name: 'Projector',
      icon: 'projector',
      sort_order: 1,
    })
  })

  it('keeps an unknown icon unless it is changed, and clears it with null', () => {
    expect(equipmentChanges(equipmentFormOf(ITEM), ITEM)).toEqual({})
    expect(equipmentChanges({ ...equipmentFormOf(ITEM), name: 'Screen' }, ITEM)).toEqual({ name: 'Screen' })
    expect(equipmentChanges({ ...equipmentFormOf(ITEM), icon: null }, ITEM)).toEqual({ icon: null })
    expect(equipmentChanges({ ...equipmentFormOf(ITEM), icon: 'tv' }, ITEM)).toEqual({ icon: 'tv' })
  })
})
