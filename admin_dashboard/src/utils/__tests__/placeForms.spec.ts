import { describe, expect, it } from 'vitest'

import type { BuildingDetail, FloorDetail, LocationOut } from '../../api/types'
import {
  buildingChanges,
  buildingCreateBody,
  buildingFormOf,
  buildingProblems,
  emptyBuildingForm,
  emptyFloorForm,
  floorChanges,
  floorCreateBody,
  floorFormOf,
  floorProblems,
  emptyOfficeForm,
  officeChanges,
  officeCreateBody,
  officeFormOf,
  officeProblems,
} from '../placeForms'

const OFFICE = {
  id: 3,
  name_en: 'Head Office',
  name_kh: 'ការិយាល័យកណ្តាល',
  description: null,
  address: 'Norodom Blvd',
  province: { code: 'PP', name_en: 'Phnom Penh', name_kh: 'ភ្នំពេញ' },
  map_query: null,
  is_active: true,
  created_at: '2026-10-01T00:00:00Z',
  updated_at: '2026-10-01T00:00:00Z',
} as unknown as LocationOut

describe('office form', () => {
  it('needs both names and a province', () => {
    expect(officeProblems(emptyOfficeForm())).toEqual({
      name_kh: 'Enter the Khmer name.',
      name_en: 'Enter the English name.',
      province: 'Choose a province.',
    })
  })

  it('applies the API length limits', () => {
    const form = {
      ...emptyOfficeForm(),
      name_kh: 'x',
      name_en: 'x'.repeat(101),
      province: 'PP',
      address: 'x'.repeat(201),
      map_query: 'x'.repeat(501),
      description: 'x'.repeat(1001),
    }
    expect(officeProblems(form)).toEqual({
      name_en: 'Max 100 characters.',
      address: 'Max 200 characters.',
      map_query: 'Max 500 characters.',
      description: 'Max 1000 characters.',
    })
  })

  it('trims and leaves out empty optional text on create', () => {
    const body = officeCreateBody({ ...emptyOfficeForm(), name_kh: ' ការិយាល័យ ', name_en: ' Head Office ', province: 'PP', address: '  ' })
    expect(body).toEqual({ name_kh: 'ការិយាល័យ', name_en: 'Head Office', province: 'PP' })
  })

  it('sends only what changed, and null for cleared text', () => {
    expect(officeChanges(officeFormOf(OFFICE), OFFICE)).toEqual({})
    expect(officeChanges({ ...officeFormOf(OFFICE), address: '' }, OFFICE)).toEqual({ address: null })
    expect(officeChanges({ ...officeFormOf(OFFICE), province: 'SIEM_REAP' }, OFFICE)).toEqual({ province: 'SIEM_REAP' })
  })
})

const BUILDING = {
  id: 5,
  location_id: 3,
  name_en: 'Tower A',
  name_kh: 'អគារ ក',
  short_name: 'A',
  sort_order: 1,
  is_active: true,
  created_at: '2026-10-01T00:00:00Z',
  updated_at: '2026-10-01T00:00:00Z',
  location: { id: 3, name_en: 'Head Office', name_kh: 'ការិយាល័យកណ្តាល' },
  province: { code: 'PP', name_en: 'Phnom Penh', name_kh: 'ភ្នំពេញ' },
} as unknown as BuildingDetail

describe('building form', () => {
  it('needs an office and both names', () => {
    expect(buildingProblems(emptyBuildingForm())).toEqual({
      location_id: 'Choose an office.',
      name_kh: 'Enter the Khmer name.',
      name_en: 'Enter the English name.',
    })
  })

  it('starts with the given office', () => {
    expect(emptyBuildingForm(3).location_id).toBe(3)
  })

  it('checks the short name and the order', () => {
    const form = { ...buildingFormOf(BUILDING), short_name: 'x'.repeat(21), sort_order: '-1' }
    expect(buildingProblems(form)).toEqual({
      short_name: 'Max 20 characters.',
      sort_order: 'Order must be a whole number from 0.',
    })
    expect(buildingProblems({ ...buildingFormOf(BUILDING), sort_order: '1.5' })).toEqual({
      sort_order: 'Order must be a whole number from 0.',
    })
  })

  it('sends order 0 and leaves out an empty short name on create', () => {
    const body = buildingCreateBody({ ...emptyBuildingForm(3), name_kh: ' អគារ ខ ', name_en: ' Tower B ' })
    expect(body).toEqual({ location_id: 3, name_kh: 'អគារ ខ', name_en: 'Tower B', sort_order: 0 })
  })

  it('moves to another office, and clears the short name with null', () => {
    expect(buildingChanges(buildingFormOf(BUILDING), BUILDING)).toEqual({})
    expect(buildingChanges({ ...buildingFormOf(BUILDING), location_id: 4 }, BUILDING)).toEqual({ location_id: 4 })
    expect(buildingChanges({ ...buildingFormOf(BUILDING), short_name: '', sort_order: '2' }, BUILDING)).toEqual({
      short_name: null,
      sort_order: 2,
    })
  })
})

const FLOOR = {
  id: 7,
  building_id: 5,
  floor_label: '3rd floor',
  sort_order: 3,
  is_active: true,
  created_at: '2026-10-01T00:00:00Z',
  updated_at: '2026-10-01T00:00:00Z',
  building: { id: 5, name_en: 'Tower A', name_kh: 'អគារ ក' },
  location: { id: 3, name_en: 'Head Office', name_kh: 'ការិយាល័យកណ្តាល' },
  province: { code: 'PP', name_en: 'Phnom Penh', name_kh: 'ភ្នំពេញ' },
} as unknown as FloorDetail

describe('floor form', () => {
  it('needs an office, a building and a name', () => {
    expect(floorProblems(emptyFloorForm())).toEqual({
      location_id: 'Choose an office.',
      building_id: 'Choose a building.',
      floor_label: 'Enter the floor name.',
    })
    expect(floorProblems({ ...floorFormOf(FLOOR), floor_label: 'x'.repeat(101), sort_order: 'a' })).toEqual({
      floor_label: 'Max 100 characters.',
      sort_order: 'Order must be a whole number from 0.',
    })
  })

  it('starts with the given office and building', () => {
    expect(emptyFloorForm(3, 5)).toEqual({ location_id: 3, building_id: 5, floor_label: '', sort_order: '' })
  })

  it('sends the building, never the office, on create', () => {
    expect(floorCreateBody({ ...emptyFloorForm(3, 5), floor_label: ' Ground ' })).toEqual({
      building_id: 5,
      floor_label: 'Ground',
      sort_order: 0,
    })
  })

  it('moves with a new building; the office alone is not sent', () => {
    expect(floorChanges(floorFormOf(FLOOR), FLOOR)).toEqual({})
    expect(floorChanges({ ...floorFormOf(FLOOR), location_id: 4, building_id: null }, FLOOR)).toEqual({})
    expect(floorChanges({ ...floorFormOf(FLOOR), location_id: 4, building_id: 8 }, FLOOR)).toEqual({ building_id: 8 })
  })
})
