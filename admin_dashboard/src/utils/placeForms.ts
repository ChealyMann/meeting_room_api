// The office, building and floor forms: their values, the checks before sending (the API
// limits, DSH-G06), and the bodies they send — all fields on create, only what changed on edit.
import type { LocationCreate, LocationOut, LocationUpdate } from '../api/types'

const length = (text: string) => [...text].length // characters, like the API
const optional = (text: string) => text.trim() || null

function nameProblems(form: { name_kh: string; name_en: string }, problems: Record<string, string>) {
  for (const [key, missing] of [
    ['name_kh', 'Enter the Khmer name.'],
    ['name_en', 'Enter the English name.'],
  ] as const) {
    const text = form[key].trim()
    if (!text) problems[key] = missing
    else if (length(text) > 100) problems[key] = 'Max 100 characters.'
  }
}

function tooLong(text: string, max: number, key: string, problems: Record<string, string>) {
  if (length(text.trim()) > max) problems[key] = `Max ${max} characters.`
}

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
