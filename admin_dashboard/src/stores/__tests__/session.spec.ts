import { createPinia, setActivePinia } from 'pinia'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { useDraftsStore } from '../drafts'
import { REFRESH_KEY, useSessionStore } from '../session'

const ADMIN_ROLE = { code: 'ADMIN', name_en: 'Admin', name_kh: 'អ្នកគ្រប់គ្រង' }
const STAFF_ROLE = { code: 'STAFF', name_en: 'Staff', name_kh: 'បុគ្គលិក' }

function json(status: number, body: unknown) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })
}

const tokens = (n: number) => ({
  access_token: `A${n}`,
  refresh_token: `R${n}`,
  token_type: 'bearer',
})

const me = (roles = [ADMIN_ROLE], mustChange = false) => ({
  id: 1,
  email: 'admin@company.com',
  roles,
  must_change_password: mustChange,
})

type Route = (url: string, init: RequestInit) => Response

/** Answers each fetch by path; a path with no answer fails the test. */
function stubApi(routes: Record<string, Route>) {
  const fetchMock = vi.fn<typeof fetch>(async (input, init) => {
    const url = String(input)
    const path = new URL(url).pathname
    const route = routes[`${init?.method ?? 'GET'} ${path}`]
    if (!route) throw new Error(`unexpected call ${init?.method} ${path}`)
    return route(url, init ?? {})
  })
  vi.stubGlobal('fetch', fetchMock)
  return fetchMock
}

