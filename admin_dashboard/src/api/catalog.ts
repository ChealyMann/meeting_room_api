// The catalog: room types (the API's "categories") and equipment.
import type { ApiClient } from './client'
import { toQuery } from './query'
import type {
  CategoryCreate,
  CategoryOut,
  CategoryUpdate,
  EquipmentCreate,
  EquipmentOut,
  EquipmentUpdate,
  Page,
} from './types'

/** The API filters both lists by status and a search over their names only. */
export interface CatalogFilters {
  is_active?: boolean
  search?: string
  page?: number
  size?: number
}

const ROOM_TYPES = '/api/v1/categories'
const EQUIPMENT = '/api/v1/equipment'

export function listRoomTypePage(client: ApiClient, f: CatalogFilters): Promise<Page<CategoryOut>> {
  return client.request<Page<CategoryOut>>('GET', ROOM_TYPES + toQuery({ ...f }))
}
export function getRoomType(client: ApiClient, id: number): Promise<CategoryOut> {
  return client.request<CategoryOut>('GET', `${ROOM_TYPES}/${id}`)
}
export function createRoomType(client: ApiClient, body: CategoryCreate): Promise<CategoryOut> {
  return client.request<CategoryOut>('POST', ROOM_TYPES, { json: body })
}
export function updateRoomType(client: ApiClient, id: number, changes: CategoryUpdate): Promise<CategoryOut> {
  return client.request<CategoryOut>('PATCH', `${ROOM_TYPES}/${id}`, { json: changes })
}

export function listEquipmentPage(client: ApiClient, f: CatalogFilters): Promise<Page<EquipmentOut>> {
  return client.request<Page<EquipmentOut>>('GET', EQUIPMENT + toQuery({ ...f }))
}
export function getEquipment(client: ApiClient, id: number): Promise<EquipmentOut> {
  return client.request<EquipmentOut>('GET', `${EQUIPMENT}/${id}`)
}
export function createEquipment(client: ApiClient, body: EquipmentCreate): Promise<EquipmentOut> {
  return client.request<EquipmentOut>('POST', EQUIPMENT, { json: body })
}
export function updateEquipment(client: ApiClient, id: number, changes: EquipmentUpdate): Promise<EquipmentOut> {
  return client.request<EquipmentOut>('PATCH', `${EQUIPMENT}/${id}`, { json: changes })
}
