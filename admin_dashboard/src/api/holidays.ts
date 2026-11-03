// Public holidays: an Admin list by date. A booking on one is allowed with a warning.
import type { ApiClient } from './client'
import { ApiError } from './errors'
import { toQuery } from './query'
import type { Page, PublicHolidayCreate, PublicHolidayOut, PublicHolidayUpdate } from './types'

/** The API filters by year only; it has no status and no search. */
export interface HolidayFilters {
  year?: number
  page?: number
  size?: number
}

const HOLIDAYS = '/api/v1/public-holidays'

export function listHolidayPage(client: ApiClient, f: HolidayFilters): Promise<Page<PublicHolidayOut>> {
  return client.request<Page<PublicHolidayOut>>('GET', HOLIDAYS + toQuery({ ...f }))
}

/** The API has no GET by id, so look through the list (one page of 100 holds years of dates). */
export async function getHoliday(client: ApiClient, id: number): Promise<PublicHolidayOut> {
  for (let page = 1; ; page++) {
    const found = await listHolidayPage(client, { page, size: 100 })
    const holiday = found.items.find((h) => h.id === id)
    if (holiday) return holiday
    if (page * found.size >= found.total) throw new ApiError(404, 'NOT_FOUND', 'Not found.', {})
  }
}

export function createHoliday(client: ApiClient, body: PublicHolidayCreate): Promise<PublicHolidayOut> {
  return client.request<PublicHolidayOut>('POST', HOLIDAYS, { json: body })
}
export function updateHoliday(client: ApiClient, id: number, changes: PublicHolidayUpdate): Promise<PublicHolidayOut> {
  return client.request<PublicHolidayOut>('PATCH', `${HOLIDAYS}/${id}`, { json: changes })
}
export function deleteHoliday(client: ApiClient, id: number): Promise<void> {
  return client.request<void>('DELETE', `${HOLIDAYS}/${id}`)
}