beforeEach(() => {
  setActivePinia(createPinia())
  sessionStorage.clear()
})

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('useSessionStore', () => {
  it('signIn keeps the access token in memory and the refresh token in sessionStorage', async () => {
    stubApi({
      'POST /api/v1/auth/login': () => json(200, tokens(1)),
      'GET /api/v1/me': () => json(200, me()),
    })
    const session = useSessionStore()

    await session.signIn('admin@company.com', 'pw')

    expect(session.accessToken).toBe('A1')
    expect(session.signedIn).toBe(true)
    expect(session.isAdmin).toBe(true)
    expect(session.mustChangePassword).toBe(false)
    expect(sessionStorage.getItem(REFRESH_KEY)).toBe('R1')
    expect(JSON.stringify(sessionStorage)).not.toContain('A1')
    expect(localStorage.length).toBe(0)
  })

  it('is not admin without the ADMIN role', async () => {
    stubApi({
      'POST /api/v1/auth/login': () => json(200, tokens(1)),
      'GET /api/v1/me': () => json(200, me([STAFF_ROLE])),
    })
    const session = useSessionStore()

    await session.signIn('staff@company.com', 'pw')

    expect(session.signedIn).toBe(true)
    expect(session.isAdmin).toBe(false)
  })

  it('restore signs in again from the stored refresh token', async () => {
    sessionStorage.setItem(REFRESH_KEY, 'R0')
    stubApi({
      'POST /api/v1/auth/refresh': () => json(200, tokens(2)),
      'GET /api/v1/me': () => json(200, me([ADMIN_ROLE], true)),
    })
    const session = useSessionStore()

    await session.restore()

    expect(session.ready).toBe(true)
    expect(session.accessToken).toBe('A2')
    expect(session.mustChangePassword).toBe(true)
    expect(sessionStorage.getItem(REFRESH_KEY)).toBe('R2')
  })

  it('restore with a refused refresh token ends signed out, ready, and the key removed', async () => {
    sessionStorage.setItem(REFRESH_KEY, 'R-old')
    stubApi({
      'POST /api/v1/auth/refresh': () =>
        json(401, { error: { code: 'UNAUTHORIZED', message: 'Please sign in.' } }),
    })
    const session = useSessionStore()

    await session.restore()

    expect(session.signedIn).toBe(false)
    expect(session.ready).toBe(true)
    expect(sessionStorage.getItem(REFRESH_KEY)).toBeNull()
  })

  it('restore without a stored token is ready and makes no call', async () => {
    const fetchMock = stubApi({})
    const session = useSessionStore()

    await session.restore()

    expect(session.ready).toBe(true)
    expect(session.signedIn).toBe(false)
    expect(fetchMock).not.toHaveBeenCalled()
  })

  it('refreshes an expired access token and repeats the call', async () => {
    stubApi({
      'POST /api/v1/auth/login': () => json(200, tokens(1)),
      'POST /api/v1/auth/refresh': () => json(200, tokens(2)),
      'GET /api/v1/me': (_url, init) =>
        new Headers(init.headers).get('Authorization') === 'Bearer A2'
          ? json(200, me())
          : json(401, { error: { code: 'UNAUTHORIZED', message: 'Expired.' } }),
    })
    const session = useSessionStore()

    await session.signIn('admin@company.com', 'pw')

    expect(session.accessToken).toBe('A2')
    expect(session.user?.email).toBe('admin@company.com')
    expect(sessionStorage.getItem(REFRESH_KEY)).toBe('R2')
  })

  it('expire clears tokens and user when the session is lost', async () => {
    stubApi({
      'POST /api/v1/auth/login': () => json(200, tokens(1)),
      'GET /api/v1/me': () => json(200, me()),
    })
    const session = useSessionStore()
    await session.signIn('admin@company.com', 'pw')

    session.expire()

    expect(session.signedIn).toBe(false)
    expect(session.user).toBeNull()
    expect(sessionStorage.getItem(REFRESH_KEY)).toBeNull()
  })

  it('a network error during refresh does not sign the user out', async () => {
    stubApi({
      'POST /api/v1/auth/login': () => json(200, tokens(1)),
      'GET /api/v1/me': () => json(200, me()),
    })
    const session = useSessionStore()
    await session.signIn('admin@company.com', 'pw')
    vi.stubGlobal(
      'fetch',
      vi.fn<typeof fetch>(async () => {
        throw new TypeError('Failed to fetch')
      }),
    )

    await expect(session.refresh()).rejects.toMatchObject({ code: 'NETWORK_ERROR' })
    expect(session.signedIn).toBe(true)
    expect(sessionStorage.getItem(REFRESH_KEY)).toBe('R1')
  })

  it('changePassword stores the new tokens and reloads the user', async () => {
    let changed = false
    stubApi({
      'POST /api/v1/auth/login': () => json(200, tokens(1)),
      'GET /api/v1/me': () => json(200, me([ADMIN_ROLE], !changed)),
      'POST /api/v1/auth/change-password': () => {
        changed = true
        return json(200, tokens(3))
      },
    })
    const session = useSessionStore()
    await session.signIn('admin@company.com', 'old')
    expect(session.mustChangePassword).toBe(true)

    await session.changePassword('old', 'new password')

    expect(session.accessToken).toBe('A3')
    expect(sessionStorage.getItem(REFRESH_KEY)).toBe('R3')
    expect(session.mustChangePassword).toBe(false)
  })

  it('signOut clears everything even when logout fails with 500', async () => {
    stubApi({
      'POST /api/v1/auth/login': () => json(200, tokens(1)),
      'GET /api/v1/me': () => json(200, me()),
      'POST /api/v1/auth/logout': () => json(500, { error: { code: 'X', message: 'Boom.' } }),
    })
    const session = useSessionStore()
    await session.signIn('admin@company.com', 'pw')

    await session.signOut()

    expect(session.signedIn).toBe(false)
    expect(session.user).toBeNull()
    expect(sessionStorage.getItem(REFRESH_KEY)).toBeNull()
  })
})

describe('useSessionStore and drafts', () => {
  async function signedIn() {
    stubApi({
      'POST /api/v1/auth/login': () => json(200, tokens(1)),
      'GET /api/v1/me': () => json(200, me()),
      'POST /api/v1/auth/logout': () => new Response(null, { status: 204 }),
    })
    const session = useSessionStore()
    await session.signIn('admin@company.com', 'pw')
    const drafts = useDraftsStore()
    drafts.set('profile:1', { phone: '099' })
    return { session, drafts }
  }

  it('signOut forgets unsaved drafts', async () => {
    const { session, drafts } = await signedIn()

    await session.signOut()

    expect(drafts.get('profile:1')).toBeUndefined()
  })

  it('expire keeps unsaved drafts for after the next sign-in (DSH-A06)', async () => {
    const { session, drafts } = await signedIn()

    session.expire()

    expect(drafts.get('profile:1')).toEqual({ phone: '099' })
  })
})
