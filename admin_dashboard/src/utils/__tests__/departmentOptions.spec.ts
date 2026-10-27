import { describe, expect, it } from 'vitest'

import type { DepartmentOut, LocationOut } from '../../api/types'
import { departmentGroups } from '../departmentOptions'

const office = (id: number, name_en: string, is_active = true) => ({ id, name_en, is_active }) as LocationOut
const department = (id: number, location_id: number, name_en: string, is_active = true) =>
  ({ id, location_id, name_en, is_active }) as DepartmentOut

const OFFICES = [office(3, 'Head Office'), office(6, 'Old Branch', false)]
const DEPARTMENTS = [department(10, 3, 'IT'), department(11, 3, 'HR', false), department(12, 6, 'Audit')]

describe('departmentGroups', () => {
  it('groups active departments under their office, in the office order', () => {
    expect(departmentGroups(DEPARTMENTS, OFFICES, null)).toEqual([
      { label: 'Head Office', options: [{ value: 10, label: 'IT' }] },
      { label: 'Old Branch (off)', options: [{ value: 12, label: 'Audit' }] },
    ])
  })

  it('keeps the chosen department when it is off', () => {
    expect(departmentGroups(DEPARTMENTS, OFFICES, 11)[0]).toEqual({
      label: 'Head Office',
      options: [
        { value: 10, label: 'IT' },
        { value: 11, label: 'HR (off)' },
      ],
    })
  })

  it('shows a chosen department it does not know first', () => {
    expect(departmentGroups(DEPARTMENTS, OFFICES, 99)[0]).toEqual({
      label: '',
      options: [{ value: 99, label: 'Unknown department' }],
    })
  })
})
