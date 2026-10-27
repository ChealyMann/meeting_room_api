// The department, division and position forms: their values, the checks before sending (the
// API limits, DSH-G06), and the bodies they send — all fields on create, only what changed on edit.
import type { DepartmentCreate, DepartmentOut, DepartmentUpdate } from '../api/types'
import { checkOrder, nameProblems } from './formChecks'
import { orderValue } from './sortOrder'

export interface DepartmentForm {
  location_id: number | null
  name_kh: string
  name_en: string
  sort_order: string
}

export function emptyDepartmentForm(locationId: number | null = null): DepartmentForm {
  return { location_id: locationId, name_kh: '', name_en: '', sort_order: '' }
}

export function departmentFormOf(department: DepartmentOut): DepartmentForm {
  return {
    location_id: department.location_id,
    name_kh: department.name_kh,
    name_en: department.name_en,
    sort_order: String(department.sort_order),
  }
}

/** Problems to show before sending, by field. Empty when the form can be sent. */
export function departmentProblems(form: DepartmentForm): Record<string, string> {
  const problems: Record<string, string> = {}
  if (form.location_id === null) problems.location_id = 'Choose an office.'
  nameProblems(form, problems)
  checkOrder(form.sort_order, problems)
  return problems
}

/** POST /departments. An empty order is sent as 0, the API's default. */
export function departmentCreateBody(form: DepartmentForm): DepartmentCreate {
  return {
    location_id: form.location_id!,
    name_kh: form.name_kh.trim(),
    name_en: form.name_en.trim(),
    sort_order: orderValue(form.sort_order),
  }
}

/** PATCH /departments/{id}: only what changed. A new office moves the department. */
export function departmentChanges(form: DepartmentForm, department: DepartmentOut): DepartmentUpdate {
  const changes: DepartmentUpdate = {}
  if (form.location_id !== null && form.location_id !== department.location_id) changes.location_id = form.location_id
  if (form.name_kh.trim() !== department.name_kh) changes.name_kh = form.name_kh.trim()
  if (form.name_en.trim() !== department.name_en) changes.name_en = form.name_en.trim()
  if (orderValue(form.sort_order) !== department.sort_order) changes.sort_order = orderValue(form.sort_order)
  return changes
}
