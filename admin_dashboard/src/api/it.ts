// IT setup (spec 2026-11-05-owner-and-it-pages-design, Part B): the IT Lead's queue and day,
// the IT Staff to assign, and the two actions (T10 assign, T11 ready). `version` is the booking's.
import type { ApiClient } from './client'
import { toQuery } from './query'
import type { ITStaffPick, ITSummary, ITTicketItem, ItemList, Page } from './types'

const TICKETS = '/api/v1/it/tickets'

export interface TicketFilters {
  /** A tab: to assign, in progress, or done (Ready or missed). */
  state?: 'to_assign' | 'in_progress' | 'done'
  /** Only the tickets I am assigned to. */
  mine?: boolean
  /** The setup (first session) day range, Phnom Penh days. */
  from?: string
  to?: string
  q?: string
  page: number
  size: number
}

export function listTicketPage(client: ApiClient, f: TicketFilters): Promise<Page<ITTicketItem>> {
  const query = { state: f.state, mine: f.mine ? 'true' : undefined, from: f.from, to: f.to, q: f.q, page: f.page, size: f.size }
  return client.request<Page<ITTicketItem>>('GET', TICKETS + toQuery(query))
}

export function getItSummary(client: ApiClient): Promise<ITSummary> {
  return client.request<ITSummary>('GET', `${TICKETS}/summary`)
}

/** Active IT Staff, by name (IT Lead only). With `day`, each one's setups that day. */
export function listItStaff(client: ApiClient, day?: string): Promise<ItemList<ITStaffPick>> {
  return client.request<ItemList<ITStaffPick>>('GET', '/api/v1/it/staff' + toQuery({ day }))
}

/** T10: the list replaces the earlier staff. */
export function assignStaff(
  client: ApiClient,
  id: number,
  body: { user_ids: number[]; technician_notes: string | null; version: number },
): Promise<ITTicketItem> {
  return client.request<ITTicketItem>('PUT', `${TICKETS}/${id}/staff`, { json: body })
}

/** T11: the booking is confirmed, with a door pass. */
export function markReady(client: ApiClient, id: number, body: { version: number }): Promise<ITTicketItem> {
  return client.request<ITTicketItem>('POST', `${TICKETS}/${id}/ready`, { json: body })
}
