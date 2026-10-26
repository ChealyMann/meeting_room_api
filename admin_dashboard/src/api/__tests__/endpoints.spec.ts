import { afterEach, describe, expect, it, vi, type Mock } from 'vitest'

import { login, refreshTokens } from '../auth'
import { createApiClient } from '../client'
import {
  changePassword,
  deleteMyAvatar,
  deleteMySignature,
  getMe,
  getImageBlob,
  logout,
  updateMe,
  uploadMyAvatar,
  uploadMySignature,
} from '../me'

const BASE = 'http://localhost:8000'
const TOKENS = { access_token: 'A', refresh_token: 'R', token_type: 'bearer' }

type FetchMock = Mock<typeof fetch>

function json(status: number, body: unknown) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })
}

function fetchReturning(make: () => Response): FetchMock {
  return vi.fn<typeof fetch>(async () => make())
}

/** Method, URL and body of the first fetch call. */
function sent(fn: FetchMock) {
  const call = fn.mock.calls[0]
  if (!call) throw new Error('fetch was not called')
  const init = call[1] ?? {}
  return { method: init.method, url: String(call[0]), body: init.body }
}

function clientWith(fetchImpl: FetchMock) {
  return createApiClient({
    baseUrl: BASE,
    getAccessToken: () => 'A',
    refresh: async () => false,
    onAuthLost: () => {},
    fetchImpl,
  })
}

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('auth', () => {
  it('login posts email and password as given, without trimming', async () => {
    const fetchMock = fetchReturning(() => json(200, TOKENS))
    vi.stubGlobal('fetch', fetchMock)

    await expect(login(BASE, 'Admin@Company.com', ' pw with spaces ')).resolves.toEqual(TOKENS)

    expect(sent(fetchMock)).toEqual({
      method: 'POST',
      url: 'http://localhost:8000/api/v1/auth/login',
      body: '{"email":"Admin@Company.com","password":" pw with spaces "}',
    })
  })

  it('login turns an API error into ApiError', async () => {
    vi.stubGlobal(
      'fetch',
      fetchReturning(() =>
        json(401, { error: { code: 'INVALID_CREDENTIALS', message: 'Wrong email or password.' } }),
      ),
    )

    await expect(login(BASE, 'a@b.c', 'x')).rejects.toMatchObject({
      status: 401,
      message: 'Wrong email or password.',
    })
  })

  it('login turns a failed fetch into NETWORK_ERROR', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn<typeof fetch>(async () => {
        throw new TypeError('Failed to fetch')
      }),
    )

    await expect(login(BASE, 'a@b.c', 'x')).rejects.toMatchObject({ code: 'NETWORK_ERROR' })
  })

  it('refreshTokens posts the refresh token', async () => {
    const fetchMock = fetchReturning(() => json(200, TOKENS))
    vi.stubGlobal('fetch', fetchMock)

    await expect(refreshTokens(BASE, 'R0')).resolves.toEqual(TOKENS)

    expect(sent(fetchMock)).toEqual({
      method: 'POST',
      url: 'http://localhost:8000/api/v1/auth/refresh',
      body: '{"refresh_token":"R0"}',
    })
  })
})

describe('me', () => {
  it('getMe reads /me', async () => {
    const fetchMock = fetchReturning(() => json(200, { id: 1 }))

    await expect(getMe(clientWith(fetchMock))).resolves.toEqual({ id: 1 })

    expect(sent(fetchMock)).toMatchObject({ method: 'GET', url: `${BASE}/api/v1/me` })
  })

  it('updateMe sends PATCH with exactly the changes', async () => {
    const fetchMock = fetchReturning(() => json(200, { id: 1 }))

    await updateMe(clientWith(fetchMock), { phone: '012 345 678' })

    expect(sent(fetchMock)).toEqual({
      method: 'PATCH',
      url: `${BASE}/api/v1/me`,
      body: '{"phone":"012 345 678"}',
    })
  })

  it('changePassword posts current and new password', async () => {
    const fetchMock = fetchReturning(() => json(200, TOKENS))

    await expect(changePassword(clientWith(fetchMock), 'old pw', 'new pw')).resolves.toEqual(TOKENS)

    expect(sent(fetchMock)).toEqual({
      method: 'POST',
      url: `${BASE}/api/v1/auth/change-password`,
      body: '{"current_password":"old pw","new_password":"new pw"}',
    })
  })

  it('logout sends the refresh token when there is one', async () => {
    const fetchMock = fetchReturning(() => new Response(null, { status: 204 }))

    await expect(logout(clientWith(fetchMock), 'R0')).resolves.toBeUndefined()

    expect(sent(fetchMock)).toEqual({
      method: 'POST',
      url: `${BASE}/api/v1/auth/logout`,
      body: '{"refresh_token":"R0"}',
    })
  })

  it('logout sends no body without a refresh token', async () => {
    const fetchMock = fetchReturning(() => new Response(null, { status: 204 }))

    await logout(clientWith(fetchMock), null)

    expect(sent(fetchMock)).toEqual({
      method: 'POST',
      url: `${BASE}/api/v1/auth/logout`,
      body: undefined,
    })
  })

  it('uploadMySignature puts the file in a form field named file', async () => {
    const fetchMock = fetchReturning(() => json(200, { id: 1 }))
    const file = new File(['png'], 'sig.png', { type: 'image/png' })

    await uploadMySignature(clientWith(fetchMock), file)

    const { method, url, body } = sent(fetchMock)
    expect(method).toBe('PUT')
    expect(url).toBe(`${BASE}/api/v1/me/signature`)
    expect(body).toBeInstanceOf(FormData)
    expect((body as FormData).get('file')).toBe(file)
  })

  it('deleteMySignature sends DELETE', async () => {
    const fetchMock = fetchReturning(() => new Response(null, { status: 204 }))

    await expect(deleteMySignature(clientWith(fetchMock))).resolves.toBeUndefined()

    expect(sent(fetchMock)).toMatchObject({ method: 'DELETE', url: `${BASE}/api/v1/me/signature` })
  })

  it('uploadMyAvatar puts the file in a form field named file', async () => {
    const fetchMock = fetchReturning(() => json(200, { id: 1 }))
    const file = new File(['jpg'], 'me.jpg', { type: 'image/jpeg' })

    await uploadMyAvatar(clientWith(fetchMock), file)

    const { method, url, body } = sent(fetchMock)
    expect(method).toBe('PUT')
    expect(url).toBe(`${BASE}/api/v1/me/avatar`)
    expect((body as FormData).get('file')).toBe(file)
  })

  it('deleteMyAvatar sends DELETE', async () => {
    const fetchMock = fetchReturning(() => new Response(null, { status: 204 }))

    await expect(deleteMyAvatar(clientWith(fetchMock))).resolves.toBeUndefined()

    expect(sent(fetchMock)).toMatchObject({ method: 'DELETE', url: `${BASE}/api/v1/me/avatar` })
  })

  it('getImageBlob downloads a private image path', async () => {
    const fetchMock = fetchReturning(() => new Response('png', { status: 200 }))

    const blob = await getImageBlob(clientWith(fetchMock), '/api/v1/users/1/signature')

    expect(await blob.text()).toBe('png')
    expect(sent(fetchMock)).toMatchObject({ method: 'GET', url: `${BASE}/api/v1/users/1/signature` })
  })
})
