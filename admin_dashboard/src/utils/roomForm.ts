// The room form's values, its checks before sending (the API limits, DSH-G06), and the
// bodies it sends: the whole room on create, only what changed on edit (DSH-G03).
import type { RoomCreate, RoomDetail, RoomUpdate } from '../api/types'

export interface RoomForm {
  name_kh: string
  name_en: string
  location_id: number | null
  building_id: number | null
  floor_id: number | null
  category_id: number | null
  capacity: string
  size_sqm: string
  start_time: string
  end_time: string
  short_desc: string
  description: string
  /** Write-only: always empty when a form opens; empty on edit means "keep the current code". */
  door_code: string
  room_owner_id: number | null
  is_private: boolean
}

export function emptyRoomForm(): RoomForm {
  return {
    name_kh: '',
    name_en: '',
    location_id: null,
    building_id: null,
    floor_id: null,
    category_id: null,
    capacity: '',
    size_sqm: '',
    start_time: '08:00',
    end_time: '17:00',
    short_desc: '',
    description: '',
    door_code: '',
    room_owner_id: null,
    is_private: false,
  }
}

export function roomFormOf(room: RoomDetail): RoomForm {
  return {
    name_kh: room.name_kh,
    name_en: room.name_en,
    location_id: room.location.id,
    building_id: room.building.id,
    floor_id: room.floor.id,
    category_id: room.category.id,
    capacity: String(room.capacity),
    size_sqm: room.size_sqm === null || room.size_sqm === undefined ? '' : String(room.size_sqm),
    start_time: room.start_time.slice(0, 5),
    end_time: room.end_time.slice(0, 5),
    short_desc: room.short_desc ?? '',
    description: room.description ?? '',
    door_code: '',
    room_owner_id: room.owner?.id ?? null,
    is_private: room.is_private,
  }
}

const TIME = /^([01]\d|2[0-3]):[0-5]\d$/
const length = (text: string) => [...text].length // characters, like the API

function wholeNumber(text: string, min: number, max: number): number | null {
  const value = Number(text.trim())
  return /^\d+$/.test(text.trim()) && value >= min && value <= max ? value : null
}

/** Problems to show before sending, by field. Empty when the form can be sent. */
export function roomProblems(form: RoomForm): Record<string, string> {
  const problems: Record<string, string> = {}
  for (const [key, missing] of [
    ['name_kh', 'Enter the Khmer name.'],
    ['name_en', 'Enter the English name.'],
  ] as const) {
    const text = form[key].trim()
    if (!text) problems[key] = missing
    else if (length(text) > 100) problems[key] = 'Max 100 characters.'
  }
  if (form.location_id === null) problems.location_id = 'Choose an office.'
  if (form.building_id === null) problems.building_id = 'Choose a building.'
  if (form.floor_id === null) problems.floor_id = 'Choose a floor.'
  if (form.category_id === null) problems.category_id = 'Choose a room type.'
  if (wholeNumber(form.capacity, 1, 10000) === null) {
    problems.capacity = 'Seats must be a whole number from 1 to 10000.'
  }
  if (form.size_sqm.trim() && wholeNumber(form.size_sqm, 1, 100000) === null) {
    problems.size_sqm = 'Size must be a whole number from 1 to 100000.'
  }
  if (!TIME.test(form.start_time)) problems.start_time = 'Use HH:MM, for example 08:00.'
  if (!TIME.test(form.end_time)) problems.end_time = 'Use HH:MM, for example 08:00.'
  else if (TIME.test(form.start_time) && form.start_time >= form.end_time) {
    problems.end_time = 'Opening must be before closing.'
  }
  if (length(form.short_desc.trim()) > 200) problems.short_desc = 'Max 200 characters.'
  if (length(form.description.trim()) > 1000) problems.description = 'Max 1000 characters.'
  if (length(form.door_code.trim()) > 50) problems.door_code = 'Max 50 characters.'
  return problems
}

const optional = (text: string) => text.trim() || null

/** POST /rooms: the form as sent; empty optional fields are left out. */
export function roomCreateBody(form: RoomForm): RoomCreate {
  const body: RoomCreate = {
    name_kh: form.name_kh.trim(),
    name_en: form.name_en.trim(),
    floor_id: form.floor_id!,
    category_id: form.category_id!,
    capacity: Number(form.capacity.trim()),
    start_time: form.start_time,
    end_time: form.end_time,
    is_private: form.is_private,
  }
  if (form.size_sqm.trim()) body.size_sqm = Number(form.size_sqm.trim())
  if (optional(form.short_desc)) body.short_desc = optional(form.short_desc)
  if (optional(form.description)) body.description = optional(form.description)
  if (optional(form.door_code)) body.door_code = optional(form.door_code)
  if (form.room_owner_id !== null) body.room_owner_id = form.room_owner_id
  return body
}

/** PATCH /rooms/{id}: only what changed. A cleared optional field is sent as null. */
export function roomChanges(form: RoomForm, room: RoomDetail): RoomUpdate {
  const before = roomFormOf(room)
  const changes: RoomUpdate = {}
  if (form.name_kh.trim() !== before.name_kh) changes.name_kh = form.name_kh.trim()
  if (form.name_en.trim() !== before.name_en) changes.name_en = form.name_en.trim()
  if (form.floor_id !== before.floor_id && form.floor_id !== null) changes.floor_id = form.floor_id
  if (form.category_id !== before.category_id && form.category_id !== null) {
    changes.category_id = form.category_id
  }
  if (form.capacity.trim() !== before.capacity) changes.capacity = Number(form.capacity.trim())
  if (form.size_sqm.trim() !== before.size_sqm) {
    changes.size_sqm = form.size_sqm.trim() ? Number(form.size_sqm.trim()) : null
  }
  if (form.start_time !== before.start_time) changes.start_time = form.start_time
  if (form.end_time !== before.end_time) changes.end_time = form.end_time
  if (optional(form.short_desc) !== optional(before.short_desc)) changes.short_desc = optional(form.short_desc)
  if (optional(form.description) !== optional(before.description)) {
    changes.description = optional(form.description)
  }
  if (optional(form.door_code)) changes.door_code = optional(form.door_code)
  if (form.room_owner_id !== before.room_owner_id) changes.room_owner_id = form.room_owner_id
  if (form.is_private !== before.is_private) changes.is_private = form.is_private
  return changes
}
