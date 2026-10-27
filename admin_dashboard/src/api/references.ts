// Lists that fill the selects: offices, buildings, floors, room types, equipment, owners.
// Every status is loaded (except owners), so a select can still show a chosen item that is off.
import type { ApiClient } from './client'
import { toQuery, type QueryValue } from './query'
import type {
  BuildingOut,
  CategoryOut,
  DepartmentOut,
  EquipmentOut,
  FloorOut,
  ItemList,
  LocationOut,
  Page,
  ProvinceRef,
  UserListItem,
} from './types'

const PAGE_SIZE = 100 // the API's maximum

/** Every item of a paged list, fetched 100 at a time. */
export async function listAll<T>(
  client: ApiClient,
  path: string,
  params: Record<string, QueryValue> = {},
): Promise<T[]> {
  const items: T[] = []
  for (let page = 1; ; page++) {
    const result = await client.request<Page<T>>(
      'GET',
      path + toQuery({ ...params, page, size: PAGE_SIZE }),
    )
    items.push(...result.items)
    if (items.length >= result.total || result.items.length === 0) return items
  }
}

export function listOffices(client: ApiClient): Promise<LocationOut[]> {
  return listAll<LocationOut>(client, '/api/v1/locations')
}

/** Every department, of every status (for the grouped department selects). */
export function listDepartments(client: ApiClient): Promise<DepartmentOut[]> {
  return listAll<DepartmentOut>(client, '/api/v1/departments')
}

export function listBuildings(client: ApiClient, locationId?: number): Promise<BuildingOut[]> {
  return listAll<BuildingOut>(client, '/api/v1/buildings', { location_id: locationId })
}

export function listFloors(client: ApiClient, buildingId?: number): Promise<FloorOut[]> {
  return listAll<FloorOut>(client, '/api/v1/floors', { building_id: buildingId })
}

export function listRoomTypes(client: ApiClient): Promise<CategoryOut[]> {
  return listAll<CategoryOut>(client, '/api/v1/categories')
}

export function listEquipment(client: ApiClient): Promise<EquipmentOut[]> {
  return listAll<EquipmentOut>(client, '/api/v1/equipment')
}

export async function listProvinces(client: ApiClient): Promise<ProvinceRef[]> {
  return (await client.request<ItemList<ProvinceRef>>('GET', '/api/v1/provinces')).items
}

/** Users who may own a room: active, with the Room owner role. */
export function listRoomOwners(client: ApiClient): Promise<UserListItem[]> {
  return listAll<UserListItem>(client, '/api/v1/users', { role: 'ROOM_OWNER', is_active: true })
}
