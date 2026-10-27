// Places: offices (the API's "locations"), buildings and floors.
import type { ApiClient } from './client'
import { toQuery } from './query'
import { listRooms } from './rooms'
import type {
  BuildingCreate,
  BuildingDetail,
  BuildingOut,
  BuildingUpdate,
  FloorCreate,
  FloorDetail,
  FloorOut,
  FloorUpdate,
  LocationCreate,
  LocationOut,
  LocationUpdate,
  Page,
} from './types'

interface Paging {
  is_active?: boolean
  search?: string
  page?: number
  size?: number
}

export interface OfficeFilters extends Paging {
  province?: string
}
export interface BuildingFilters extends Paging {
  location_id?: number
}
export interface FloorFilters extends Paging {
  location_id?: number
  building_id?: number
}

const OFFICES = '/api/v1/locations'
const BUILDINGS = '/api/v1/buildings'
const FLOORS = '/api/v1/floors'

export function listOfficePage(client: ApiClient, f: OfficeFilters): Promise<Page<LocationOut>> {
  return client.request<Page<LocationOut>>('GET', OFFICES + toQuery({ ...f }))
}
export function getOffice(client: ApiClient, id: number): Promise<LocationOut> {
  return client.request<LocationOut>('GET', `${OFFICES}/${id}`)
}
export function createOffice(client: ApiClient, body: LocationCreate): Promise<LocationOut> {
  return client.request<LocationOut>('POST', OFFICES, { json: body })
}
export function updateOffice(client: ApiClient, id: number, changes: LocationUpdate): Promise<LocationOut> {
  return client.request<LocationOut>('PATCH', `${OFFICES}/${id}`, { json: changes })
}

export function listBuildingPage(client: ApiClient, f: BuildingFilters): Promise<Page<BuildingOut>> {
  return client.request<Page<BuildingOut>>('GET', BUILDINGS + toQuery({ ...f }))
}
export function getBuilding(client: ApiClient, id: number): Promise<BuildingDetail> {
  return client.request<BuildingDetail>('GET', `${BUILDINGS}/${id}`)
}
export function createBuilding(client: ApiClient, body: BuildingCreate): Promise<BuildingDetail> {
  return client.request<BuildingDetail>('POST', BUILDINGS, { json: body })
}
/** A new `location_id` moves the building, with its floors and rooms. */
export function updateBuilding(client: ApiClient, id: number, changes: BuildingUpdate): Promise<BuildingDetail> {
  return client.request<BuildingDetail>('PATCH', `${BUILDINGS}/${id}`, { json: changes })
}

export function listFloorPage(client: ApiClient, f: FloorFilters): Promise<Page<FloorOut>> {
  return client.request<Page<FloorOut>>('GET', FLOORS + toQuery({ ...f }))
}
export function getFloor(client: ApiClient, id: number): Promise<FloorDetail> {
  return client.request<FloorDetail>('GET', `${FLOORS}/${id}`)
}
export function createFloor(client: ApiClient, body: FloorCreate): Promise<FloorDetail> {
  return client.request<FloorDetail>('POST', FLOORS, { json: body })
}
/** A new `building_id` moves the floor, with its rooms. */
export function updateFloor(client: ApiClient, id: number, changes: FloorUpdate): Promise<FloorDetail> {
  return client.request<FloorDetail>('PATCH', `${FLOORS}/${id}`, { json: changes })
}

/** Which rooms a turn-off warning counts: those in a place, of a room type, or with an item. */
export type RoomCount = {
  location_id?: number
  building_id?: number
  floor_id?: number
  category_id?: number
  equipment_ids?: number[]
}

/** How many active rooms match (for the turn-off warning). */
export async function countActiveRooms(client: ApiClient, where: RoomCount): Promise<number> {
  return (await listRooms(client, { ...where, is_active: true, page: 1, size: 1 })).total
}
