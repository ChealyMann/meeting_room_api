import { describe, expect, it, vi, type Mock } from 'vitest'

import { createApiClient } from '../client'
import { countActiveUsers, listDivisionPage, updateDepartment } from '../organisation'

const BASE = 'http://localhost:8000'
type FetchMock = Mock<typeof fetch>

function json(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } })
}
const answer = (body: unknown) => vi.fn<typeof fetch>(async () => json(body))
const client = (fetchImpl: FetchMock) =>
  createApiClient({ baseUrl: BASE, getAccessToken: () => 'A', refresh: async () => false, onAuthLost: () => {}, fetchImpl })

function sent(fn: FetchMock) {
  const call = fn.mock.calls[0]
  if (!call) throw new Error('fetch was not called')
  return { method: call[1]?.method, url: String(call[0]), body: call[1]?.body }
}

describe('organisation API', () => {
  it('lists divisions of a department', async () => {
    const fetchMock = answer({ items: [], page: 1, size: 20, total: 0 })

    await listDivisionPage(client(fetchMock), { department_id: 4, search: 'it', is_active: true, page: 1, size: 20 })

    expect(sent(fetchMock)).toMatchObject({
      method: 'GET',
      url: `${BASE}/api/v1/divisions?department_id=4&search=it&is_active=true&page=1&size=20`,
    })
  })

  it('moves a department with a PATCH of its office', async () => {
    const fetchMock = answer({ id: 3 })

    await updateDepartment(client(fetchMock), 3, { location_id: 5 })

    expect(sent(fetchMock)).toEqual({ method: 'PATCH', url: `${BASE}/api/v1/departments/3`, body: '{"location_id":5}' })
  })

  it('counts active users with one small page', async () => {
    const fetchMock = answer({ items: [], page: 1, size: 1, total: 7 })

    const total = await countActiveUsers(client(fetchMock), { position_id: 2 })

    expect(sent(fetchMock).url).toBe(`${BASE}/api/v1/users?position_id=2&is_active=true&page=1&size=1`)
    expect(total).toBe(7)
  })
})
