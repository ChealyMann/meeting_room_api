// Bookings, read only for the Admin: a room's schedule.
import type { ApiClient } from './client'
import { toQuery } from './query'
import type { ItemList, ScheduleItem } from './types'

/** The blocking sessions of one room, `from`..`to` (Phnom Penh days, at most 31). */
export function getRoomSchedule(client: ApiClient, roomId: number, from: string, to: string): Promise<ItemList<ScheduleItem>> {
  return client.request<ItemList<ScheduleItem>>('GET', `/api/v1/rooms/${roomId}/schedule` + toQuery({ from, to }))
}
