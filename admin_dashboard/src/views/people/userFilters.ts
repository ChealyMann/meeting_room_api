import type { FilterSpec } from '../../composables/useListQuery'

/** The user list's filters, in the order they go to the API (search last). Same keys as UserFilters. */
export const USER_FILTERS: FilterSpec = {
  division_id: 'int',
  department_id: 'int',
  position_id: 'int',
  role: 'string',
  province: 'string',
  search: 'string',
}
