import { describe, expect, it } from 'vitest'

import type { RoomDetail } from '../../api/types'
import { emptyRoomForm, roomChanges, roomCreateBody, roomFormOf, roomProblems, type RoomForm } from '../roomForm'

const ROOM = {
  id: 12,
  name_en: 'Mekong Room',
  name_kh: 'បន្ទប់មេគង្គ',
  short_desc: 'Small meetings',
  description: null,
  capacity: 12,
  size_sqm: 40,
  start_time: '08:00',
  end_time: '17:00',
  category: { id: 1, name_en: 'Meeting room', name_kh: 'បន្ទប់ប្រជុំ' },
  floor: { id: 7, floor_label: '3rd floor' },
  building: { id: 5, name_en: 'Building A', name_kh: 'អគារ A', short_name: null },
  location: { id: 3, name_en: 'Head Office', name_kh: 'ការិយាល័យកណ្តាល' },
  province: { code: 'PP', name_en: 'Phnom Penh', name_kh: 'ភ្នំពេញ' },
  owner: { id: 2, name_en: 'Sok Dara', name_kh: 'សុខ ដារា' },
  cover_photo: null,
  is_active: true,
  is_bookable: true,
  is_private: false,
  photos: [],
  equipment: [],
  created_at: '2026-10-01T00:00:00Z',
  updated_at: '2026-10-01T00:00:00Z',
} as unknown as RoomDetail

const valid = (changes: Partial<RoomForm> = {}): RoomForm => ({
  ...emptyRoomForm(),
  name_kh: 'បន្ទប់មេគង្គ',
  name_en: 'Mekong Room',
  location_id: 3,
  building_id: 5,
  floor_id: 7,
  category_id: 1,
  capacity: '12',
  ...changes,
})

describe('roomProblems', () => {
  it('lists every missing required field', () => {
    expect(roomProblems(emptyRoomForm())).toEqual({
      name_kh: 'Enter the Khmer name.',
      name_en: 'Enter the English name.',
      location_id: 'Choose an office.',
      building_id: 'Choose a building.',
      floor_id: 'Choose a floor.',
      category_id: 'Choose a room type.',
      capacity: 'Seats must be a whole number from 1 to 10000.',
    })
  })

  it('finds nothing wrong with a complete form', () => {
    expect(roomProblems(valid())).toEqual({})
  })

  it.each(['0', '10001', '2.5', 'ten'])('refuses %s seats', (capacity) => {
    expect(roomProblems(valid({ capacity })).capacity).toBe(
      'Seats must be a whole number from 1 to 10000.',
    )
  })

  it('checks the optional size only when given', () => {
    expect(roomProblems(valid({ size_sqm: '' }))).toEqual({})
    expect(roomProblems(valid({ size_sqm: '100001' })).size_sqm).toBe(
      'Size must be a whole number from 1 to 100000.',
    )
  })

  it('needs opening before closing, in HH:MM', () => {
    expect(roomProblems(valid({ start_time: '17:00', end_time: '08:00' })).end_time).toBe(
      'Opening must be before closing.',
    )
    expect(roomProblems(valid({ start_time: '08:00', end_time: '08:00' })).end_time).toBe(
      'Opening must be before closing.',
    )
    expect(roomProblems(valid({ start_time: '24:00' })).start_time).toBe('Use HH:MM, for example 08:00.')
  })

  it('applies the API length limits', () => {
    const problems = roomProblems(
      valid({
        name_en: 'x'.repeat(101),
        short_desc: 'x'.repeat(201),
        description: 'x'.repeat(1001),
        door_code: 'x'.repeat(51),
      }),
    )
    expect(problems).toEqual({
      name_en: 'Max 100 characters.',
      short_desc: 'Max 200 characters.',
      description: 'Max 1000 characters.',
      door_code: 'Max 50 characters.',
    })
  })
})

describe('roomCreateBody', () => {
  it('trims text, parses numbers and leaves out empty optional fields', () => {
    expect(roomCreateBody(valid({ name_en: '  Mekong Room ', capacity: '12' }))).toEqual({
      name_kh: 'បន្ទប់មេគង្គ',
      name_en: 'Mekong Room',
      floor_id: 7,
      category_id: 1,
      capacity: 12,
      start_time: '08:00',
      end_time: '17:00',
      is_private: false,
    })
  })

  it('sends the optional fields that are filled in', () => {
    const body = roomCreateBody(
      valid({ size_sqm: '40', short_desc: 'Small', door_code: '4821#', room_owner_id: 2, is_private: true }),
    )
    expect(body).toMatchObject({ size_sqm: 40, short_desc: 'Small', door_code: '4821#', room_owner_id: 2, is_private: true })
  })
})

describe('roomChanges', () => {
  it('is empty when nothing changed', () => {
    expect(roomChanges(roomFormOf(ROOM), ROOM)).toEqual({})
  })

  it('never shows or sends the door code unless one is typed', () => {
    const form = roomFormOf(ROOM)
    expect(form.door_code).toBe('')

    form.door_code = ''
    expect(roomChanges(form, ROOM)).toEqual({})

    form.door_code = '4821#'
    expect(roomChanges(form, ROOM)).toEqual({ door_code: '4821#' })
  })

  it('sends null for a cleared optional field', () => {
    expect(roomChanges({ ...roomFormOf(ROOM), short_desc: '   ' }, ROOM)).toEqual({ short_desc: null })
    expect(roomChanges({ ...roomFormOf(ROOM), room_owner_id: null }, ROOM)).toEqual({ room_owner_id: null })
  })

  it('sends only the new floor when the place changes', () => {
    expect(roomChanges({ ...roomFormOf(ROOM), location_id: 4, building_id: 6, floor_id: 9 }, ROOM)).toEqual({
      floor_id: 9,
    })
  })
})
