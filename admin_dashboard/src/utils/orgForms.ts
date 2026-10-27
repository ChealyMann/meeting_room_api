// The department, division and position forms: their values, the checks before sending (the
// API limits, DSH-G06), and the bodies they send — all fields on create, only what changed on edit.
import type {
  DepartmentCreate,
  DepartmentOut,
  DepartmentUpdate,
  DivisionCreate,
  DivisionOut,
  DivisionUpdate,
} from '../api/types'
import { checkOrder, nameProblems, optional, tooLong } from './formChecks'
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

export interface DivisionForm {
  department_id: number | null
  name_kh: string
  name_en: string
  short_name: string
  sort_order: string
}

export function emptyDivisionForm(departmentId: number | null = null): DivisionForm {
  return { department_id: departmentId, name_kh: '', name_en: '', short_name: '', sort_order: '' }
}

export function divisionFormOf(division: DivisionOut): DivisionForm {
  return {
    department_id: division.department_id,
    name_kh: division.name_kh,
    name_en: division.name_en,
    short_name: division.short_name ?? '',
    sort_order: String(division.sort_order),
  }
}

export function divisionProblems(form: DivisionForm): Record<string, string> {
  const problems: Record<string, string> = {}
  if (form.department_id === null) problems.department_id = 'Choose a department.'
  nameProblems(form, problems)
  tooLong(form.short_name, 20, 'short_name', problems)
  checkOrder(form.sort_order, problems)
  return problems
}

/** POST /divisions. An empty short name is left out; an empty order is sent as 0. */
export function divisionCreateBody(form: DivisionForm): DivisionCreate {
  const body: DivisionCreate = {
    department_id: form.department_id!,
    name_kh: form.name_kh.trim(),
    name_en: form.name_en.trim(),
    sort_order: orderValue(form.sort_order),
  }
  if (optional(form.short_name)) body.short_name = optional(form.short_name)
  return body
}

/** PATCH /divisions/{id}: only what changed. A new department moves the division; a cleared short name is null. */
export function divisionChanges(form: DivisionForm, division: DivisionOut): DivisionUpdate {
  const changes: DivisionUpdate = {}
  if (form.department_id !== null && form.department_id !== division.department_id) changes.department_id = form.department_id
  if (form.name_kh.trim() !== division.name_kh) changes.name_kh = form.name_kh.trim()
  if (form.name_en.trim() !== division.name_en) changes.name_en = form.name_en.trim()
  if (optional(form.short_name) !== optional(division.short_name ?? '')) changes.short_name = optional(form.short_name)
  if (orderValue(form.sort_order) !== division.sort_order) changes.sort_order = orderValue(form.sort_order)
  return changes
}
