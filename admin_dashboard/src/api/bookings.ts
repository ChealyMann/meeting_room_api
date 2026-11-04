// Bookings, read only for the Admin: a room's schedule and the day's food list.
import type { ApiClient } from './client'
import { toQuery } from './query'
import type { CateringOrderItem, ItemList, ScheduleItem } from './types'

/** The blocking sessions of one room, `from`..`to` (Phnom Penh days, at most 31). */
export function getRoomSchedule(client: ApiClient, roomId: number, from: string, to: string): Promise<ItemList<ScheduleItem>> {
  return client.request<ItemList<ScheduleItem>>('GET', `/api/v1/rooms/${roomId}/schedule` + toQuery({ from, to }))
}

/** Food orders of bookings whose first session is on `day`; the Admin sees every province. */
export function getFoodList(client: ApiClient, day: string): Promise<ItemList<CateringOrderItem>> {
  return client.request<ItemList<CateringOrderItem>>('GET', '/api/v1/pitika/catering' + toQuery({ date: day }))
}
