// Rooms, their photos and their equipment.
import type { ApiClient } from './client'
import { toQuery } from './query'
import type {
  DoorCode,
  EquipmentOut,
  ItemList,
  Page,
  PhotoOut,
  RoomCreate,
  RoomDetail,
  RoomListItem,
  RoomUpdate,
} from './types'

export interface RoomFilters {
  province?: string
  location_id?: number
  building_id?: number
  floor_id?: number
  category_id?: number
  min_capacity?: number
  equipment_ids?: number[]
  owner_id?: number
  has_owner?: boolean
  is_active?: boolean
  is_bookable?: boolean
  is_private?: boolean
  search?: string
  page?: number
  size?: number
}

const ROOMS = '/api/v1/rooms'

export function listRooms(client: ApiClient, filters: RoomFilters): Promise<Page<RoomListItem>> {
  return client.request<Page<RoomListItem>>('GET', ROOMS + toQuery({ ...filters }))
}

export function getRoom(client: ApiClient, id: number): Promise<RoomDetail> {
  return client.request<RoomDetail>('GET', `${ROOMS}/${id}`)
}

export function createRoom(client: ApiClient, body: RoomCreate): Promise<RoomDetail> {
  return client.request<RoomDetail>('POST', ROOMS, { json: body })
}

/** Send only the fields that changed. */
export function updateRoom(client: ApiClient, id: number, changes: RoomUpdate): Promise<RoomDetail> {
  return client.request<RoomDetail>('PATCH', `${ROOMS}/${id}`, { json: changes })
}

/** The only place a door code is ever read. */
export function getDoorCode(client: ApiClient, id: number): Promise<DoorCode> {
  return client.request<DoorCode>('GET', `${ROOMS}/${id}/door-code`)
}

export function uploadRoomPhoto(client: ApiClient, id: number, file: File): Promise<PhotoOut> {
  const form = new FormData()
  form.append('file', file)
  return client.request<PhotoOut>('POST', `${ROOMS}/${id}/photos`, { form })
}

/** `photoIds` must hold every photo of the room exactly once; the first becomes the cover. */
export function reorderRoomPhotos(
  client: ApiClient,
  id: number,
  photoIds: number[],
): Promise<ItemList<PhotoOut>> {
  return client.request<ItemList<PhotoOut>>('PUT', `${ROOMS}/${id}/photos/order`, {
    json: { photo_ids: photoIds },
  })
}

export function deleteRoomPhoto(client: ApiClient, id: number, photoId: number): Promise<void> {
  return client.request<void>('DELETE', `${ROOMS}/${id}/photos/${photoId}`)
}

/** Replaces the room's whole equipment set. */
export function setRoomEquipment(
  client: ApiClient,
  id: number,
  equipmentIds: number[],
): Promise<ItemList<EquipmentOut>> {
  return client.request<ItemList<EquipmentOut>>('PUT', `${ROOMS}/${id}/equipment`, {
    json: { equipment_ids: equipmentIds },
  })
}
