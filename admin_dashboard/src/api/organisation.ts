// The organisation: departments (in an office), divisions (in a department) and positions.
import type { ApiClient } from './client'
import { toQuery } from './query'
import type {
  DepartmentCreate,
  DepartmentOut,
  DepartmentUpdate,
  DivisionCreate,
  DivisionOut,
  DivisionUpdate,
  Page,
  PositionCreate,
  PositionOut,
  PositionUpdate,
} from './types'

interface Paging {
  is_active?: boolean
  search?: string
  page?: number
  size?: number
}
export interface DepartmentFilters extends Paging {
  location_id?: number
}
export interface DivisionFilters extends Paging {
  department_id?: number
}
export type PositionFilters = Paging

const DEPARTMENTS = '/api/v1/departments'
const DIVISIONS = '/api/v1/divisions'
const POSITIONS = '/api/v1/positions'

export function listDepartmentPage(client: ApiClient, f: DepartmentFilters): Promise<Page<DepartmentOut>> {
  return client.request<Page<DepartmentOut>>('GET', DEPARTMENTS + toQuery({ ...f }))
}
export function getDepartment(client: ApiClient, id: number): Promise<DepartmentOut> {
  return client.request<DepartmentOut>('GET', `${DEPARTMENTS}/${id}`)
}
export function createDepartment(client: ApiClient, body: DepartmentCreate): Promise<DepartmentOut> {
  return client.request<DepartmentOut>('POST', DEPARTMENTS, { json: body })
}
/** A new `location_id` moves the department; its users' province follows. */
export function updateDepartment(client: ApiClient, id: number, changes: DepartmentUpdate): Promise<DepartmentOut> {
  return client.request<DepartmentOut>('PATCH', `${DEPARTMENTS}/${id}`, { json: changes })
}

export function listDivisionPage(client: ApiClient, f: DivisionFilters): Promise<Page<DivisionOut>> {
  return client.request<Page<DivisionOut>>('GET', DIVISIONS + toQuery({ ...f }))
}
export function getDivision(client: ApiClient, id: number): Promise<DivisionOut> {
  return client.request<DivisionOut>('GET', `${DIVISIONS}/${id}`)
}
export function createDivision(client: ApiClient, body: DivisionCreate): Promise<DivisionOut> {
  return client.request<DivisionOut>('POST', DIVISIONS, { json: body })
}
/** A new `department_id` moves the division, with its users. */
export function updateDivision(client: ApiClient, id: number, changes: DivisionUpdate): Promise<DivisionOut> {
  return client.request<DivisionOut>('PATCH', `${DIVISIONS}/${id}`, { json: changes })
}

export function listPositionPage(client: ApiClient, f: PositionFilters): Promise<Page<PositionOut>> {
  return client.request<Page<PositionOut>>('GET', POSITIONS + toQuery({ ...f }))
}
export function getPosition(client: ApiClient, id: number): Promise<PositionOut> {
  return client.request<PositionOut>('GET', `${POSITIONS}/${id}`)
}
export function createPosition(client: ApiClient, body: PositionCreate): Promise<PositionOut> {
  return client.request<PositionOut>('POST', POSITIONS, { json: body })
}
export function updatePosition(client: ApiClient, id: number, changes: PositionUpdate): Promise<PositionOut> {
  return client.request<PositionOut>('PATCH', `${POSITIONS}/${id}`, { json: changes })
}

/** How many active users are in a department or division, or have a position (turn-off warning). */
export async function countActiveUsers(
  client: ApiClient,
  where: { department_id?: number; division_id?: number; position_id?: number },
): Promise<number> {
  const query = toQuery({ ...where, is_active: true, page: 1, size: 1 })
  return (await client.request<Page<unknown>>('GET', `/api/v1/users${query}`)).total
}
