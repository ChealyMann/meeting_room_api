// The Staff booking pages: find a room, see every room's day, check and send a booking, and
// follow my bookings. A booking's details, door pass and calendar file come from ./bookings.
import type { ApiClient } from './client'
import { toQuery } from './query'
import type { ServiceKind, ServiceOut } from './services'
import type {
  BookingCheck,
  BookingCheckResult,
  BookingCreate,
  BookingDetail,
  BookingListItem,
  BookingSaved,
  ItemList,
  Page,
  PublicHolidayOut,
  RoomDaySchedule,
  RoomListItem,
} from './types'

const SERVICE_PATHS: Record<ServiceKind, string> = {
  catering: '/api/v1/catering-packages',
  it: '/api/v1/it-services',
}

export interface StaffRoomFilters {
  q?: string
  is_private?: boolean
  location_id?: number
  building_id?: number
  min_capacity?: number
  /** Rooms having every one. */
  equipment_ids?: number[]
  /** All three or none: free at that time on every one of the dates. */
  free_dates?: string[]
  free_from?: string
  free_to?: string
  page?: number
  size?: number
}

/** Rooms a staff member can book now. */
export function listBookableRooms(client: ApiClient, f: StaffRoomFilters): Promise<Page<RoomListItem>> {
  const query = toQuery({
    is_bookable: true,
    search: f.q,
    is_private: f.is_private,
    location_id: f.location_id,
    building_id: f.building_id,
    min_capacity: f.min_capacity,
    equipment_ids: f.equipment_ids?.length ? f.equipment_ids.join(',') : undefined,
    free_dates: f.free_dates?.length ? f.free_dates.join(',') : undefined,
    free_from: f.free_from,
    free_to: f.free_to,
    page: f.page,
    size: f.size,
  })
  return client.request<Page<RoomListItem>>('GET', '/api/v1/rooms' + query)
}

/** Every room's blocking sessions on `day`, in one request (`roomIds` empty: every active room). */
export function getDaySchedule(client: ApiClient, day: string, roomIds?: number[]): Promise<ItemList<RoomDaySchedule>> {
  return client.request<ItemList<RoomDaySchedule>>('GET', '/api/v1/room-schedule' + toQuery({ date: day, room_ids: roomIds }))
}

/** Active food packages or IT services; one page of 100 holds them all. */
export async function listActiveServices(client: ApiClient, kind: ServiceKind): Promise<ServiceOut[]> {
  const page = await client.request<Page<ServiceOut>>('GET', SERVICE_PATHS[kind] + toQuery({ page: 1, size: 100 }))
  return page.items
}

/** Public holidays from `from` to `to` (both days included). The API filters by year, so each
 * year in the range is asked once and the dates outside the range are dropped. */
export async function listHolidays(client: ApiClient, from: string, to: string): Promise<PublicHolidayOut[]> {
  const first = Number(from.slice(0, 4))
  const last = Number(to.slice(0, 4))
  const out: PublicHolidayOut[] = []
  for (let year = first; year <= last; year += 1) {
    const page = await client.request<Page<PublicHolidayOut>>(
      'GET',
      '/api/v1/public-holidays' + toQuery({ year, page: 1, size: 100 }),
    )
    out.push(...page.items.filter((h) => h.holiday_date >= from && h.holiday_date <= to))
  }
  return out
}

export function checkBooking(client: ApiClient, body: BookingCheck): Promise<BookingCheckResult> {
  return client.request<BookingCheckResult>('POST', '/api/v1/bookings/check', { json: body })
}

export function sendBooking(client: ApiClient, body: BookingCreate): Promise<BookingSaved> {
  return client.request<BookingSaved>('POST', '/api/v1/bookings', { json: body })
}

export function listMyBookings(client: ApiClient, f: { page?: number; size?: number }): Promise<Page<BookingListItem>> {
  return client.request<Page<BookingListItem>>('GET', '/api/v1/bookings/mine' + toQuery({ page: f.page, size: f.size }))
}

/** Cancel my booking; `reason` is optional (5–500 characters when given). */
export function cancelMyBooking(client: ApiClient, id: number, version: number, reason?: string): Promise<BookingDetail> {
  const json = reason ? { version, reason } : { version }
  return client.request<BookingDetail>('POST', `/api/v1/bookings/${id}/cancel`, { json })
}
