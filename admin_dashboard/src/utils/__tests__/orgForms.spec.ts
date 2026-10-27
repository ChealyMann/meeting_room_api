import { describe, expect, it } from 'vitest'

import type { DepartmentOut } from '../../api/types'
import {
  departmentChanges,
  departmentCreateBody,
  departmentFormOf,
  departmentProblems,
  emptyDepartmentForm,
} from '../orgForms'

const stamps = { is_active: true, created_at: '2026-10-01T00:00:00Z', updated_at: '2026-10-01T00:00:00Z' }
const DEPARTMENT = { id: 3, location_id: 3, name_en: 'IT Department', name_kh: 'នាយកដ្ឋានព័ត៌មានវិទ្យា', sort_order: 1, ...stamps } as DepartmentOut

describe('department form', () => {
  it('needs an office and both names', () => {
    expect(departmentProblems(emptyDepartmentForm())).toEqual({
      location_id: 'Choose an office.',
      name_kh: 'Enter the Khmer name.',
      name_en: 'Enter the English name.',
    })
    expect(emptyDepartmentForm(3).location_id).toBe(3)
  })

  it('checks the order', () => {
    expect(departmentProblems({ ...departmentFormOf(DEPARTMENT), sort_order: '10000' })).toEqual({
      sort_order: 'Order must be a whole number from 0 to 9999.',
    })
  })

  it('sends order 0 when it is empty', () => {
    expect(departmentCreateBody({ location_id: 3, name_kh: ' ក ', name_en: ' Audit ', sort_order: '' })).toEqual({
      location_id: 3,
      name_kh: 'ក',
      name_en: 'Audit',
      sort_order: 0,
    })
  })

  it('moves with a new office, and sends only what changed', () => {
    expect(departmentChanges(departmentFormOf(DEPARTMENT), DEPARTMENT)).toEqual({})
    expect(departmentChanges({ ...departmentFormOf(DEPARTMENT), location_id: 5 }, DEPARTMENT)).toEqual({ location_id: 5 })
  })
})
