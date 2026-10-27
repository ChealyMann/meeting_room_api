// Shapes from the API's OpenAPI document (src/api/schema.d.ts, made by `npm run gen:api`).
import type { components } from './schema'

type Schemas = components['schemas']

export type Tokens = Schemas['Tokens']
export type UserDetail = Schemas['UserDetail']
export type MeUpdate = Schemas['MeUpdate']
export type RoleRef = Schemas['RoleRef']

export type NamedRef = Schemas['NamedRef']
export type ProvinceRef = Schemas['ProvinceRef']
export type RoomListItem = Schemas['RoomListItem']
export type RoomDetail = Schemas['RoomDetail']
export type RoomCreate = Schemas['RoomCreate']
export type RoomUpdate = Schemas['RoomUpdate']
export type DoorCode = Schemas['DoorCode']
export type PhotoOut = Schemas['PhotoOut']
export type EquipmentOut = Schemas['EquipmentOut']
export type CategoryOut = Schemas['CategoryOut']
export type CategoryCreate = Schemas['CategoryCreate']
export type CategoryUpdate = Schemas['CategoryUpdate']
export type EquipmentCreate = Schemas['EquipmentCreate']
export type EquipmentUpdate = Schemas['EquipmentUpdate']
export type LocationOut = Schemas['LocationOut']
export type BuildingOut = Schemas['BuildingOut']
export type FloorOut = Schemas['FloorOut']
export type UserListItem = Schemas['UserListItem']

/** One page of a list (`Page_X_` in the schema). */
export interface Page<T> {
  items: T[]
  page: number
  size: number
  total: number
}

/** A whole, unpaged list (`ItemList_X_` in the schema). */
export interface ItemList<T> {
  items: T[]
  total: number
}
export type LocationCreate = Schemas['LocationCreate']
export type LocationUpdate = Schemas['LocationUpdate']
export type BuildingDetail = Schemas['BuildingDetail']
export type BuildingCreate = Schemas['BuildingCreate']
export type BuildingUpdate = Schemas['BuildingUpdate']
export type FloorDetail = Schemas['FloorDetail']
export type FloorCreate = Schemas['FloorCreate']
export type FloorUpdate = Schemas['FloorUpdate']
