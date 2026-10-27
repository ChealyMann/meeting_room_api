// The office, building and floor forms: their values, the checks before sending (the API
// limits, DSH-G06), and the bodies they send — all fields on create, only what changed on edit.
import type {
  BuildingCreate,
  BuildingDetail,
  BuildingUpdate,
  FloorCreate,
  FloorDetail,
  FloorUpdate,
  LocationCreate,
  LocationOut,
  LocationUpdate,
} from '../api/types'
import { checkOrder, length, nameProblems, optional, tooLong } from './formChecks'
import { orderValue as order } from './sortOrder'

export interface OfficeForm {
  name_kh: string
  name_en: string
  /** Province code, e.g. PP. */
  province: string
  address: string
  map_query: string
  description: string
}

export function emptyOfficeForm(): OfficeForm {
  return { name_kh: '', name_en: '', province: '', address: '', map_query: '', description: '' }
}

export function officeFormOf(office: LocationOut): OfficeForm {
  return {
    name_kh: office.name_kh,
    name_en: office.name_en,
    province: office.province.code,
    address: office.address ?? '',
    map_query: office.map_query ?? '',
    description: office.description ?? '',
  }
}

/** Problems to show before sending, by field. Empty when the form can be sent. */
export function officeProblems(form: OfficeForm): Record<string, string> {
  const problems: Record<string, string> = {}
  nameProblems(form, problems)
  if (!form.province) problems.province = 'Choose a province.'
  tooLong(form.address, 200, 'address', problems)
  tooLong(form.map_query, 500, 'map_query', problems)
  tooLong(form.description, 1000, 'description', problems)
  return problems
}

/** POST /locations: the form as sent; empty optional fields are left out. */
export function officeCreateBody(form: OfficeForm): LocationCreate {
  const body: LocationCreate = { name_kh: form.name_kh.trim(), name_en: form.name_en.trim(), province: form.province }
  for (const key of ['address', 'map_query', 'description'] as const) {
    if (optional(form[key])) body[key] = optional(form[key])
  }
  return body
}

/** PATCH /locations/{id}: only what changed. A cleared optional field is sent as null. */
export function officeChanges(form: OfficeForm, office: LocationOut): LocationUpdate {
  const before = officeFormOf(office)
  const changes: LocationUpdate = {}
  if (form.name_kh.trim() !== before.name_kh) changes.name_kh = form.name_kh.trim()
  if (form.name_en.trim() !== before.name_en) changes.name_en = form.name_en.trim()
  if (form.province !== before.province) changes.province = form.province
  for (const key of ['address', 'map_query', 'description'] as const) {
    if (optional(form[key]) !== optional(before[key])) changes[key] = optional(form[key])
  }
  return changes
}

export interface BuildingForm {
  location_id: number | null
  name_kh: string
  name_en: string
  short_name: string
  sort_order: string
}

export function emptyBuildingForm(locationId: number | null = null): BuildingForm {
  return { location_id: locationId, name_kh: '', name_en: '', short_name: '', sort_order: '' }
}

export function buildingFormOf(building: BuildingDetail): BuildingForm {
  return {
    location_id: building.location_id,
    name_kh: building.name_kh,
    name_en: building.name_en,
    short_name: building.short_name ?? '',
    sort_order: String(building.sort_order),
  }
}

export function buildingProblems(form: BuildingForm): Record<string, string> {
  const problems: Record<string, string> = {}
  if (form.location_id === null) problems.location_id = 'Choose an office.'
  nameProblems(form, problems)
  tooLong(form.short_name, 20, 'short_name', problems)
  checkOrder(form.sort_order, problems)
  return problems
}

/** POST /buildings. An empty order is sent as 0, the API's default. */
export function buildingCreateBody(form: BuildingForm): BuildingCreate {
  const body: BuildingCreate = {
    location_id: form.location_id!,
    name_kh: form.name_kh.trim(),
    name_en: form.name_en.trim(),
    sort_order: order(form.sort_order),
  }
  if (optional(form.short_name)) body.short_name = optional(form.short_name)
  return body
}

/** PATCH /buildings/{id}: only what changed. A new office moves the building. */
export function buildingChanges(form: BuildingForm, building: BuildingDetail): BuildingUpdate {
  const before = buildingFormOf(building)
  const changes: BuildingUpdate = {}
  if (form.location_id !== null && form.location_id !== before.location_id) changes.location_id = form.location_id
  if (form.name_kh.trim() !== before.name_kh) changes.name_kh = form.name_kh.trim()
  if (form.name_en.trim() !== before.name_en) changes.name_en = form.name_en.trim()
  if (optional(form.short_name) !== optional(before.short_name)) changes.short_name = optional(form.short_name)
  if (order(form.sort_order) !== building.sort_order) changes.sort_order = order(form.sort_order)
  return changes
}

export interface FloorForm {
  /** Only narrows the building select; the API takes the building. */
  location_id: number | null
  building_id: number | null
  floor_label: string
  sort_order: string
}

export function emptyFloorForm(locationId: number | null = null, buildingId: number | null = null): FloorForm {
  return { location_id: locationId, building_id: buildingId, floor_label: '', sort_order: '' }
}

export function floorFormOf(floor: FloorDetail): FloorForm {
  return {
    location_id: floor.location.id,
    building_id: floor.building_id,
    floor_label: floor.floor_label,
    sort_order: String(floor.sort_order),
  }
}

export function floorProblems(form: FloorForm): Record<string, string> {
  const problems: Record<string, string> = {}
  if (form.location_id === null) problems.location_id = 'Choose an office.'
  if (form.building_id === null) problems.building_id = 'Choose a building.'
  const label = form.floor_label.trim()
  if (!label) problems.floor_label = 'Enter the floor name.'
  else if (length(label) > 100) problems.floor_label = 'Max 100 characters.'
  checkOrder(form.sort_order, problems)
  return problems
}

/** POST /floors. An empty order is sent as 0, the API's default. */
export function floorCreateBody(form: FloorForm): FloorCreate {
  return { building_id: form.building_id!, floor_label: form.floor_label.trim(), sort_order: order(form.sort_order) }
}

/** PATCH /floors/{id}: only what changed. A new building moves the floor; the office alone is not sent. */
export function floorChanges(form: FloorForm, floor: FloorDetail): FloorUpdate {
  const changes: FloorUpdate = {}
  if (form.building_id !== null && form.building_id !== floor.building_id) changes.building_id = form.building_id
  if (form.floor_label.trim() !== floor.floor_label) changes.floor_label = form.floor_label.trim()
  if (order(form.sort_order) !== floor.sort_order) changes.sort_order = order(form.sort_order)
  return changes
}
