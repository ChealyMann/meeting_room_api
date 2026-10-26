import { ApiError, networkError, parseApiError } from './errors'

export type Method = 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE'

export interface RequestBody {
  json?: unknown
  form?: FormData
}

export interface ClientOptions {
  /** API origin, e.g. http://localhost:8000; request paths start with /api/v1/. */
  baseUrl: string
  getAccessToken(): string | null
  /** Get a new access token; true when it worked. */
  refresh(): Promise<boolean>
  /** The session is gone (refresh failed or was refused). */
  onAuthLost(): void
  /** Defaults to the global fetch, looked up on every call. */
  fetchImpl?: typeof fetch
}

export interface ApiClient {
  request<T>(method: Method, path: string, body?: RequestBody): Promise<T>
  requestBlob(path: string): Promise<Blob>
}

export function createApiClient(options: ClientOptions): ApiClient {
  // One refresh at a time: calls that get 401 together wait for the same one.
  let pendingRefresh: Promise<boolean> | null = null

  function refreshOnce(): Promise<boolean> {
    if (!pendingRefresh) {
      pendingRefresh = options.refresh().finally(() => {
        pendingRefresh = null
      })
    }
    return pendingRefresh
  }

  async function send(method: Method, path: string, body?: RequestBody): Promise<Response> {
    const headers = new Headers()
    const token = options.getAccessToken()
    if (token) headers.set('Authorization', `Bearer ${token}`)
    let payload: BodyInit | undefined
    if (body?.form) {
      payload = body.form
    } else if (body && 'json' in body) {
      headers.set('Content-Type', 'application/json')
      payload = JSON.stringify(body.json)
    }
    const fetchImpl = options.fetchImpl ?? globalThis.fetch
    try {
      return await fetchImpl(`${options.baseUrl}${path}`, { method, headers, body: payload })
    } catch (cause) {
      throw networkError(cause)
    }
  }

  async function authorized(method: Method, path: string, body?: RequestBody): Promise<Response> {
    let response = await send(method, path, body)
    if (response.status === 401) {
      const refreshed = await refreshOnce()
      if (refreshed) response = await send(method, path, body)
      if (!refreshed || response.status === 401) {
        options.onAuthLost()
      }
    }
    if (!response.ok) throw await parseApiError(response)
    return response
  }

  return {
    async request<T>(method: Method, path: string, body?: RequestBody): Promise<T> {
      const response = await authorized(method, path, body)
      if (response.status === 204) return undefined as T
      return (await response.json()) as T
    },
    async requestBlob(path: string): Promise<Blob> {
      const response = await authorized('GET', path)
      return response.blob()
    },
  }
}

export { ApiError }
