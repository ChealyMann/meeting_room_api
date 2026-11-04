// Bookings, read only for the Admin: the list of all bookings, a room's schedule and the day's food list.
import type { ApiClient } from './client'
import { toQuery } from './query'
import type { BookingDetail, BookingListItem, CateringOrderItem, DoorPassOut, ItemList, Page, ScheduleItem } from './types'

/** The blocking sessions of one room, `from`..`to` (Phnom Penh days, at most 31). */
export function getRoomSchedule(client: ApiClient, roomId: number, from: string, to: string): Promise<ItemList<ScheduleItem>> {
  return client.request<ItemList<ScheduleItem>>('GET', `/api/v1/rooms/${roomId}/schedule` + toQuery({ from, to }))
}

/** Food orders of bookings whose first session is on `day`; the Admin sees every province. */
export function getFoodList(client: ApiClient, day: string): Promise<ItemList<CateringOrderItem>> {
  return client.request<ItemList<CateringOrderItem>>('GET', '/api/v1/pitika/catering' + toQuery({ date: day }))
}

/** The API's filters for the Admin list (B-32). `status` is a display status; days are Phnom Penh days. */
export interface BookingFilters {
  status?: string
  province?: string
  room_id?: number
  from?: string
  to?: string
  q?: string
  page?: number
  size?: number
}

export function listBookingPage(client: ApiClient, f: BookingFilters): Promise<Page<BookingListItem>> {
  return client.request<Page<BookingListItem>>('GET', '/api/v1/bookings' + toQuery({ ...f }))
}

export function getBooking(client: ApiClient, id: number): Promise<BookingDetail> {
  return client.request<BookingDetail>('GET', `/api/v1/bookings/${id}`)
}

/** Only for a confirmed booking (else 404); never shown unless the Admin asks. */
export function getDoorPass(client: ApiClient, id: number): Promise<DoorPassOut> {
  return client.request<DoorPassOut>('GET', `/api/v1/bookings/${id}/door-pass`)
}

/** The calendar file (text/calendar), one event per session. */
export function getBookingIcs(client: ApiClient, id: number): Promise<Blob> {
  return client.requestBlob(`/api/v1/bookings/${id}/ics`)
}
