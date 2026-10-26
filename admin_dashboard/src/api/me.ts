// The signed-in user's own account, through the client (token refresh included).
import type { ApiClient } from './client'
import type { MeUpdate, Tokens, UserDetail } from './types'

export function getMe(client: ApiClient): Promise<UserDetail> {
  return client.request<UserDetail>('GET', '/api/v1/me')
}

/** Send only the fields that changed; null clears a field. */
export function updateMe(client: ApiClient, changes: MeUpdate): Promise<UserDetail> {
  return client.request<UserDetail>('PATCH', '/api/v1/me', { json: changes })
}

/** Returns new tokens: the old ones stop working after a password change. */
export function changePassword(client: ApiClient, current: string, next: string): Promise<Tokens> {
  return client.request<Tokens>('POST', '/api/v1/auth/change-password', {
    json: { current_password: current, new_password: next },
  })
}

export function logout(client: ApiClient, refreshToken: string | null): Promise<void> {
  return client.request<void>(
    'POST',
    '/api/v1/auth/logout',
    refreshToken ? { json: { refresh_token: refreshToken } } : undefined,
  )
}

export function uploadMySignature(client: ApiClient, file: File): Promise<UserDetail> {
  const form = new FormData()
  form.append('file', file)
  return client.request<UserDetail>('PUT', '/api/v1/me/signature', { form })
}

export function deleteMySignature(client: ApiClient): Promise<void> {
  return client.request<void>('DELETE', '/api/v1/me/signature')
}

export function uploadMyAvatar(client: ApiClient, file: File): Promise<UserDetail> {
  const form = new FormData()
  form.append('file', file)
  return client.request<UserDetail>('PUT', '/api/v1/me/avatar', { form })
}

export function deleteMyAvatar(client: ApiClient): Promise<void> {
  return client.request<void>('DELETE', '/api/v1/me/avatar')
}

/**
 * A private image (`signature_url` or `avatar_url` from UserDetail). It needs the bearer
 * token, so an <img> cannot load it directly.
 */
export function getImageBlob(client: ApiClient, path: string): Promise<Blob> {
  return client.requestBlob(path)
}
