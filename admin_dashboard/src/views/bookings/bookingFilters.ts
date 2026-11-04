import type { FilterSpec } from '../../composables/useListQuery'

/** The bookings list's filters, in the order they go to the API (search last). Same keys as BookingFilters. */
export const BOOKING_FILTERS: FilterSpec = {
  status: 'string',
  province: 'string',
  room_id: 'int',
  from: 'string',
  to: 'string',
  q: 'string',
}
