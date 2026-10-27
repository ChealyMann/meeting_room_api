// The room type and equipment forms: their values, the checks before sending (the API limits,
// DSH-G06), and the bodies they send — all fields on create, only what changed on edit.
import type {
  CategoryCreate,
  CategoryOut,
  CategoryUpdate,
  EquipmentCreate,
  EquipmentOut,
  EquipmentUpdate,
} from '../api/types'
import { checkOrder, length, nameProblems } from './formChecks'
import { orderValue } from './sortOrder'

export interface RoomTypeForm {
  name_kh: string
  name_en: string
  sort_order: string
}

export function emptyRoomTypeForm(): RoomTypeForm {
  return { name_kh: '', name_en: '', sort_order: '' }
}

export function roomTypeFormOf(roomType: CategoryOut): RoomTypeForm {
  return { name_kh: roomType.name_kh, name_en: roomType.name_en, sort_order: String(roomType.sort_order) }
}

/** Problems to show before sending, by field. Empty when the form can be sent. */
export function roomTypeProblems(form: RoomTypeForm): Record<string, string> {
  const problems: Record<string, string> = {}
  nameProblems(form, problems)
  checkOrder(form.sort_order, problems)
  return problems
}

/** POST /categories. An empty order is sent as 0, the API's default. */
export function roomTypeCreateBody(form: RoomTypeForm): CategoryCreate {
  return { name_kh: form.name_kh.trim(), name_en: form.name_en.trim(), sort_order: orderValue(form.sort_order) }
}

/** PATCH /categories/{id}: only what changed. */
export function roomTypeChanges(form: RoomTypeForm, roomType: CategoryOut): CategoryUpdate {
  const changes: CategoryUpdate = {}
  if (form.name_kh.trim() !== roomType.name_kh) changes.name_kh = form.name_kh.trim()
  if (form.name_en.trim() !== roomType.name_en) changes.name_en = form.name_en.trim()
  if (orderValue(form.sort_order) !== roomType.sort_order) changes.sort_order = orderValue(form.sort_order)
  return changes
}

export interface EquipmentForm {
  name: string
  /** The Lucide name, or null for no icon. */
  icon: string | null
  sort_order: string
}

export function emptyEquipmentForm(): EquipmentForm {
  return { name: '', icon: null, sort_order: '' }
}

export function equipmentFormOf(item: EquipmentOut): EquipmentForm {
  return { name: item.name, icon: item.icon, sort_order: String(item.sort_order) }
}

export function equipmentProblems(form: EquipmentForm): Record<string, string> {
  const problems: Record<string, string> = {}
  const name = form.name.trim()
  if (!name) problems.name = 'Enter the name.'
  else if (length(name) > 200) problems.name = 'Max 200 characters.'
  checkOrder(form.sort_order, problems)
  return problems
}

/** POST /equipment. No icon is left out; an empty order is sent as 0. */
export function equipmentCreateBody(form: EquipmentForm): EquipmentCreate {
  return {
    name: form.name.trim(),
    ...(form.icon ? { icon: form.icon } : {}),
    sort_order: orderValue(form.sort_order),
  }
}

/** PATCH /equipment/{id}: only what changed. The icon goes only when it changed (cleared → null). */
export function equipmentChanges(form: EquipmentForm, item: EquipmentOut): EquipmentUpdate {
  const changes: EquipmentUpdate = {}
  if (form.name.trim() !== item.name) changes.name = form.name.trim()
  if (form.icon !== item.icon) changes.icon = form.icon
  if (orderValue(form.sort_order) !== item.sort_order) changes.sort_order = orderValue(form.sort_order)
  return changes
}
