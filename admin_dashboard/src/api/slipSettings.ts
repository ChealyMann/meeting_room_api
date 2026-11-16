// The request slip's settings (Admin): the Director of Cabinet and the address line.
import type { ApiClient } from './client'
import type { components } from './schema'

export type SlipSettings = components['schemas']['SlipSettingsOut']
export type SlipSettingsUpdate = components['schemas']['SlipSettingsUpdate']

const PATH = '/api/v1/slip-settings'

export function getSlipSettings(client: ApiClient): Promise<SlipSettings> {
  return client.request<SlipSettings>('GET', PATH)
}

/** PUT: both fields, every time. `director_user_id: null` leaves the director's box empty. */
export function saveSlipSettings(client: ApiClient, body: SlipSettingsUpdate): Promise<SlipSettings> {
  return client.request<SlipSettings>('PUT', PATH, { json: body })
}
