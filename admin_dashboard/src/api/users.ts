// People: users (Admin only) and the six roles.
import type { ApiClient } from './client'
import { toQuery } from './query'
import type { Page, RoleOut, RoleUpdate, UserChanged, UserCreate, UserDetail, UserListItem, UserUpdate } from './types'

export interface UserFilters {
  division_id?: number
  department_id?: number
  position_id?: number
  /** A role code, e.g. PITIKA. */
  role?: string
  province?: string
  search?: string
  is_active?: boolean
  page?: number
  size?: number
}

const USERS = '/api/v1/users'

export function listUserPage(client: ApiClient, f: UserFilters): Promise<Page<UserListItem>> {
  return client.request<Page<UserListItem>>('GET', USERS + toQuery({ ...f }))
}
export function getUser(client: ApiClient, id: number): Promise<UserDetail> {
  return client.request<UserDetail>('GET', `${USERS}/${id}`)
}
/** The new user has no roles and must change the temporary password at first sign-in. */
export function createUser(client: ApiClient, body: UserCreate): Promise<UserDetail> {
  return client.request<UserDetail>('POST', USERS, { json: body })
}
/** Turning a user off clears the rooms they own: `rooms_unassigned` lists them. */
export function updateUser(client: ApiClient, id: number, changes: UserUpdate): Promise<UserChanged> {
  return client.request<UserChanged>('PATCH', `${USERS}/${id}`, { json: changes })
}
/** Replaces every role. Removing Room owner clears the rooms they own (`rooms_unassigned`). */
export function setUserRoles(client: ApiClient, id: number, codes: string[]): Promise<UserChanged> {
  return client.request<UserChanged>('PUT', `${USERS}/${id}/roles`, { json: { role_codes: codes } })
}
/** Signs the user out everywhere; the password is sent exactly as typed. */
export function resetPassword(client: ApiClient, id: number, temporary: string): Promise<void> {
  return client.request<void>('POST', `${USERS}/${id}/reset-password`, { json: { temporary_password: temporary } })
}
export function uploadUserSignature(client: ApiClient, id: number, file: File): Promise<UserDetail> {
  const form = new FormData()
  form.append('file', file)
  return client.request<UserDetail>('PUT', `${USERS}/${id}/signature`, { form })
}
export function deleteUserSignature(client: ApiClient, id: number): Promise<void> {
  return client.request<void>('DELETE', `${USERS}/${id}/signature`)
}

/** The six roles, in seed order (not paged). */
export async function listRoles(client: ApiClient): Promise<RoleOut[]> {
  return (await client.request<{ items: RoleOut[] }>('GET', '/api/v1/roles')).items
}
/** Only the English and Khmer names can change. */
export function updateRole(client: ApiClient, id: number, changes: RoleUpdate): Promise<RoleOut> {
  return client.request<RoleOut>('PATCH', `/api/v1/roles/${id}`, { json: changes })
}
/** How many active users have a role. */
export async function countUsersWithRole(client: ApiClient, code: string): Promise<number> {
  return (await listUserPage(client, { role: code, is_active: true, page: 1, size: 1 })).total
}
