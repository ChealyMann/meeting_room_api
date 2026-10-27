import { describe, expect, it, vi, type Mock } from 'vitest'

import { createApiClient } from '../client'
import { countUsersWithRole, listUserPage, resetPassword, setUserRoles, uploadUserSignature } from '../users'

const BASE = 'http://localhost:8000'
type FetchMock = Mock<typeof fetch>

function json(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } })
}
const answer = (body: unknown, status = 200) => vi.fn<typeof fetch>(async () => (status === 204 ? new Response(null, { status }) : json(body, status)))
const client = (fetchImpl: FetchMock) =>
  createApiClient({ baseUrl: BASE, getAccessToken: () => 'A', refresh: async () => false, onAuthLost: () => {}, fetchImpl })

function sent(fn: FetchMock) {
  const call = fn.mock.calls[0]
  if (!call) throw new Error('fetch was not called')
  return { method: call[1]?.method, url: String(call[0]), body: call[1]?.body }
}

describe('users API', () => {
  it('lists users with the given filters', async () => {
    const fetchMock = answer({ items: [], page: 1, size: 20, total: 0 })

    await listUserPage(client(fetchMock), { department_id: 4, role: 'PITIKA', is_active: true, page: 1, size: 20 })

    expect(sent(fetchMock)).toMatchObject({ method: 'GET', url: `${BASE}/api/v1/users?department_id=4&role=PITIKA&is_active=true&page=1&size=20` })
  })

  it('replaces the roles', async () => {
    const fetchMock = answer({ id: 7 })

    await setUserRoles(client(fetchMock), 7, ['STAFF'])

    expect(sent(fetchMock)).toEqual({ method: 'PUT', url: `${BASE}/api/v1/users/7/roles`, body: '{"role_codes":["STAFF"]}' })
  })

  it('sends a temporary password exactly as typed', async () => {
    const fetchMock = answer(null, 204)

    await resetPassword(client(fetchMock), 7, ' secret12 ')

    expect(sent(fetchMock)).toEqual({
      method: 'POST',
      url: `${BASE}/api/v1/users/7/reset-password`,
      body: '{"temporary_password":" secret12 "}',
    })
  })

  it("uploads a user's signature as a form", async () => {
    const fetchMock = answer({ id: 7 })
    const file = new File(['x'], 'sign.png', { type: 'image/png' })

    await uploadUserSignature(client(fetchMock), 7, file)

    const call = sent(fetchMock)
    expect(call).toMatchObject({ method: 'PUT', url: `${BASE}/api/v1/users/7/signature` })
    expect((call.body as FormData).get('file')).toBe(file)
  })

  it('counts the active users with a role', async () => {
    const fetchMock = answer({ items: [], page: 1, size: 1, total: 4 })

    expect(await countUsersWithRole(client(fetchMock), 'IT_LEAD')).toBe(4)
    expect(sent(fetchMock).url).toBe(`${BASE}/api/v1/users?role=IT_LEAD&is_active=true&page=1&size=1`)
  })
})
