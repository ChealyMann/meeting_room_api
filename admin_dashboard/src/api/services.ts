// Booking services: catering packages and IT services. The two lists have the same shape.
import type { ApiClient } from './client'
import type { CatalogFilters } from './catalog'
import { ApiError } from './errors'
import { toQuery } from './query'
import type {
  CateringPackageCreate,
  CateringPackageOut,
  CateringPackageUpdate,
  ITServiceCreate,
  ITServiceOut,
  ITServiceUpdate,
  Page,
} from './types'

export type ServiceKind = 'catering' | 'it'
export type ServiceOut = CateringPackageOut | ITServiceOut
export type ServiceCreate = CateringPackageCreate | ITServiceCreate
export type ServiceUpdate = CateringPackageUpdate | ITServiceUpdate

const PATHS: Record<ServiceKind, string> = {
  catering: '/api/v1/catering-packages',
  it: '/api/v1/it-services',
}

export function listServicePage(client: ApiClient, kind: ServiceKind, f: CatalogFilters): Promise<Page<ServiceOut>> {
  return client.request<Page<ServiceOut>>('GET', PATHS[kind] + toQuery({ ...f }))
}

/** The API has no GET by id, so look through the list (one page of 100 holds them all). */
export async function getService(client: ApiClient, kind: ServiceKind, id: number): Promise<ServiceOut> {
  for (let page = 1; ; page++) {
    const found = await listServicePage(client, kind, { page, size: 100 })
    const service = found.items.find((s) => s.id === id)
    if (service) return service
    if (page * found.size >= found.total) throw new ApiError(404, 'NOT_FOUND', 'Not found.', {})
  }
}

export function createService(client: ApiClient, kind: ServiceKind, body: ServiceCreate): Promise<ServiceOut> {
  return client.request<ServiceOut>('POST', PATHS[kind], { json: body })
}
/** Send the `version` you read: an old one gets 409 STALE_VERSION. */
export function updateService(client: ApiClient, kind: ServiceKind, id: number, changes: ServiceUpdate): Promise<ServiceOut> {
  return client.request<ServiceOut>('PATCH', `${PATHS[kind]}/${id}`, { json: changes })
}
