// Bookings for the Admin: the list of all bookings, a room's schedule, the day's food list, and the
// Admin's actions on one booking (cancel, and approve or reject as backup reviewer).
import type { ApiClient } from './client'
import { toQuery } from './query'
import type { AdminActionsOut, BookingDetail, BookingListItem, CateringOrderItem, DoorPassOut, ItemList, Page, ScheduleItem } from './types'

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

// The Admin's actions (B-33, B-34): cancel any open booking; approve or reject as a backup.
const ADMIN = '/api/v1/admin/bookings'

/** What the Admin may do with this booking now; the buttons follow it. */
export function getAdminActions(client: ApiClient, id: number): Promise<AdminActionsOut> {
  return client.request<AdminActionsOut>('GET', `${ADMIN}/${id}/actions`)
}
export function adminCancel(client: ApiClient, id: number, body: { reason: string | null; version: number }): Promise<BookingDetail> {
  return client.request<BookingDetail>('POST', `${ADMIN}/${id}/cancel`, { json: body })
}
export function adminApprove(client: ApiClient, id: number, body: { notes: string | null; version: number }): Promise<BookingDetail> {
  return client.request<BookingDetail>('POST', `${ADMIN}/${id}/approve`, { json: body })
}
export function adminReject(client: ApiClient, id: number, body: { reason: string | null; version: number }): Promise<BookingDetail> {
  return client.request<BookingDetail>('POST', `${ADMIN}/${id}/reject`, { json: body })
}
