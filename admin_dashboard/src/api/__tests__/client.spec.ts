import { describe, expect, it, vi, type Mock } from 'vitest'

import { createApiClient, type ClientOptions } from '../client'

const BASE = 'http://localhost:8000'

type FetchMock = Mock<typeof fetch>

function json(status: number, body: unknown) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })
}

const unauthorized = () => json(401, { error: { code: 'UNAUTHORIZED', message: 'Please sign in.' } })

function fetchReturning(...responses: Array<() => Response>): FetchMock {
  const fn = vi.fn<typeof fetch>()
  for (const make of responses) fn.mockImplementationOnce(async () => make())
  return fn
}

/** The URL and options of the n-th fetch call. */
function callOf(fn: FetchMock, n = 0): { url: string; init: RequestInit } {
  const call = fn.mock.calls[n]
  if (!call) throw new Error(`fetch was not called ${n + 1} time(s)`)
  return { url: String(call[0]), init: call[1] ?? {} }
}

const authOf = (fn: FetchMock, n = 0) => new Headers(callOf(fn, n).init.headers).get('Authorization')

/** A client whose token store starts with A1 and becomes A2 after a successful refresh. */
function setup(fetchImpl: FetchMock, refreshResult = true) {
  let token = 'A1'
  const refresh = vi.fn<() => Promise<boolean>>(async () => {
    if (refreshResult) token = 'A2'
    return refreshResult
  })
  const onAuthLost = vi.fn<() => void>()
  const options: ClientOptions = {
    baseUrl: BASE,
    getAccessToken: () => token,
    refresh,
    onAuthLost,
    fetchImpl,
  }
  return { client: createApiClient(options), refresh, onAuthLost }
}

describe('createApiClient', () => {
  it('sends the bearer token to the full API URL', async () => {
    const fetchImpl = fetchReturning(() => json(200, { id: 1 }))
    const { client } = setup(fetchImpl)

    const body = await client.request<{ id: number }>('GET', '/api/v1/me')

    expect(body).toEqual({ id: 1 })
    expect(callOf(fetchImpl).url).toBe('http://localhost:8000/api/v1/me')
    expect(authOf(fetchImpl)).toBe('Bearer A1')
  })

  it('returns undefined for 204 No Content', async () => {
    const { client } = setup(fetchReturning(() => new Response(null, { status: 204 })))

    await expect(client.request('DELETE', '/api/v1/me/signature')).resolves.toBeUndefined()
  })

  it('sends JSON with a JSON content type', async () => {
    const fetchImpl = fetchReturning(() => json(200, {}))
    const { client } = setup(fetchImpl)

    await client.request('PATCH', '/api/v1/me', { json: { phone: '012' } })

    const { init } = callOf(fetchImpl)
    expect(new Headers(init.headers).get('Content-Type')).toBe('application/json')
    expect(init.body).toBe('{"phone":"012"}')
  })

  it('leaves the content type to the browser for form data', async () => {
    const fetchImpl = fetchReturning(() => json(200, {}))
    const { client } = setup(fetchImpl)
    const form = new FormData()
    form.append('file', new Blob(['x']), 'sig.png')

    await client.request('PUT', '/api/v1/me/signature', { form })

    const { init } = callOf(fetchImpl)
    expect(new Headers(init.headers).has('Content-Type')).toBe(false)
    expect(init.body).toBe(form)
  })

  it('refreshes once on 401 and repeats the call with the new token', async () => {
    const fetchImpl = fetchReturning(unauthorized, () => json(200, { ok: true }))
    const { client, refresh } = setup(fetchImpl)

    await expect(client.request('GET', '/api/v1/me')).resolves.toEqual({ ok: true })
    expect(refresh).toHaveBeenCalledTimes(1)
    expect(authOf(fetchImpl, 1)).toBe('Bearer A2')
  })

  it('shares one refresh between calls that get 401 at the same time', async () => {
    const fetchImpl = vi.fn<typeof fetch>(async (_url, init) =>
      new Headers(init?.headers).get('Authorization') === 'Bearer A1'
        ? unauthorized()
        : json(200, { ok: true }),
    )
    const { client, refresh } = setup(fetchImpl)

    const results = await Promise.all([
      client.request('GET', '/api/v1/me'),
      client.request('GET', '/api/v1/provinces'),
    ])

    expect(results).toEqual([{ ok: true }, { ok: true }])
    expect(refresh).toHaveBeenCalledTimes(1)
  })

  it('reports lost sign-in when the refresh fails', async () => {
    const { client, onAuthLost } = setup(vi.fn<typeof fetch>(async () => unauthorized()), false)

    await expect(client.request('GET', '/api/v1/me')).rejects.toMatchObject({
      status: 401,
      code: 'UNAUTHORIZED',
    })
    expect(onAuthLost).toHaveBeenCalledTimes(1)
  })

  it('reports lost sign-in when the repeated call is 401 again', async () => {
    const { client, onAuthLost, refresh } = setup(vi.fn<typeof fetch>(async () => unauthorized()))

    await expect(client.request('GET', '/api/v1/me')).rejects.toMatchObject({ status: 401 })
    expect(refresh).toHaveBeenCalledTimes(1)
    expect(onAuthLost).toHaveBeenCalledTimes(1)
  })

  it('turns a failed fetch into a NETWORK_ERROR', async () => {
    const { client } = setup(
      vi.fn<typeof fetch>(async () => {
        throw new TypeError('Failed to fetch')
      }),
    )

    await expect(client.request('GET', '/api/v1/me')).rejects.toMatchObject({
      status: 0,
      code: 'NETWORK_ERROR',
    })
  })

  it('turns API errors into ApiError', async () => {
    const { client } = setup(
      fetchReturning(() =>
        json(422, {
          error: { code: 'VALIDATION_ERROR', message: 'Invalid request.', fields: { phone: 'x' } },
        }),
      ),
    )

    await expect(client.request('PATCH', '/api/v1/me', { json: {} })).rejects.toMatchObject({
      status: 422,
      fields: { phone: 'x' },
    })
  })

  it('downloads a blob with the bearer token', async () => {
    const fetchImpl = fetchReturning(() => new Response('png', { status: 200 }))
    const { client } = setup(fetchImpl)

    const blob = await client.requestBlob('/api/v1/users/2/signature')

    expect(await blob.text()).toBe('png')
    expect(authOf(fetchImpl)).toBe('Bearer A1')
  })

  it('uses the global fetch when no fetchImpl is given', async () => {
    const globalFetch = fetchReturning(() => json(200, { ok: 1 }))
    vi.stubGlobal('fetch', globalFetch)
    const client = createApiClient({
      baseUrl: BASE,
      getAccessToken: () => null,
      refresh: async () => false,
      onAuthLost: () => {},
    })

    await client.request('GET', '/api/v1/health')

    expect(globalFetch).toHaveBeenCalledTimes(1)
    expect(authOf(globalFetch)).toBeNull()
    vi.unstubAllGlobals()
  })
})
