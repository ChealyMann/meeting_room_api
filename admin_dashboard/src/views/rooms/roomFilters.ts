import type { FilterSpec } from '../../composables/useListQuery'

/** The room list's filters, in the order they go to the API (search last). Same keys as RoomFilters. */
export const ROOM_FILTERS: FilterSpec = {
  province: 'string',
  location_id: 'int',
  building_id: 'int',
  floor_id: 'int',
  category_id: 'int',
  min_capacity: 'int',
  equipment_ids: 'ints',
  owner_id: 'int',
  has_owner: 'bool',
  is_bookable: 'bool',
  is_private: 'bool',
  search: 'string',
}

/** Filters that live in the "More filters" row. */
export const MORE_FILTERS = [
  'province',
  'min_capacity',
  'equipment_ids',
  'owner_id',
  'has_owner',
  'is_bookable',
  'is_private',
] as const
