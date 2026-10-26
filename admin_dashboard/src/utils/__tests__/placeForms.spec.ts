import { describe, expect, it } from 'vitest'

import type { LocationOut } from '../../api/types'
import { emptyOfficeForm, officeChanges, officeCreateBody, officeFormOf, officeProblems } from '../placeForms'

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
